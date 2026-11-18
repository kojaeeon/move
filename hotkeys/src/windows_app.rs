use crate::config::{self, Action, Binding, ALT, CTRL, SHIFT, WIN};
use std::ffi::OsStr;
use std::fs;
use std::io;
use std::mem::{size_of, zeroed};
use std::os::windows::ffi::OsStrExt;
use std::path::PathBuf;
use std::ptr::{null, null_mut};
use std::time::{Duration, Instant};
use windows_sys::Win32::Foundation::{HWND, LPARAM, LRESULT, POINT, WPARAM};
use windows_sys::Win32::System::Diagnostics::Debug::MessageBeep;
use windows_sys::Win32::System::LibraryLoader::GetModuleHandleW;
use windows_sys::Win32::UI::Input::KeyboardAndMouse::*;
use windows_sys::Win32::UI::Shell::*;
use windows_sys::Win32::UI::WindowsAndMessaging::*;

const TRAY_MESSAGE: u32 = WM_APP + 1;
const SEND_TIMER: usize = 1;
const EDIT: usize = 1;
const EXIT: usize = 2;
const MODIFIERS: [(u32, u16); 4] = [
    (CTRL, VK_CONTROL),
    (ALT, VK_MENU),
    (SHIFT, VK_SHIFT),
    (WIN, VK_LWIN),
];

struct Pending {
    index: usize,
    target: HWND,
    started: Instant,
}

struct State {
    bindings: Vec<Binding>,
    config_path: PathBuf,
    pending: Option<Pending>,
    taskbar_created: u32,
}

fn wide(value: impl AsRef<OsStr>) -> Vec<u16> {
    value.as_ref().encode_wide().chain(Some(0)).collect()
}

fn last_error(operation: &str) -> String {
    format!("{operation}: {}", io::Error::last_os_error())
}

pub fn show_error(text: &str) {
    unsafe {
        MessageBoxW(
            null_mut(),
            wide(text).as_ptr(),
            wide("Hotkeys").as_ptr(),
            MB_ICONERROR,
        );
    }
}

pub fn run() -> Result<(), String> {
    let mut config_path = std::env::current_exe().map_err(|error| error.to_string())?;
    config_path.set_file_name("hotkeys.toml");
    let source = fs::read_to_string(&config_path)
        .map_err(|error| format!("Cannot read {}: {error}", config_path.display()))?;
    let bindings = config::parse(&source)?;
    let mut state = State {
        bindings,
        config_path,
        pending: None,
        taskbar_created: 0,
    };
    unsafe { run_window(&mut state) }
}

unsafe fn run_window(state: &mut State) -> Result<(), String> {
    let instance = GetModuleHandleW(null());
    let class_name = wide("MoveHotkeysWindow");
    let mut class: WNDCLASSW = zeroed();
    class.hInstance = instance;
    class.lpszClassName = class_name.as_ptr();
    class.lpfnWndProc = Some(window_proc);
    if RegisterClassW(&class) == 0 {
        return Err(last_error("Cannot register the tray window"));
    }
    // Keep a hidden top-level window so Explorer broadcasts can restore the tray icon.
    let window = CreateWindowExW(
        0,
        class_name.as_ptr(),
        wide("Hotkeys").as_ptr(),
        WS_OVERLAPPED,
        0,
        0,
        0,
        0,
        null_mut(),
        null_mut(),
        instance,
        null(),
    );
    if window.is_null() {
        return Err(last_error("Cannot create the tray window"));
    }

    let mut registered = 0;
    let result = (|| {
        for binding in &state.bindings {
            let id = registered + 1;
            if RegisterHotKey(
                window,
                id,
                binding.chord.modifiers | MOD_NOREPEAT,
                u32::from(binding.chord.key),
            ) == 0
            {
                return Err(last_error(&format!("Cannot register {}", binding.name)));
            }
            registered = id;
        }
        state.taskbar_created = RegisterWindowMessageW(wide("TaskbarCreated").as_ptr());
        SetWindowLongPtrW(window, GWLP_USERDATA, state as *mut State as isize);
        if !tray_icon(window, NIM_ADD) {
            return Err("Cannot add the notification area icon.".into());
        }
        let mut message: MSG = zeroed();
        loop {
            let status = GetMessageW(&mut message, null_mut(), 0, 0);
            if status == 0 {
                return Ok(());
            }
            if status == -1 {
                return Err(last_error("Cannot read Windows messages"));
            }
            TranslateMessage(&message);
            DispatchMessageW(&message);
        }
    })();

    for id in 1..=registered {
        UnregisterHotKey(window, id);
    }
    SetWindowLongPtrW(window, GWLP_USERDATA, 0);
    tray_icon(window, NIM_DELETE);
    DestroyWindow(window);
    result
}

unsafe fn tray_icon(window: HWND, operation: u32) -> bool {
    let mut data: NOTIFYICONDATAW = zeroed();
    data.cbSize = size_of::<NOTIFYICONDATAW>() as u32;
    data.hWnd = window;
    data.uID = 1;
    data.uFlags = NIF_ICON | NIF_MESSAGE | NIF_TIP;
    data.uCallbackMessage = TRAY_MESSAGE;
    data.hIcon = LoadIconW(null_mut(), IDI_APPLICATION);
    let tip = wide("Hotkeys");
    data.szTip[..tip.len()].copy_from_slice(&tip);
    Shell_NotifyIconW(operation, &data) != 0
}

