use std::sync::Mutex;

use tauri::Manager;
use tauri_plugin_shell::{
  process::{CommandChild, CommandEvent},
  ShellExt,
};

const BACKEND_SIDECAR_NAME: &str = "smart-move-backend";
const BACKEND_PORT: &str = "18457";

#[derive(Default)]
struct BackendSidecar(Mutex<Option<CommandChild>>);

fn main() {
  tauri::Builder::default()
    .manage(BackendSidecar::default())
    .plugin(tauri_plugin_shell::init())
    .plugin(tauri_plugin_process::init())
    .plugin(tauri_plugin_updater::Builder::new().build())
    .setup(|app| {
      let data_dir = app.path().app_data_dir()?;
      std::fs::create_dir_all(&data_dir)?;

      let env_path = data_dir.join(".env");
      let (mut rx, child) = app
        .shell()
        .sidecar(BACKEND_SIDECAR_NAME)?
        .current_dir(&data_dir)
        .env("SMART_MOVE_DATA_DIR", &data_dir)
        .env("SMART_MOVE_ENV_PATH", &env_path)
        .env("SMART_MOVE_BACKEND_PORT", BACKEND_PORT)
        .spawn()?;

      *app.state::<BackendSidecar>().0.lock().unwrap() = Some(child);

      tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
          match event {
            CommandEvent::Stdout(line) => {
              println!("[smart-move-backend] {}", String::from_utf8_lossy(&line).trim());
            }
            CommandEvent::Stderr(line) => {
              eprintln!("[smart-move-backend] {}", String::from_utf8_lossy(&line).trim());
            }
            CommandEvent::Error(error) => {
              eprintln!("[smart-move-backend] {error}");
            }
            CommandEvent::Terminated(payload) => {
              println!(
                "[smart-move-backend] exited with code {:?} signal {:?}",
                payload.code, payload.signal
              );
            }
            _ => {}
          }
        }
      });

      Ok(())
    })
    .build(tauri::generate_context!())
    .expect("error while building Smart Move desktop app")
    .run(|app, event| {
      if let tauri::RunEvent::Exit = event {
        if let Some(child) = app.state::<BackendSidecar>().0.lock().unwrap().take() {
          let _ = child.kill();
        }
      }
    });
}
