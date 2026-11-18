use std::env;
use std::ffi::c_void;
use std::io::{self, Write};
use std::mem::size_of_val;
use std::process::ExitCode;
use std::ptr;

const DOMAIN_PASSWORD: u32 = 2;
const LOCAL_MACHINE: u32 = 2;
const ENTERPRISE: u32 = 3;
const ERROR_NOT_FOUND: i32 = 1168;
const STD_INPUT_HANDLE: u32 = -10i32 as u32;
const ENABLE_PROCESSED_INPUT: u32 = 1;
const ENABLE_LINE_INPUT: u32 = 2;
const ENABLE_ECHO_INPUT: u32 = 4;
const MAX_PASSWORD_UNITS: usize = 1280;

type Handle = *mut c_void;

#[repr(C)]
struct Credential {
    flags: u32,
    kind: u32,
    target: *mut u16,
    comment: *mut u16,
    last_written: [u32; 2],
    blob_size: u32,
    blob: *mut u8,
    persist: u32,
    attribute_count: u32,
    attributes: *mut c_void,
    target_alias: *mut u16,
    user_name: *mut u16,
}

#[link(name = "advapi32")]
unsafe extern "system" {
    fn CredGetSessionTypes(count: u32, maximum: *mut u32) -> i32;
    fn CredReadW(target: *const u16, kind: u32, flags: u32, result: *mut *mut Credential) -> i32;
    fn CredFree(buffer: *mut c_void);
    fn CredWriteW(credential: *const Credential, flags: u32) -> i32;
}

#[link(name = "kernel32")]
unsafe extern "system" {
    fn GetStdHandle(kind: u32) -> Handle;
    fn GetConsoleMode(handle: Handle, mode: *mut u32) -> i32;
    fn SetConsoleMode(handle: Handle, mode: u32) -> i32;
    fn ReadConsoleW(
        handle: Handle,
        buffer: *mut u16,
        length: u32,
        read: *mut u32,
        control: *mut c_void,
    ) -> i32;
}

fn win_error(operation: &str) -> String {
    format!("{operation}: {}", io::Error::last_os_error())
}

fn storage_allowed() -> Result<(), String> {
    let mut levels = [0u32; DOMAIN_PASSWORD as usize + 1];
    if unsafe { CredGetSessionTypes(levels.len() as u32, levels.as_mut_ptr()) } == 0 {
        return Err(win_error("CredGetSessionTypes"));
    }
    if !matches!(levels[DOMAIN_PASSWORD as usize], LOCAL_MACHINE | ENTERPRISE) {
        return Err("Windows credentials cannot be saved persistently in this session.".into());
    }
    Ok(())
}

fn ensure_target_is_new(target: &[u16]) -> Result<(), String> {
    let mut existing = ptr::null_mut();
    if unsafe { CredReadW(target.as_ptr(), DOMAIN_PASSWORD, 0, &mut existing) } != 0 {
        unsafe { CredFree(existing.cast()) };
        return Err(
            "A Windows credential already exists for this host. Edit it in Credential Manager."
                .into(),
        );
    }
    let error = io::Error::last_os_error();
    if error.raw_os_error() != Some(ERROR_NOT_FOUND) {
        return Err(format!("CredReadW: {error}"));
    }
    Ok(())
}

struct ConsoleMode {
    handle: Handle,
    original: u32,
}

impl Drop for ConsoleMode {
    fn drop(&mut self) {
        unsafe { SetConsoleMode(self.handle, self.original) };
    }
}

struct Password([u16; MAX_PASSWORD_UNITS + 3]);

impl Drop for Password {
    fn drop(&mut self) {
        for unit in &mut self.0 {
            unsafe { ptr::write_volatile(unit, 0) };
        }
    }
}