unsafe extern "system" fn window_proc(
    window: HWND,
    message: u32,
    wparam: WPARAM,
    lparam: LPARAM,
) -> LRESULT {
    let state = GetWindowLongPtrW(window, GWLP_USERDATA) as *mut State;
    let Some(state) = state.as_mut() else {
        return DefWindowProcW(window, message, wparam, lparam);
    };
    match message {
        WM_HOTKEY => {
            if let Some(index) = wparam
                .checked_sub(1)
                .filter(|id| *id < state.bindings.len())
            {
                let target = GetForegroundWindow();
                if !target.is_null() && SetTimer(window, SEND_TIMER, 20, None) != 0 {
                    state.pending = Some(Pending {
                        index,
                        target,
                        started: Instant::now(),
                    });
                }
            }
        }
        WM_TIMER if wparam == SEND_TIMER => {
            if let Some(pending) = state.pending.as_ref() {
                let binding = &state.bindings[pending.index];
                if GetForegroundWindow() != pending.target
                    || pending.started.elapsed() > Duration::from_secs(3)
                {
                    state.pending = None;
                    KillTimer(window, SEND_TIMER);
                } else if keys_released(binding.chord.key) {
                    state.pending = None;
                    KillTimer(window, SEND_TIMER);
                    if !send_action(&binding.action) {
                        MessageBeep(MB_ICONWARNING);
                    }
                }
            }
        }
        TRAY_MESSAGE if lparam as u32 == WM_RBUTTONUP || lparam as u32 == WM_CONTEXTMENU => {
            // Avoid keeping a mutable borrow of State across the menu's nested message loop.
            let config_path = state.config_path.clone();
            show_tray_menu(window, config_path);
        }
        WM_CLOSE => PostQuitMessage(0),
        other if other != 0 && other == state.taskbar_created => {
            tray_icon(window, NIM_ADD);
        }
        _ => return DefWindowProcW(window, message, wparam, lparam),
    }
    0
}

unsafe fn show_tray_menu(window: HWND, config_path: PathBuf) {
    let menu = CreatePopupMenu();
    if menu.is_null() {
        return;
    }
    AppendMenuW(menu, MF_STRING, EDIT, wide("Open settings").as_ptr());
    AppendMenuW(menu, MF_STRING, EXIT, wide("Exit").as_ptr());
    let mut point: POINT = zeroed();
    if GetCursorPos(&mut point) != 0 {
        SetForegroundWindow(window);
        let selected = TrackPopupMenu(
            menu,
            TPM_RETURNCMD | TPM_RIGHTBUTTON,
            point.x,
            point.y,
            0,
            window,
            null(),
        );
        PostMessageW(window, WM_NULL, 0, 0);
        match selected as usize {
            EDIT => {
                let result = ShellExecuteW(
                    window,
                    wide("open").as_ptr(),
                    wide(config_path).as_ptr(),
                    null(),
                    null(),
                    SW_SHOWNORMAL,
                );
                if result as isize <= 32 {
                    show_error("Open hotkeys.toml in a text editor, then restart Hotkeys.");
                }
            }
            EXIT => PostQuitMessage(0),
            _ => {}
        }
    }
    DestroyMenu(menu);
}

unsafe fn keys_released(key: u16) -> bool {
    [key, VK_CONTROL, VK_MENU, VK_SHIFT, VK_LWIN, VK_RWIN]
        .into_iter()
        .all(|key| GetAsyncKeyState(i32::from(key)) >= 0)
}

fn input(key: u16, scan: u16, flags: u32) -> INPUT {
    INPUT {
        r#type: INPUT_KEYBOARD,
        Anonymous: INPUT_0 {
            ki: KEYBDINPUT {
                wVk: key,
                wScan: scan,
                dwFlags: flags,
                time: 0,
                dwExtraInfo: 0,
            },
        },
    }
}

unsafe fn send_action(action: &Action) -> bool {
    let mut events = Vec::new();
    match action {
        Action::Text(text) => {
            for unit in text.encode_utf16() {
                events.push(input(0, unit, KEYEVENTF_UNICODE));
                events.push(input(0, unit, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP));
            }
        }
        Action::Send(chord) => {
            let active = MODIFIERS
                .into_iter()
                .filter(|(bit, _)| chord.modifiers & bit != 0);
            for (_, key) in active.clone() {
                events.push(input(key, 0, key_flags(key)));
            }
            let flags = key_flags(chord.key);
            events.push(input(chord.key, 0, flags));
            events.push(input(chord.key, 0, flags | KEYEVENTF_KEYUP));
            for (_, key) in active.rev() {
                events.push(input(key, 0, key_flags(key) | KEYEVENTF_KEYUP));
            }
        }
    }
    SendInput(
        events.len() as u32,
        events.as_ptr(),
        size_of::<INPUT>() as i32,
    ) == events.len() as u32
}

fn key_flags(key: u16) -> u32 {
    match key {
        VK_PRIOR | VK_NEXT | VK_END | VK_HOME | VK_LEFT | VK_UP | VK_RIGHT | VK_DOWN
        | VK_INSERT | VK_DELETE | VK_LWIN => KEYEVENTF_EXTENDEDKEY,
        _ => 0,
    }
}
