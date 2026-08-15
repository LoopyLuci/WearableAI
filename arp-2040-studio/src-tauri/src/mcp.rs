use std::io::{BufRead, BufReader, Write};
use std::net::{TcpStream, SocketAddr};
use std::thread;
use std::time::Duration;
use tauri::State;
use serde_json::Value;

#[derive(Debug, Clone)]
pub struct McpClient {
    addr: SocketAddr,
}

impl McpClient {
    pub fn new(addr: SocketAddr) -> Self {
        Self { addr }
    }

    pub fn call(&self, method: &str, params: Value) -> Result<Value, String> {
        let mut stream = TcpStream::connect(self.addr).map_err(|e| format!("connect failed: {e}"))?;
        stream.set_read_timeout(Some(Duration::from_secs(60))).ok();
        stream.set_write_timeout(Some(Duration::from_secs(5))).ok();

        let req = serde_json::json!({
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        });
        writeln!(stream, "{}", req).map_err(|e| format!("write failed: {e}"))?;
        stream.flush().map_err(|e| format!("flush failed: {e}"))?;

        let mut reader = BufReader::new(stream);
        let mut line = String::new();
        reader.read_line(&mut line).map_err(|e| format!("read failed: {e}"))?;
        let trimmed = line.trim();
        if trimmed.is_empty() {
            return Err("empty MCP response from server".into());
        }
        let resp: Value = serde_json::from_str(trimmed).map_err(|e| format!("json parse failed: {e}"))?;

        if let Some(error) = resp.get("error").and_then(|e| e.as_object()) {
            let code = error.get("code").and_then(|c| c.as_i64()).unwrap_or(-1);
            let message = error.get("message").and_then(|m| m.as_str()).unwrap_or("unknown");
            return Err(format!("MCP error {}: {}", code, message));
        }

        Ok(resp.get("result").cloned().unwrap_or(Value::Null))
    }

    pub fn initialize(&self) -> Result<(), String> {
        // Retry a few times in case server is still starting
        let mut last_err = String::new();
        for attempt in 0..5 {
            if attempt > 0 {
                thread::sleep(Duration::from_millis(500));
            }
            match self.call("initialize", serde_json::json!({
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": { "name": "arp-2040-studio", "version": "0.1.0" }
            })) {
                Ok(_) => return Ok(()),
                Err(e) => last_err = e,
            }
        }
        Err(last_err)
    }
}

#[tauri::command]
pub fn mcp_call(client: State<'_, McpClient>, name: String, arguments: Value) -> Result<Value, String> {
    let params = serde_json::json!({ "tool_calls": [ { "name": name, "arguments": arguments } ] });
    let result = client.call("tools/call", params)?;
    if let Some(tool_results) = result.get("tool_results").and_then(|v| v.as_array()) {
        if let Some(first) = tool_results.first() {
            if let Some(result_obj) = first.get("result").and_then(|v| v.as_object()) {
                if let Some(content) = result_obj.get("content").and_then(|v| v.as_array()).and_then(|arr| arr.first()) {
                    return Ok(content.clone());
                }
            }
        }
    }
    Ok(result)
}

#[tauri::command]
pub fn mcp_tools_list(client: State<'_, McpClient>) -> Result<Value, String> {
    client.call("tools/list", Value::Null)
}
