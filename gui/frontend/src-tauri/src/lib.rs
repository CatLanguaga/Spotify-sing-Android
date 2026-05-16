// Entry point for mobile targets (not used on desktop but required by Tauri v2 scaffold).
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Desktop entry is in main.rs; this is only compiled for mobile.
}
