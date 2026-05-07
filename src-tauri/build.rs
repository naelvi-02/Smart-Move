fn main() {
  if let Ok(remote_api_url) = std::env::var("SMART_MOVE_REMOTE_API_URL") {
    let trimmed = remote_api_url.trim();
    if !trimmed.is_empty() {
      println!("cargo:rustc-env=SMART_MOVE_REMOTE_API_URL={trimmed}");
    }
  }

  tauri_build::build();
}
