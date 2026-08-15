mod mcp;

use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }

      let client = crate::mcp::McpClient::new("127.0.0.1:18789".parse().unwrap());
      if let Err(e) = client.initialize() {
        log::error!("Failed to initialize MCP server: {}", e);
      }
      app.manage(client);

      Ok(())
    })
    .invoke_handler(tauri::generate_handler![
      crate::mcp::mcp_call,
      crate::mcp::mcp_tools_list
    ])
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
