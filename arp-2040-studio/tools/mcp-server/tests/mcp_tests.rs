use arp_2040_mcp::*;

#[test]
fn initialize_returns_server_info() {
    let resp = process_line(r#"{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"0.1"}}}"#);
    assert!(resp.is_some());
    let value = resp.unwrap();
    assert_eq!(value.get("jsonrpc").and_then(|v| v.as_str()), Some("2.0"));
    assert_eq!(value.get("id").and_then(|v| v.as_i64()), Some(1));
    let result = value.get("result").expect("result");
    assert_eq!(result.get("protocolVersion").and_then(|v| v.as_str()), Some("2025-03-26"));
    assert!(result.get("capabilities").is_some());
    assert!(result.get("serverInfo").is_some());
}

#[test]
fn list_tools_contains_device_list() {
    let resp = process_line(r#"{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}"#);
    assert!(resp.is_some());
    let value = resp.unwrap();
    let tools = value.get("result").and_then(|r| r.get("tools")).and_then(|t| t.as_array()).expect("tools array");
    let names: Vec<&str> = tools.iter().filter_map(|t| t.get("name").and_then(|n| n.as_str())).collect();
    assert!(names.contains(&"device_list"));
    assert!(names.contains(&"device_flash"));
    assert!(names.contains(&"telemetry_start"));
    assert!(names.contains(&"firmware_build"));
    assert!(names.contains(&"gui_open_panel"));
}

#[test]
fn device_list_returns_text_content() {
    let resp = process_line(r#"{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"tool_calls":[{"id":"t1","name":"device_list","arguments":{}}]}}"#);
    assert!(resp.is_some());
    let value = resp.unwrap();
    let tool_results = value.get("tool_results").and_then(|t| t.as_array()).expect("tool_results");
    assert_eq!(tool_results.len(), 1);
    let result = tool_results[0].get("result").expect("result");
    let content = result.get("content").and_then(|c| c.as_array()).expect("content");
    assert_eq!(content.len(), 1);
    assert_eq!(content[0].get("type").and_then(|t| t.as_str()), Some("text"));
    let text = content[0].get("text").and_then(|t| t.as_str()).expect("text");
    let devices: Vec<serde_json::Value> = serde_json::from_str(text).expect("device list JSON");
    assert!(!devices.is_empty());
    let first = &devices[0];
    assert!(first.get("id").and_then(|v| v.as_str()).is_some());
    assert!(first.get("port").and_then(|v| v.as_str()).is_some());
    assert!(first.get("mode").and_then(|v| v.as_str()).is_some());
}

#[test]
fn unknown_tool_returns_error() {
    let resp = process_line(r#"{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"tool_calls":[{"id":"t2","name":"does_not_exist","arguments":{}}]}}"#);
    assert!(resp.is_some());
    let value = resp.unwrap();
    let tool_results = value.get("tool_results").and_then(|t| t.as_array()).expect("tool_results");
    let result = tool_results[0].get("result").expect("result");
    assert_eq!(result.get("is_error").and_then(|v| v.as_bool()), Some(true));
    let content = result.get("content").and_then(|c| c.as_array()).expect("content");
    assert!(content[0].get("text").and_then(|t| t.as_str()).unwrap().contains("Unknown tool"));
}
