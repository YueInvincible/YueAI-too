use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::collections::HashMap;
use std::env;
use std::fs;
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStderr, ChildStdin, ChildStdout, Command, Stdio};
use std::sync::mpsc::{self, Receiver, Sender};
use std::sync::{Arc, Mutex};
use std::thread::{self, JoinHandle};
use std::time::Duration;

const DEFAULT_TIMEOUT_MS: u64 = 15_000;
const EVENT_QUEUE_LIMIT: usize = 512;

#[derive(Debug, Clone, Deserialize)]
pub struct BridgeRequestPayload {
    pub method: String,
    #[serde(default)]
    pub params: Value,
    #[serde(default)]
    pub timeout_ms: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BridgeResponse {
    pub ok: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct BridgeRuntimeInfo {
    pub mode: String,
    pub core_transport: String,
    pub note: String,
    pub process_started: bool,
    pub pending_requests: usize,
    pub queued_events: usize,
    pub last_error: Option<String>,
    pub diagnostic_enabled: bool,
    pub diagnostic_auto_exit_ms: Option<u64>,
}

#[derive(Debug, Clone, Serialize)]
pub struct BridgeEventBatch {
    pub events: Vec<Value>,
}

#[derive(Debug)]
pub struct BridgeState {
    inner: Mutex<BridgeController>,
}

#[derive(Debug)]
struct BridgeController {
    process: Option<CoreBridgeProcess>,
    next_request_id: u64,
}

#[derive(Debug)]
struct CoreBridgeProcess {
    child: Child,
    stdin: ChildStdin,
    pending: Arc<Mutex<HashMap<String, Sender<BridgeResponse>>>>,
    event_queue: Arc<Mutex<Vec<Value>>>,
    last_error: Arc<Mutex<Option<String>>>,
    stdout_thread: Option<JoinHandle<()>>,
    stderr_thread: Option<JoinHandle<()>>,
}

#[derive(Debug, Deserialize)]
struct WireResponse {
    id: Option<String>,
    ok: Option<bool>,
    result: Option<Value>,
    error: Option<String>,
    event: Option<Value>,
}

impl Default for BridgeState {
    fn default() -> Self {
        Self {
            inner: Mutex::new(BridgeController {
                process: None,
                next_request_id: 1,
            }),
        }
    }
}

#[tauri::command]
pub fn bridge_runtime_info(state: tauri::State<'_, BridgeState>) -> BridgeRuntimeInfo {
    let guard = match state.inner.lock() {
        Ok(guard) => guard,
        Err(_) => {
            return BridgeRuntimeInfo {
                mode: "stdio-jsonl".to_string(),
                core_transport: "lock_poisoned".to_string(),
                note: "Bridge controller lock poisoned".to_string(),
                process_started: false,
                pending_requests: 0,
                queued_events: 0,
                last_error: Some("bridge controller lock poisoned".to_string()),
                diagnostic_enabled: desktop_diagnostic_output_path().is_some(),
                diagnostic_auto_exit_ms: desktop_diagnostic_auto_exit_ms(),
            };
        }
    };

    match guard.process.as_ref() {
        Some(process) => BridgeRuntimeInfo {
            mode: "stdio-jsonl".to_string(),
            core_transport: "spawned".to_string(),
            note:
                "Rust bridge is configured to talk to `python -m yue_core serve` over stdio JSONL."
                    .to_string(),
            process_started: true,
            pending_requests: process.pending_count(),
            queued_events: process.event_count(),
            last_error: process.last_error(),
            diagnostic_enabled: desktop_diagnostic_output_path().is_some(),
            diagnostic_auto_exit_ms: desktop_diagnostic_auto_exit_ms(),
        },
        None => BridgeRuntimeInfo {
            mode: "stdio-jsonl".to_string(),
            core_transport: "not_started".to_string(),
            note: "Core bridge is lazy-started on first request.".to_string(),
            process_started: false,
            pending_requests: 0,
            queued_events: 0,
            last_error: None,
            diagnostic_enabled: desktop_diagnostic_output_path().is_some(),
            diagnostic_auto_exit_ms: desktop_diagnostic_auto_exit_ms(),
        },
    }
}

#[tauri::command]
pub fn bridge_request(
    payload: BridgeRequestPayload,
    state: tauri::State<'_, BridgeState>,
) -> BridgeResponse {
    let mut controller = match state.inner.lock() {
        Ok(guard) => guard,
        Err(_) => return error_response("bridge controller lock poisoned"),
    };

    if controller.process.is_none() {
        let process = match CoreBridgeProcess::spawn() {
            Ok(process) => process,
            Err(error) => return error_response(error),
        };
        controller.process = Some(process);
    }

    let request_id = format!("desktop-bridge-{}", controller.next_request_id);
    controller.next_request_id += 1;

    let request = json!({
        "id": request_id,
        "method": payload.method,
        "params": payload.params,
    });

    let timeout_ms = payload.timeout_ms.unwrap_or(DEFAULT_TIMEOUT_MS);
    match controller
        .process
        .as_mut()
        .expect("process must exist after lazy start")
        .send_request(&request_id, &request, timeout_ms)
    {
        Ok(response) => response,
        Err(error) => error_response(error),
    }
}

#[tauri::command]
pub fn bridge_drain_events(state: tauri::State<'_, BridgeState>) -> BridgeEventBatch {
    let controller = match state.inner.lock() {
        Ok(guard) => guard,
        Err(_) => return BridgeEventBatch { events: Vec::new() },
    };

    let events = controller
        .process
        .as_ref()
        .map(CoreBridgeProcess::drain_events)
        .unwrap_or_default();
    BridgeEventBatch { events }
}

#[tauri::command]
pub fn bridge_shutdown_core(state: tauri::State<'_, BridgeState>) -> BridgeResponse {
    let mut controller = match state.inner.lock() {
        Ok(guard) => guard,
        Err(_) => return error_response("bridge controller lock poisoned"),
    };

    if let Some(mut process) = controller.process.take() {
        match process.shutdown() {
            Ok(()) => ok(json!({ "stopped": true })),
            Err(error) => error_response(error),
        }
    } else {
        ok(json!({ "stopped": false }))
    }
}

#[tauri::command]
pub fn bridge_report_diagnostic(payload: Value) -> BridgeResponse {
    let Some(path) = desktop_diagnostic_output_path() else {
        return error_response("desktop diagnostic output path is not configured");
    };

    let serialized = match serde_json::to_string(&payload) {
        Ok(value) => value,
        Err(error) => {
            return error_response(format!("failed to serialize diagnostic payload: {error}"));
        }
    };

    if let Some(parent) = path.parent() {
        if let Err(error) = fs::create_dir_all(parent) {
            return error_response(format!("failed to create diagnostic directory: {error}"));
        }
    }
    let mut line = serialized;
    if !line.ends_with('\n') {
        line.push('\n');
    }
    if let Err(error) = fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&path)
        .and_then(|mut file| std::io::Write::write_all(&mut file, line.as_bytes()))
    {
        return error_response(format!("failed to write diagnostic payload: {error}"));
    }

    ok(json!({ "written": true }))
}

impl CoreBridgeProcess {
    fn spawn() -> Result<Self, String> {
        let root = repo_root()?;
        let python = env::var("YUE_PYTHON_BIN").unwrap_or_else(|_| "python".to_string());
        let mut command = Command::new(python);
        command
            .arg("-m")
            .arg("yue_core")
            .args(spawn_core_config_args(&root))
            .arg("serve")
            .current_dir(&root)
            .env("PYTHONDONTWRITEBYTECODE", "1")
            .env("PYTHONPATH", pythonpath_for_root(&root))
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        let mut child = command
            .spawn()
            .map_err(|error| format!("failed to spawn yue_core serve: {error}"))?;

        let stdin = child
            .stdin
            .take()
            .ok_or_else(|| "failed to capture core stdin".to_string())?;
        let stdout = child
            .stdout
            .take()
            .ok_or_else(|| "failed to capture core stdout".to_string())?;
        let stderr = child
            .stderr
            .take()
            .ok_or_else(|| "failed to capture core stderr".to_string())?;

        let pending = Arc::new(Mutex::new(HashMap::new()));
        let event_queue = Arc::new(Mutex::new(Vec::new()));
        let last_error = Arc::new(Mutex::new(None));

        let stdout_thread = Some(spawn_stdout_thread(
            stdout,
            Arc::clone(&pending),
            Arc::clone(&event_queue),
            Arc::clone(&last_error),
        ));
        let stderr_thread = Some(spawn_stderr_thread(stderr, Arc::clone(&last_error)));

        Ok(Self {
            child,
            stdin,
            pending,
            event_queue,
            last_error,
            stdout_thread,
            stderr_thread,
        })
    }

