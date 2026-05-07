use std::sync::Mutex;

use reqwest::Method;
use serde::{Deserialize, Serialize};
use tauri::Manager;
use tauri_plugin_shell::{
  process::{CommandChild, CommandEvent},
  ShellExt,
};

const BACKEND_SIDECAR_NAME: &str = "smart-move-backend";
const BACKEND_PORT: &str = "18457";
const REMOTE_API_URL: Option<&str> = option_env!("SMART_MOVE_REMOTE_API_URL");

#[derive(Default)]
struct BackendSidecar(Mutex<Option<CommandChild>>);

#[derive(Deserialize)]
struct DesktopApiRequest {
  url: String,
  method: Option<String>,
  headers: Option<std::collections::HashMap<String, String>>,
  body: Option<String>,
}

#[derive(Serialize)]
struct DesktopApiResponse {
  ok: bool,
  status: u16,
  body: String,
}

#[tauri::command]
async fn desktop_api_request(request: DesktopApiRequest) -> Result<DesktopApiResponse, String> {
  let client = reqwest::Client::new();
  let method = request
    .method
    .as_deref()
    .unwrap_or("GET")
    .parse::<Method>()
    .map_err(|error| error.to_string())?;

  let mut builder = client.request(method, &request.url);

  if let Some(headers) = request.headers {
    for (key, value) in headers {
      builder = builder.header(&key, value);
    }
  }

  if let Some(body) = request.body {
    builder = builder.body(body);
  }

  let response = builder.send().await.map_err(|error| error.to_string())?;
  let status = response.status().as_u16();
  let ok = response.status().is_success();
  let body = response.text().await.map_err(|error| error.to_string())?;

  Ok(DesktopApiResponse { ok, status, body })
}

fn main() {
  tauri::Builder::default()
    .manage(BackendSidecar::default())
    .plugin(tauri_plugin_shell::init())
    .plugin(tauri_plugin_process::init())
    .plugin(tauri_plugin_updater::Builder::new().build())
    .invoke_handler(tauri::generate_handler![desktop_api_request])
    .setup(|app| {
      if let Some(remote_api_url) = REMOTE_API_URL {
        if !remote_api_url.trim().is_empty() {
          println!("[smart-move-backend] remote API mode enabled: {remote_api_url}");
          return Ok(());
        }
      }

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