fn read_password(password: &mut Password) -> Result<&mut [u16], String> {
    let handle = unsafe { GetStdHandle(STD_INPUT_HANDLE) };
    let mut original = 0;
    if unsafe { GetConsoleMode(handle, &mut original) } == 0 {
        return Err("Open this program in a Windows console to enter a password.".into());
    }

    eprint!("Password (hidden): ");
    io::stderr().flush().map_err(|error| error.to_string())?;

    let hidden = (original | ENABLE_LINE_INPUT) & !(ENABLE_ECHO_INPUT | ENABLE_PROCESSED_INPUT);
    if unsafe { SetConsoleMode(handle, hidden) } == 0 {
        return Err(win_error("SetConsoleMode"));
    }
    let mode = ConsoleMode { handle, original };

    let mut count = 0;
    let status = unsafe {
        ReadConsoleW(
            handle,
            password.0.as_mut_ptr(),
            password.0.len() as u32,
            &mut count,
            ptr::null_mut(),
        )
    };
    let result = if status == 0 {
        Err(win_error("ReadConsoleW"))
    } else {
        Ok(())
    };
    drop(mode);
    eprintln!();
    result?;

    let line = &mut password.0[..count as usize];
    let end = match line {
        [.., 13, 10] => line.len() - 2,
        [.., 13 | 10] => line.len() - 1,
        _ => return Err("Password input is incomplete or too long.".into()),
    };
    if end == 0 || end > MAX_PASSWORD_UNITS || line[..end].iter().any(|unit| *unit < 32) {
        return Err("Password is empty, too long, or contains a console control character.".into());
    }
    Ok(&mut line[..end])
}

fn add(target: &str, account: &str) -> Result<(), String> {
    let valid_host = !target.is_empty()
        && target.len() <= 253
        && target.split('.').all(|label| {
            !label.is_empty()
                && label.len() <= 63
                && !label.starts_with('-')
                && !label.ends_with('-')
                && label
                    .bytes()
                    .all(|ch| ch.is_ascii_alphanumeric() || ch == b'-')
        });
    if !valid_host {
        return Err("Enter one exact host name, without a URL, path, or wildcard.".into());
    }
    if account.trim().is_empty()
        || account.encode_utf16().count() > 513
        || account.chars().any(char::is_control)
    {
        return Err("Enter a valid Windows account name.".into());
    }

    storage_allowed()?;
    let mut target: Vec<u16> = target.encode_utf16().chain([0]).collect();
    let mut account: Vec<u16> = account.encode_utf16().chain([0]).collect();
    ensure_target_is_new(&target)?;
    let mut password = Password([0; MAX_PASSWORD_UNITS + 3]);
    let secret = read_password(&mut password)?;

    ensure_target_is_new(&target)?;
    let credential = Credential {
        flags: 0,
        kind: DOMAIN_PASSWORD,
        target: target.as_mut_ptr(),
        comment: ptr::null_mut(),
        last_written: [0; 2],
        blob_size: size_of_val(secret) as u32,
        blob: secret.as_mut_ptr().cast(),
        persist: LOCAL_MACHINE,
        attribute_count: 0,
        attributes: ptr::null_mut(),
        target_alias: ptr::null_mut(),
        user_name: account.as_mut_ptr(),
    };
    if unsafe { CredWriteW(&credential, 0) } == 0 {
        return Err(win_error("CredWriteW"));
    }
    Ok(())
}

const USAGE: &str = "Usage:\n  wincred check\n  wincred add HOST ACCOUNT";

fn run() -> Result<(), String> {
    let args: Vec<_> = env::args_os().skip(1).collect();
    match args.as_slice() {
        [] => println!("{USAGE}"),
        [action] if action == "--help" || action == "-h" => println!("{USAGE}"),
        [action] if action == "check" => {
            storage_allowed()?;
            println!("Persistent Windows credential storage is available.");
        }
        [action, target, account] if action == "add" => {
            let target = target.to_str().ok_or("Host name must be valid Unicode.")?;
            let account = account
                .to_str()
                .ok_or("Account name must be valid Unicode.")?;
            add(target, account)?;
            println!("Windows credential added for {target}.");
        }
        _ => return Err(USAGE.into()),
    }
    Ok(())
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("{message}");
            ExitCode::FAILURE
        }
    }
}