    fn send_request(
        &mut self,
        request_id: &str,
        request: &Value,
        timeout_ms: u64,
    ) -> Result<BridgeResponse, String> {
        let (sender, receiver): (Sender<BridgeResponse>, Receiver<BridgeResponse>) =
            mpsc::channel();
        {
            let mut pending = self
                .pending
                .lock()
                .map_err(|_| "pending request registry lock poisoned".to_string())?;
            pending.insert(request_id.to_string(), sender);
        }

        let serialized = serde_json::to_string(request)
            .map_err(|error| format!("failed to serialize bridge request: {error}"))?;
        if let Err(error) = writeln!(self.stdin, "{serialized}") {
            self.remove_pending(request_id);
            return Err(format!("failed to write bridge request: {error}"));
        }
        if let Err(error) = self.stdin.flush() {
            self.remove_pending(request_id);
            return Err(format!("failed to flush bridge request: {error}"));
        }

        match receiver.recv_timeout(Duration::from_millis(timeout_ms)) {
            Ok(response) => Ok(response),
            Err(_) => {
                self.remove_pending(request_id);
                Err(format!("bridge request timed out after {timeout_ms} ms"))
            }
        }
    }

    fn remove_pending(&self, request_id: &str) {
        if let Ok(mut pending) = self.pending.lock() {
            pending.remove(request_id);
        }
    }

