#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::TcpStream;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use tauri::{Manager, State};

struct BackendProcess(Mutex<Option<Child>>);

/// Poll port 8000 until it accepts connections or timeout elapses.
fn wait_for_backend(timeout: Duration) -> bool {
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        if TcpStream::connect("127.0.0.1:8000").is_ok() {
            // Give uvicorn a moment to finish startup after TCP is up.
            std::thread::sleep(Duration::from_millis(600));
            return true;
        }
        std::thread::sleep(Duration::from_millis(250));
    }
    false
}

/// Locate the project root relative to this binary.
/// In debug builds (cargo run from src-tauri/) root is 3 levels up.
/// In release builds the .exe sits inside the bundle; cwd is the project root.
fn project_root() -> std::path::PathBuf {
    if cfg!(debug_assertions) {
        let exe = std::env::current_exe().unwrap();
        // target/debug/spotify-sync-manager.exe → go up 3
        exe.parent().unwrap()   // debug/
            .parent().unwrap()  // target/
            .parent().unwrap()  // src-tauri/
            .parent().unwrap()  // frontend/
            .parent().unwrap()  // gui/
            .parent().unwrap()  // project root
            .to_path_buf()
    } else {
        std::env::current_dir().unwrap()
    }
}

fn main() {
    tauri::Builder::default()
        .manage(BackendProcess(Mutex::new(None)))
        .setup(|app| {
            let root = project_root();
            let script = root.join("gui").join("backend").join("main.py");

            // On Windows "python", on Unix prefer "python3".
            let python = if cfg!(target_os = "windows") { "python" } else { "python3" };

            // Spawn the FastAPI backend; it won't open the browser (handled by Tauri).
            let child = Command::new(python)
                .arg(&script)
                .env("SPOTIFY_SYNC_TAURI", "1") // signal to main.py to skip webbrowser.open
                .current_dir(&root)
                .spawn()?;

            *app.state::<BackendProcess>().0.lock().unwrap() = Some(child);

            // Wait for the backend in a background thread, then show the window.
            let window = app.get_webview_window("main")
                .expect("no 'main' window in tauri.conf.json");

            std::thread::spawn(move || {
                let ready = wait_for_backend(Duration::from_secs(20));
                if !ready {
                    eprintln!("[tauri] backend did not start within 20 s — showing window anyway");
                }
                window.show().unwrap();
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            // Kill the Python backend when the last window is destroyed.
            if let tauri::WindowEvent::Destroyed = event {
                let state = window.state::<BackendProcess>();
                if let Some(mut child) = state.0.lock().unwrap().take() {
                    let _ = child.kill();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
