#![cfg_attr(all(windows, not(test)), windows_subsystem = "windows")]

#[cfg(any(windows, test))]
mod config;
#[cfg(windows)]
mod windows_app;

#[cfg(windows)]
fn main() {
    if let Err(error) = windows_app::run() {
        windows_app::show_error(&error);
    }
}

#[cfg(not(windows))]
fn main() {
    eprintln!("Hotkeys runs on Windows.");
}