    fn drain_events(&self) -> Vec<Value> {
        let mut queue = match self.event_queue.lock() {
            Ok(queue) => queue,
            Err(_) => return Vec::new(),
        };
        queue.drain(..).collect()
    }

    fn event_count(&self) -> usize {
        self.event_queue
            .lock()
            .map(|queue| queue.len())
            .unwrap_or(0)
    }

    fn pending_count(&self) -> usize {
        self.pending
            .lock()
            .map(|pending| pending.len())
            .unwrap_or(0)
    }

    fn last_error(&self) -> Option<String> {
        self.last_error.lock().ok().and_then(|value| value.clone())
    }

    fn shutdown(&mut self) -> Result<(), String> {
        if let Ok(mut pending) = self.pending.lock() {
            for (_, sender) in pending.drain() {
                let _ = sender.send(error_response("core bridge shutting down"));
            }
        }

        let _ = self.stdin.flush();
        if let Err(error) = self.child.kill() {
            let message = format!("failed to kill core bridge process: {error}");
            remember_error(&self.last_error, &message);
            return Err(message);
        }
        let _ = self.child.wait();

        if let Some(handle) = self.stdout_thread.take() {
            let _ = handle.join();
        }
        if let Some(handle) = self.stderr_thread.take() {
            let _ = handle.join();
        }
        Ok(())
    }
}

impl Drop for CoreBridgeProcess {
    fn drop(&mut self) {
        let _ = self.shutdown();
    }
}

fn spawn_stdout_thread(
    stdout: ChildStdout,
    pending: Arc<Mutex<HashMap<String, Sender<BridgeResponse>>>>,
    event_queue: Arc<Mutex<Vec<Value>>>,
    last_error: Arc<Mutex<Option<String>>>,
) -> JoinHandle<()> {
    thread::spawn(move || {
        let reader = BufReader::new(stdout);
        for line_result in reader.lines() {
            let line = match line_result {
                Ok(line) => line,
                Err(error) => {
                    remember_error(
                        &last_error,
                        &format!("failed to read core stdout line: {error}"),
                    );
                    break;
                }
            };
            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }
            match serde_json::from_str::<WireResponse>(trimmed) {
                Ok(wire) => route_wire_message(wire, &pending, &event_queue),
                Err(error) => {
                    remember_error(
                        &last_error,
                        &format!("failed to parse core stdout JSON: {error}"),
                    );
                }
            }
        }
    })
}

fn spawn_stderr_thread(
    stderr: ChildStderr,
    last_error: Arc<Mutex<Option<String>>>,
) -> JoinHandle<()> {
    thread::spawn(move || {
        let reader = BufReader::new(stderr);
        for line_result in reader.lines() {
            let line = match line_result {
                Ok(line) => line,
                Err(error) => {
                    remember_error(
                        &last_error,
                        &format!("failed to read core stderr line: {error}"),
                    );
                    break;
                }
            };
            if !line.trim().is_empty() {
                remember_error(&last_error, &line);
            }
        }
    })
}

fn route_wire_message(
    wire: WireResponse,
    pending: &Arc<Mutex<HashMap<String, Sender<BridgeResponse>>>>,
    event_queue: &Arc<Mutex<Vec<Value>>>,
) {
    if let Some(event) = wire.event {
        if let Ok(mut queue) = event_queue.lock() {
            queue.push(event);
            if queue.len() > EVENT_QUEUE_LIMIT {
                let overflow = queue.len() - EVENT_QUEUE_LIMIT;
                queue.drain(0..overflow);
            }
        }
        return;
    }

    let Some(id) = wire.id else {
        return;
    };
    let response = BridgeResponse {
        ok: wire.ok.unwrap_or(false),
        result: wire.result,
        error: wire.error,
    };
    if let Ok(mut pending) = pending.lock() {
        if let Some(sender) = pending.remove(&id) {
            let _ = sender.send(response);
        }
    }
}

