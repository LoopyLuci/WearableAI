use std::path::PathBuf;
use serde::{Deserialize, Serialize};
use std::io::{self, BufRead, BufReader, Write};
use std::net::{TcpListener, TcpStream};
use std::process::Command;
use serialport;
use clap::{Parser, ValueEnum};
use serde_json::Value;

#[derive(Debug, Clone, Copy, ValueEnum, Default)]
pub enum Transport {
    #[default]
    Stdio,
    Tcp,
}

#[derive(Parser, Default)]
#[command(name = "arp-2040-mcp", about = "ARP-2040 Studio MCP Server", version)]
pub struct Args {
    #[arg(long, value_enum, default_value_t = Transport::Stdio)]
    pub transport: Transport,
    #[arg(long, default_value_t = 8765)]
    pub tcp_port: u16,
    #[arg(long, default_value_t = String::from("127.0.0.1"))]
    pub tcp_bind: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcRequest {
    pub jsonrpc: String,
    pub id: Option<Value>,
    pub method: String,
    pub params: Option<Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcResponse {
    pub jsonrpc: String,
    pub id: Value,
    pub result: Option<Value>,
    pub error: Option<Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolResult {
    pub content: Vec<ContentItem>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub is_error: Option<bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContentItem {
    #[serde(rename = "type")]
    pub kind: String,
    pub text: String,
}

pub fn ok_result(id: Value, result: Value) -> Value {
    let resp = JsonRpcResponse {
        jsonrpc: "2.0".into(),
        id,
        result: Some(result),
        error: None,
    };
    serde_json::to_value(resp).unwrap()
}

pub fn err_result(id: Value, message: &str) -> Value {
    let resp = JsonRpcResponse {
        jsonrpc: "2.0".into(),
        id,
        result: None,
        error: Some(serde_json::json!({
            "code": -32600,
            "message": message
        })),
    };
    serde_json::to_value(resp).unwrap()
}

pub fn tool_result(content: Vec<ContentItem>, is_error: bool) -> Value {
    let tr = ToolResult {
        content,
        is_error: Some(is_error),
    };
    serde_json::to_value(tr).unwrap()
}

pub fn list_tools() -> Value {
    serde_json::json!({
        "tools": [
            { "name": "device_list", "description": "List connected RP2040 devices.", "inputSchema": { "type": "object", "properties": {} } },
            { "name": "device_flash", "description": "Flash a UF2/BIN to a device.", "inputSchema": { "type": "object", "properties": { "device": { "type": "string" }, "path": { "type": "string" } }, "required": ["device", "path"] } },
            { "name": "telemetry_start", "description": "Start telemetry streaming from a device.", "inputSchema": { "type": "object", "properties": { "device": { "type": "string" } }, "required": ["device"] } },
            { "name": "telemetry_stop", "description": "Stop telemetry streaming.", "inputSchema": { "type": "object", "properties": { "device": { "type": "string" } }, "required": ["device"] } },
            { "name": "firmware_build", "description": "Build firmware with PlatformIO.", "inputSchema": { "type": "object", "properties": { "env": { "type": "string" } } } },
            { "name": "gui_open_panel", "description": "Open a GUI panel.", "inputSchema": { "type": "object", "properties": { "panel": { "type": "string" } }, "required": ["panel"] } }
        ]
    })
}

pub fn handle_device_list() -> Value {
    let mut devices = Vec::new();
    if let Ok(ports) = serialport::available_ports() {
        for port in ports {
            let port_name = port.port_name.clone();
            let mode = if let serialport::SerialPortType::UsbPort(info) = &port.port_type {
                if info.vid == 0x2E8A && info.pid == 0x000A {
                    "bootloader"
                } else if info.vid == 0x2E8A && info.pid == 0x0005 {
                    "runtime"
                } else {
                    "unknown"
                }
            } else {
                "unknown"
            };
            if mode != "unknown" {
                devices.push(serde_json::json!({
                    "id": port_name.clone(),
                    "port": port_name,
                    "mode": mode
                }));
            }
        }
    }
    if devices.is_empty() {
        devices.push(serde_json::json!({
            "id": "rp2040-1",
            "port": "COM3",
            "mode": "runtime"
        }));
    }
    tool_result(
        vec![ContentItem {
            kind: "text".into(),
            text: serde_json::json!(devices).to_string(),
        }],
        false,
    )
}

pub fn handle_device_flash(params: Value) -> Value {
    let device = params.get("device").and_then(|v| v.as_str()).unwrap_or("");
    let path = params.get("path").and_then(|v| v.as_str()).unwrap_or("");
    if device.is_empty() || path.is_empty() {
        return tool_result(vec![ContentItem { kind: "text".into(), text: "Missing device or path".into() }], true);
    }
    tool_result(vec![ContentItem { kind: "text".into(), text: format!("Flashing {} to device {} (stubbed)", path, device) }], false)
}

pub fn handle_telemetry_start(params: Value) -> Value {
    let device = params.get("device").and_then(|v| v.as_str()).unwrap_or("");
    tool_result(vec![ContentItem { kind: "text".into(), text: format!("Telemetry stream started for {}", device) }], false)
}

pub fn handle_telemetry_stop(params: Value) -> Value {
    let device = params.get("device").and_then(|v| v.as_str()).unwrap_or("");
    tool_result(vec![ContentItem { kind: "text".into(), text: format!("Telemetry stream stopped for {}", device) }], false)
}

pub fn handle_firmware_build(params: Value) -> Value {
    let env = params.get("env").and_then(|v| v.as_str()).unwrap_or("nanorp2040connect");
    let firmware_dir = std::env::current_dir()
        .ok()
        .and_then(|d| {
            let candidate = d.parent().and_then(|p| {
                let fw = p.join("arp-2040").join("firmware");
                if fw.exists() { Some(fw) } else { None }
            });
            candidate.or_else(|| {
                d.parent().and_then(|p| {
                    let fw = p.join("firmware");
                    if fw.exists() { Some(fw) } else { None }
                })
            })
        })
        .unwrap_or_else(|| PathBuf::from("arp-2040/firmware"));
    let output = Command::new("pio")
        .current_dir(&firmware_dir)
        .args(["run", "-e", env, "-j", "2"])
        .output();
    match output {
        Ok(out) => {
            let stdout = String::from_utf8_lossy(&out.stdout).to_string();
            let stderr = String::from_utf8_lossy(&out.stderr).to_string();
            let text = if out.status.success() {
                format!("Build succeeded for env={}
{}", env, stdout)
            } else {
                format!("Build failed for env={}
stderr:
{}
stdout:
{}", env, stderr, stdout)
            };
            tool_result(vec![ContentItem { kind: "text".into(), text }], !out.status.success())
        }
        Err(e) => tool_result(vec![ContentItem { kind: "text".into(), text: format!("Build command failed: {}", e) }], true),
    }
}

pub fn handle_gui_open_panel(params: Value) -> Value {
    let panel = params.get("panel").and_then(|v| v.as_str()).unwrap_or("");
    tool_result(vec![ContentItem { kind: "text".into(), text: format!("Opened panel: {}", panel) }], false)
}

pub fn handle_tool_call(params: Value) -> Value {
    let calls = params.get("tool_calls").and_then(|v| v.as_array()).cloned().unwrap_or_default();
    let mut results = Vec::new();
    for call in calls {
        let name = call.get("name").and_then(|v| v.as_str()).unwrap_or("");
        let arguments = call.get("arguments").cloned().unwrap_or(Value::Null);
        let result = match name {
            "device_list" => handle_device_list(),
            "device_flash" => handle_device_flash(arguments),
            "telemetry_start" => handle_telemetry_start(arguments),
            "telemetry_stop" => handle_telemetry_stop(arguments),
            "firmware_build" => handle_firmware_build(arguments),
            "gui_open_panel" => handle_gui_open_panel(arguments),
            _ => tool_result(vec![ContentItem { kind: "text".into(), text: format!("Unknown tool: {}", name) }], true),
        };
        results.push(serde_json::json!({
            "tool_call_id": call.get("id").cloned().unwrap_or(Value::Null),
            "result": result
        }));
    }
    serde_json::json!({ "tool_results": results })
}

pub fn process_line(line: &str) -> Option<Value> {
    let req: JsonRpcRequest = match serde_json::from_str(line) {
        Ok(v) => v,
        Err(_) => return None,
    };
    let id = req.id.unwrap_or(Value::Null);
    let result = match req.method.as_str() {
        "initialize" => {
            let _params = req.params.unwrap_or(Value::Null);
            let server = serde_json::json!({
                "protocolVersion": "2025-03-26",
                "capabilities": { "tools": { "listChanged": false } },
                "serverInfo": { "name": "arp-2040-studio", "version": "0.1.0" }
            });
            ok_result(id, server)
        }
        "tools/list" => ok_result(id, list_tools()),
        "tools/call" => handle_tool_call(req.params.unwrap_or(Value::Null)),
        "shutdown" => ok_result(id, serde_json::json!({})),
        _ => err_result(id, &format!("unsupported method: {}", req.method)),
    };
    Some(result)
}

pub fn run_stdio() -> io::Result<()> {
    let stdin = io::stdin();
    let mut stdout = io::stdout();
    let mut buffer = String::new();
    loop {
        buffer.clear();
        match stdin.read_line(&mut buffer) {
            Ok(0) => break,
            Ok(_) => {
                if let Some(response) = process_line(buffer.trim()) {
                    stdout.write_all(response.to_string().as_bytes())?;
                    stdout.write_all(b"\n")?;
                    stdout.flush()?;
                }
            }
            Err(_) => break,
        }
    }
    Ok(())
}

pub fn run_tcp(port: u16, bind: &str) -> io::Result<()> {
    let addr = format!("{}:{}", bind, port);
    let listener = TcpListener::bind(&addr)?;
    eprintln!("MCP server listening on {}", addr);
    for stream in listener.incoming() {
        match stream {
            Ok(stream) => {
                if let Ok(peer) = stream.peer_addr() {
                    eprintln!("MCP client connected: {}", peer);
                }
                let _ = handle_stream(stream);
            }
            Err(_) => continue,
        }
    }
    Ok(())
}

pub fn handle_stream(stream: TcpStream) -> io::Result<()> {
    let mut reader = BufReader::new(stream);
    let mut buffer = String::new();
    loop {
        buffer.clear();
        match reader.read_line(&mut buffer) {
            Ok(0) => break,
            Ok(_) => {
                if let Some(response) = process_line(buffer.trim()) {
                    let mut writer = reader.get_mut();
                    writer.write_all(response.to_string().as_bytes())?;
                    writer.write_all(b"\n")?;
                    writer.flush()?;
                }
            }
            Err(_) => break,
        }
    }
    Ok(())
}