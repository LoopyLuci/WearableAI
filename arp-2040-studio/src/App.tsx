import { useEffect, useState, useRef, useCallback } from 'react';
import { invoke as tauriInvoke } from '@tauri-apps/api/core';

type Tab = 'devices' | 'telemetry' | 'models' | 'build' | 'cli' | 'settings';

interface Device {
  id: string;
  port: string;
  mode: 'runtime' | 'bootloader';
}

const LS_KEY = 'arp2040-layout';

type PaneSizes = {
  left: number;
  right: number;
};

function loadSizes(): PaneSizes {
  const saved = localStorage.getItem(LS_KEY);
  if (saved) {
    try {
      const parsed = JSON.parse(saved) as PaneSizes;
      if (typeof parsed.left === 'number' && typeof parsed.right === 'number') {
        return parsed;
      }
    } catch {}
  }
  return { left: 240, right: 300 };
}

export default function App() {
  const [tab, setTab] = useState<Tab>('devices');
  const [devices, setDevices] = useState<Device[]>([]);
  const [log, setLog] = useState('ARP-2040 Studio ready');
  const [cmd, setCmd] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const [sizes, setSizes] = useState<PaneSizes>(loadSizes);
  const [tauriReady, setTauriReady] = useState(false);
  const [resizing, setResizing] = useState<null | 'left' | 'right'>(null);
  const sizesRef = useRef(sizes);
  sizesRef.current = sizes;

  useEffect(() => {
    const savedLog = localStorage.getItem('arp2040-log');
    if (savedLog) setLog(savedLog);
  }, []);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
    localStorage.setItem('arp2040-log', log);
  }, [log]);

  useEffect(() => {
    localStorage.setItem(LS_KEY, JSON.stringify(sizes));
  }, [sizes]);

  useEffect(() => {
    setTauriReady(true);
  }, []);

  const append = useCallback((text: string) => {
    setLog((l) => l + '\n' + text);
  }, []);

  const mcpCall = useCallback(async (name: string, args: Record<string, any>) => {
    if (!tauriReady) return null;
    return tauriInvoke('mcp_call', { name, arguments: args });
  },
  [tauriReady]
  );

  const runCommand = async () => {
    const trimmed = cmd.trim();
    if (!trimmed) return;
    append('> ' + trimmed);
    setCmd('');
    try {
      const resp = await mcpCall('arduino.serial_command', { port: '', command: trimmed, baud: 921600, timeout_s: 4.0 });
      append(String(resp ?? '(empty)'));
    } catch (e) {
      append('Error: ' + e);
    }
  };

  const startResize = (side: 'left' | 'right') => (e: React.MouseEvent) => {
    e.preventDefault();
    setResizing(side);
  };

  useEffect(() => {
    if (!resizing) return;
    const onMove = (e: MouseEvent) => {
      const parent = document.querySelector('[data-resizable="true"]') as HTMLElement | null;
      if (!parent) return;
      const rect = parent.getBoundingClientRect();
      const x = e.clientX - rect.left;
      if (resizing === 'left') {
        const newLeft = Math.max(180, Math.min(x, 480));
        setSizes((s) => ({ ...s, left: newLeft }));
      } else {
        const newRight = Math.max(220, Math.min(rect.width - x, 520));
        setSizes((s) => ({ ...s, right: newRight }));
      }
    };
    const onUp = () => setResizing(null);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [resizing]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <header style={{ padding: 8, background: '#222', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ fontWeight: 600 }}>ARP-2040 Studio</div>
        <nav style={{ display: 'flex', gap: 8 }}>
          {(['devices', 'telemetry', 'models', 'build', 'cli', 'settings'] as Tab[]).map((t) => (
            <button key={t} onClick={() => setTab(t)} style={{ background: tab === t ? '#444' : '#222', color: '#fff', border: '1px solid #555', padding: '4px 10px', cursor: 'pointer' }}>
              {t}
            </button>
          ))}
        </nav>
      </header>

      <div
        data-resizable="true"
        style={{ display: 'flex', flex: 1, minHeight: 0, position: 'relative' }}
      >
        <aside style={{ width: sizes.left, background: '#1b1b1b', color: '#fff', padding: 8, borderRight: '1px solid #333', minWidth: 180, maxWidth: 480, overflow: 'auto' }}>
          {tab === 'devices' && (
            <>
              <h4 style={{ marginTop: 0 }}>Devices</h4>
              <button
                onClick={async () => {
                  append('Scanning...');
                  try {
                    append('Scan requested...');
                    const r:any = await mcpCall('arduino.detect', {});
                    append('Scan response: ' + JSON.stringify(r));
                    const text = r?.content?.[0]?.text;
                    const list = text ? JSON.parse(text) : [];
                    setDevices(list);
                    append('Found ' + list.length);
                  } catch (e) {
                    append('device_list failed: ' + e);
                  }
                }}
                style={{ width: '100%', marginBottom: 8 }}
              >
                Scan
              </button>
              <ul style={{ paddingLeft: 16, fontSize: 12, lineHeight: 1.6 }}>
                {devices.map((d) => (
                  <li key={d.id} style={{ cursor: 'pointer', color: selected === d.id ? '#0f0' : '#fff' }} onClick={() => { setSelected(d.id); append('Selected ' + d.id + ' on ' + d.port); }}>
                    {d.id} <span style={{ color: '#aaa' }}>({d.mode})</span>
                  </li>
                ))}
              </ul>
            </>
          )}
          {tab === 'models' && (
            <>
              <h4 style={{ marginTop: 0 }}>Models</h4>
              <ul style={{ paddingLeft: 16, fontSize: 12 }}>
                <li>audio_event.tflite</li>
                <li>gesture.tflite</li>
              </ul>
            </>
          )}
          {tab === 'build' && (
            <>
              <h4 style={{ marginTop: 0 }}>Firmware</h4>
              <button
                onClick={async () => {
                  append('Building...');
                  try {
                    const r:any = await mcpCall('arduino.build_and_flash', { source_path: 'Z:/Projects/WearableAI/arp-2040/firmware', fqbn: 'rp2040:rp2040:nano_rp2040_connect' });
                    append(String(r?.content?.[0]?.text ?? '(empty)'));
                  } catch (e) {
                    append('build failed: ' + e);
                  }
                }}
                style={{ width: '100%', marginBottom: 8 }}
              >
                Build firmware
              </button>
              <div style={{ fontSize: 12, color: '#aaa' }}>Artifacts: .elf, .uf2, .bin</div>
            </>
          )}
          {tab === 'settings' && (
            <>
              <h4 style={{ marginTop: 0 }}>Settings</h4>
              <div style={{ fontSize: 12 }}>
                <div>Theme: Dark</div>
                <div>MCP: stdio</div>
                <div>Serial baud: 921600</div>
              </div>
            </>
          )}
        </aside>

        <div
          onMouseDown={startResize('left')}
          style={{ width: 6, cursor: 'col-resize', background: '#333', borderLeft: '1px solid #444', borderRight: '1px solid #444' }}
        />

        <main style={{ flex: 1, background: '#000', color: '#fff', padding: 8, overflow: 'auto', minWidth: 120 }}>
          {tab === 'devices' && (
            <div>
              <h3 style={{ marginTop: 0 }}>Device Manager</h3>
              <div style={{ color: '#aaa' }}>Select a device or scan to detect RP2040 boards.</div>
              {selected && <div style={{ marginTop: 12 }}>Selected: <strong>{selected}</strong></div>}
            </div>
          )}
          {tab === 'telemetry' && (
            <div>
              <h3 style={{ marginTop: 0 }}>Telemetry</h3>
              <div style={{ color: '#555' }}>Live charts and data stream will appear here.</div>
            </div>
          )}
          {tab === 'models' && (
            <div>
              <h3 style={{ marginTop: 0 }}>Model Studio</h3>
              <div style={{ color: '#aaa' }}>Upload, inspect, run, and compare TFLite models.</div>
            </div>
          )}
          {tab === 'build' && (
            <div>
              <h3 style={{ marginTop: 0 }}>Build Log</h3>
              <pre style={{ background: '#111', padding: 8, height: 300, overflow: 'auto' }}>{log}</pre>
            </div>
          )}
          {tab === 'cli' && (
            <div>
              <h3 style={{ marginTop: 0 }}>CLI</h3>
              <div style={{ color: '#aaa' }}>Use the right panel for commands.</div>
            </div>
          )}
          {tab === 'settings' && (
            <div>
              <h3 style={{ marginTop: 0 }}>Settings</h3>
              <div style={{ color: '#aaa' }}>App configuration and preferences.</div>
            </div>
          )}
        </main>

        <div
          onMouseDown={startResize('right')}
          style={{ width: 6, cursor: 'col-resize', background: '#333', borderLeft: '1px solid #444', borderRight: '1px solid #444' }}
        />

        <aside style={{ width: sizes.right, background: '#111', color: '#fff', display: 'flex', flexDirection: 'column', borderLeft: '1px solid #333', minWidth: 220, maxWidth: 520, overflow: 'hidden' }}>
          <div style={{ padding: 8, background: '#222' }}>Console</div>
          <div ref={logRef} style={{ flex: 1, padding: 8, fontFamily: 'monospace', fontSize: 12, overflow: 'auto', whiteSpace: 'pre-wrap' }}>{log}</div>
          <div style={{ display: 'flex', borderTop: '1px solid #333' }}>
            <input
              value={cmd}
              onChange={(e) => setCmd(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && runCommand()}
              style={{ flex: 1, background: '#000', color: '#fff', border: 'none', padding: 8 }}
              placeholder={tauriReady ? 'Enter command...' : 'Tauri IPC unavailable'}
            />
            <button onClick={runCommand} style={{ background: '#222', color: '#fff', border: 'none' }}>Run</button>
          </div>
        </aside>
      </div>
    </div>
  );
}