fn repo_root() -> Result<PathBuf, String> {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest_dir
        .parent()
        .and_then(Path::parent)
        .map(Path::to_path_buf)
        .ok_or_else(|| "failed to resolve repository root from CARGO_MANIFEST_DIR".to_string())
}

fn pythonpath_for_root(root: &Path) -> String {
    let separator = if cfg!(windows) { ";" } else { ":" };
    format!("{}{}.", root.join("src").display(), separator)
}

#[cfg(not(test))]
fn core_config_args(root: &Path) -> Vec<String> {
    resolve_core_config_path(root)
        .map(|path| vec!["--config".to_string(), path.display().to_string()])
        .unwrap_or_default()
}

#[cfg(test)]
fn spawn_core_config_args(root: &Path) -> Vec<String> {
    env::var_os("YUE_CORE_CONFIG")
        .map(PathBuf::from)
        .and_then(|path| {
            let resolved = if path.is_absolute() {
                path
            } else {
                root.join(path)
            };
            resolved.is_file().then_some(resolved)
        })
        .map(|path| vec!["--config".to_string(), path.display().to_string()])
        .unwrap_or_default()
}

#[cfg(not(test))]
fn spawn_core_config_args(root: &Path) -> Vec<String> {
    core_config_args(root)
}

fn resolve_core_config_path(root: &Path) -> Option<PathBuf> {
    let explicit = env::var_os("YUE_CORE_CONFIG").map(PathBuf::from);
    let candidates = explicit.into_iter().chain([
        root.join("config.local.toml"),
        root.join("config.example.toml"),
    ]);
    for candidate in candidates {
        let resolved = if candidate.is_absolute() {
            candidate
        } else {
            root.join(candidate)
        };
        if resolved.is_file() {
            return Some(resolved);
        }
    }
    None
}

fn remember_error(target: &Arc<Mutex<Option<String>>>, message: &str) {
    if let Ok(mut slot) = target.lock() {
        *slot = Some(message.to_string());
    }
}

fn desktop_diagnostic_output_path() -> Option<PathBuf> {
    env::var_os("YUE_DESKTOP_DIAGNOSTIC_PATH").map(PathBuf::from)
}

fn desktop_diagnostic_auto_exit_ms() -> Option<u64> {
    env::var("YUE_DESKTOP_AUTO_EXIT_MS")
        .ok()
        .and_then(|value| value.parse::<u64>().ok())
}

fn ok(result: Value) -> BridgeResponse {
    BridgeResponse {
        ok: true,
        result: Some(result),
        error: None,
    }
}

fn error_response(message: impl Into<String>) -> BridgeResponse {
    BridgeResponse {
        ok: false,
        result: None,
        error: Some(message.into()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn temp_test_dir(name: &str) -> PathBuf {
        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system time before epoch")
            .as_nanos();
        let path = env::temp_dir().join(format!("yue-bridge-{name}-{unique}"));
        fs::create_dir_all(&path).expect("create temp test dir");
        path
    }

    #[test]
    fn bridge_process_round_trips_desktop_request_and_receives_events() {
        let mut process = CoreBridgeProcess::spawn().expect("spawn core bridge");
        let request_id = "test-attach";
        let request = json!({
            "id": request_id,
            "method": "desktop.attach",
            "params": {
                "session_id": "rust-test",
                "metadata": {"surface": "cargo-test"},
            }
        });

        let response = process
            .send_request(request_id, &request, 10_000)
            .expect("desktop.attach response");

        assert!(response.ok);
        let result = response.result.expect("attach result");
        assert_eq!(result["session_id"], "rust-test");

        std::thread::sleep(Duration::from_millis(100));
        let events = process.drain_events();
        assert!(
            events
                .iter()
                .any(|event| event["topic"] == "desktop.session.attached")
        );
        assert!(
            events
                .iter()
                .any(|event| event["topic"] == "desktop.state.changed")
        );

        process.shutdown().expect("bridge shutdown");
    }

    #[test]
    fn bridge_process_round_trips_conversation_and_receives_conversation_events() {
        let mut process = CoreBridgeProcess::spawn().expect("spawn core bridge");

        let create_request = json!({
            "id": "create-conversation",
            "method": "conversations.create",
            "params": {
                "title": "Rust bridge test"
            }
        });
        let create_response = process
            .send_request("create-conversation", &create_request, 10_000)
            .expect("conversations.create response");
        assert!(create_response.ok);
        let conversation_id = create_response.result.expect("conversation result")["id"]
            .as_str()
            .expect("conversation id")
            .to_string();

        let send_request = json!({
            "id": "send-conversation",
            "method": "conversations.send",
            "params": {
                "conversation_id": conversation_id,
                "content": "hello from rust bridge",
                "run_id": "rust-bridge-run"
            }
        });
        let send_response = process
            .send_request("send-conversation", &send_request, 10_000)
            .expect("conversations.send response");
        assert!(send_response.ok);
        let send_result = send_response.result.expect("send result");
        assert_eq!(send_result["run_id"], "rust-bridge-run");
        assert_eq!(
            send_result["message"]["content"],
            "Echo: hello from rust bridge"
        );

        std::thread::sleep(Duration::from_millis(100));
        let events = process.drain_events();
        assert!(
            events
                .iter()
                .any(|event| event["topic"] == "conversation.created")
        );
        assert!(
            events
                .iter()
                .any(|event| event["topic"] == "conversation.run.started")
        );
        assert!(
            events
                .iter()
                .any(|event| event["topic"] == "conversation.delta")
        );
        assert!(
            events
                .iter()
                .any(|event| event["topic"] == "conversation.run.completed")
        );

        process.shutdown().expect("bridge shutdown");
    }

    #[test]
    fn bridge_process_handles_multiple_requests_before_shutdown() {
        let mut process = CoreBridgeProcess::spawn().expect("spawn core bridge");

        let attach_request = json!({
            "id": "attach-multi",
            "method": "desktop.attach",
            "params": {
                "session_id": "rust-multi",
                "metadata": {"surface": "cargo-test"},
            }
        });
        let attach_response = process
            .send_request("attach-multi", &attach_request, 10_000)
            .expect("desktop.attach response");
        assert!(attach_response.ok);

        let create_request = json!({
            "id": "create-multi",
            "method": "conversations.create",
            "params": {
                "title": "Rust bridge multi request test"
            }
        });
        let create_response = process
            .send_request("create-multi", &create_request, 10_000)
            .expect("conversations.create response");
        assert!(create_response.ok);
        let conversation_id = create_response.result.expect("conversation result")["id"]
            .as_str()
            .expect("conversation id")
            .to_string();

        let first_send_request = json!({
            "id": "send-multi-1",
            "method": "conversations.send",
            "params": {
                "conversation_id": conversation_id,
                "content": "first message",
                "run_id": "rust-multi-run-1"
            }
        });
        let first_send_response = process
            .send_request("send-multi-1", &first_send_request, 10_000)
            .expect("first send response");
        assert!(first_send_response.ok);
        assert_eq!(
            first_send_response.result.expect("first send result")["message"]["content"],
            "Echo: first message"
        );

        let second_send_request = json!({
            "id": "send-multi-2",
            "method": "conversations.send",
            "params": {
                "conversation_id": conversation_id,
                "content": "second message",
                "run_id": "rust-multi-run-2"
            }
        });
        let second_send_response = process
            .send_request("send-multi-2", &second_send_request, 10_000)
            .expect("second send response");
        assert!(second_send_response.ok);
        assert_eq!(
            second_send_response.result.expect("second send result")["message"]["content"],
            "Echo: second message"
        );

        std::thread::sleep(Duration::from_millis(150));
        let events = process.drain_events();
        let completed_runs = events
            .iter()
            .filter(|event| event["topic"] == "conversation.run.completed")
            .count();
        assert!(
            events
                .iter()
                .any(|event| event["topic"] == "desktop.session.attached")
        );
        assert!(completed_runs >= 2);

        process.shutdown().expect("bridge shutdown");
    }

    #[test]
    fn resolve_core_config_path_prefers_local_then_example() {
        let root = temp_test_dir("config-priority");
        let local = root.join("config.local.toml");
        let example = root.join("config.example.toml");
        fs::write(&example, "[core]\nlog_level = \"INFO\"\n").expect("write example config");
        assert_eq!(resolve_core_config_path(&root), Some(example.clone()));

        fs::write(&local, "[core]\nlog_level = \"DEBUG\"\n").expect("write local config");
        assert_eq!(resolve_core_config_path(&root), Some(local));

        fs::remove_dir_all(&root).expect("cleanup temp test dir");
    }
}
