#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod bridge;

use std::{
    env, fs,
    path::PathBuf,
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
    },
    thread,
    time::Duration,
};

use tauri::Manager;

const DESKTOP_GLOBAL_INVOKE_SCRIPT: &str = r#"
(() => {
  const internals = window.__TAURI_INTERNALS__ = window.__TAURI_INTERNALS__ || {};
  const tauriGlobal = window.__TAURI__ = window.__TAURI__ || {};
  tauriGlobal.core = tauriGlobal.core || {};

  if (!internals.transformCallback || !internals.runCallback || !internals.unregisterCallback) {
    const callbacks = new Map();
    const uid = () => window.crypto.getRandomValues(new Uint32Array(1))[0];

    internals.transformCallback = (callback, once = false) => {
      const identifier = uid();
      callbacks.set(identifier, (data) => {
        if (once) {
          internals.unregisterCallback(identifier);
        }
        if (callback) {
          callback(data);
        }
      });
      return identifier;
    };

    internals.unregisterCallback = (identifier) => {
      callbacks.delete(identifier);
    };

    internals.runCallback = (identifier, data) => {
      const callback = callbacks.get(identifier);
      if (callback) {
        callback(data);
      }
    };
  }

  if (!internals.invoke) {
    const ipcQueue = [];
    let waitingForIpc = false;

    const flushIpcQueue = () => {
      if ('ipc' in internals) {
        for (const action of ipcQueue.splice(0, ipcQueue.length)) {
          action();
        }
        waitingForIpc = false;
      } else {
        window.setTimeout(flushIpcQueue, 50);
      }
    };

    internals.invoke = (cmd, payload = {}, options) => new Promise((resolve, reject) => {
      const callback = internals.transformCallback((result) => {
        resolve(result);
        internals.unregisterCallback(error);
      }, true);
      const error = internals.transformCallback((reason) => {
        reject(reason);
        internals.unregisterCallback(callback);
      }, true);

      const action = () => {
        internals.ipc({
          cmd,
          callback,
          error,
          payload,
          options,
        });
      };

      if ('ipc' in internals) {
        action();
      } else {
        ipcQueue.push(action);
        if (!waitingForIpc) {
          waitingForIpc = true;
          flushIpcQueue();
        }
      }
    });
  }

  if (!tauriGlobal.core.invoke) {
    tauriGlobal.core.invoke = internals.invoke;
  }
})();
"#;

#[derive(Clone, Debug, Default)]
struct DiagnosticConfig {
    emit_stdout: bool,
    output_path: Option<PathBuf>,
    sample_delay_ms: u64,
    auto_exit_ms: Option<u64>,
    probe_retries: u32,
}

impl DiagnosticConfig {
    fn from_env() -> Self {
        let emit_stdout = env::var("YUE_DESKTOP_DIAGNOSTIC").ok().as_deref() == Some("1");
        let output_path = env::var_os("YUE_DESKTOP_DIAGNOSTIC_PATH").map(PathBuf::from);
        let sample_delay_ms = env::var("YUE_DESKTOP_DIAGNOSTIC_DELAY_MS")
            .ok()
            .and_then(|value| value.parse::<u64>().ok())
            .unwrap_or(2_000);
        let auto_exit_ms = env::var("YUE_DESKTOP_AUTO_EXIT_MS")
            .ok()
            .and_then(|value| value.parse::<u64>().ok());
        let probe_retries = env::var("YUE_DESKTOP_DIAGNOSTIC_RETRIES")
            .ok()
            .and_then(|value| value.parse::<u32>().ok())
            .filter(|value| *value > 0)
            .unwrap_or(3);

        Self {
            emit_stdout,
            output_path,
            sample_delay_ms,
            auto_exit_ms,
            probe_retries,
        }
    }

    fn enabled(&self) -> bool {
        self.emit_stdout || self.output_path.is_some()
    }
}

fn write_diagnostic_output(path: &PathBuf, payload: &str) {
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    let _ = fs::write(path, payload);
}

fn write_diagnostic_stage(path: &PathBuf, stage: &str, detail: Option<&str>) {
    let escaped_detail = detail
        .map(|value| serde_json::to_string(value).unwrap_or_else(|_| "\"detail\"".to_string()))
        .unwrap_or_else(|| "null".to_string());
    let payload = format!(r#"{{"stage":"{stage}","detail":{escaped_detail}}}"#);
    write_diagnostic_output(path, &payload);
}

fn configure_builder<R: tauri::Runtime>(builder: tauri::Builder<R>) -> tauri::Builder<R> {
    builder
        .append_invoke_initialization_script(DESKTOP_GLOBAL_INVOKE_SCRIPT)
        .manage(bridge::BridgeState::default())
        .on_page_load(|window, _| {
            if let Some(path) = DiagnosticConfig::from_env().output_path.as_ref() {
                write_diagnostic_stage(path, "page_load", None);
            }
            let probe_script = r#"
                (() => {
                  const payload = {
                    stage: "page_load_probe",
                    readyState: document.readyState,
                    hasTauri: typeof window.__TAURI__ !== "undefined",
                    hasInternals: typeof window.__TAURI_INTERNALS__ !== "undefined",
                    hasInvoke: typeof window.__TAURI__?.core?.invoke === "function",
                    hasIpc: typeof window.__TAURI_INTERNALS__?.ipc === "function",
                    bridgeLine: document.querySelector('#bridge-line')?.textContent ?? null
                  };
                  if (typeof window.__TAURI__?.core?.invoke === "function") {
                    window.__TAURI__.core.invoke("bridge_report_diagnostic", { payload }).catch(() => {});
                  }
                })();
            "#;
            let _ = window.eval(probe_script);
        })
        .setup(|app| {
            let diagnostic = DiagnosticConfig::from_env();
            if diagnostic.enabled() {
                if let Some(path) = diagnostic.output_path.as_ref() {
                    write_diagnostic_stage(path, "setup", None);
                }
                if let Some(window) = app.get_webview_window("main") {
                    let window = window.clone();
                    let app_handle = app.handle().clone();
                    let diagnostic_path = diagnostic.output_path.clone();
                    thread::spawn(move || {
                        if let Some(path) = diagnostic_path.as_ref() {
                            write_diagnostic_stage(path, "scheduled", None);
                        }
                        let callback_seen = Arc::new(AtomicBool::new(false));
                        let script = r#"
                            (() => JSON.stringify({
                              readyState: document.readyState,
                              hasTauri: typeof window.__TAURI__ !== 'undefined',
                              hasInternals: typeof window.__TAURI_INTERNALS__ !== 'undefined',
                              hasInvoke: typeof window.__TAURI_INTERNALS__?.invoke === 'function',
                              hasIpc: typeof window.__TAURI_INTERNALS__?.ipc === 'function',
                              locationHref: window.location.href,
                              bridgeLine: document.querySelector('#bridge-line')?.textContent ?? null
                            }))()
                        "#;
                        for attempt in 1..=diagnostic.probe_retries {
                            thread::sleep(Duration::from_millis(diagnostic.sample_delay_ms));
                            if callback_seen.load(Ordering::SeqCst) {
                                break;
                            }
                            if let Some(path) = diagnostic_path.as_ref() {
                                let detail = format!(
                                    "attempt {attempt}/{}",
                                    diagnostic.probe_retries
                                );
                                write_diagnostic_stage(path, "probe_dispatching", Some(&detail));
                            }
                            let callback_seen_for_eval = callback_seen.clone();
                            let callback_seen_for_callback = callback_seen.clone();
                            let diagnostic_for_callback = diagnostic.clone();
                            let app_handle_for_callback = app_handle.clone();
                            if let Err(error) = window.eval_with_callback(script, move |payload| {
                                callback_seen_for_callback.store(true, Ordering::SeqCst);
                                if diagnostic_for_callback.emit_stdout {
                                    println!("YUE_DESKTOP_DIAGNOSTIC={payload}");
                                }
                                if let Some(path) = diagnostic_for_callback.output_path.as_ref() {
                                    write_diagnostic_output(path, &payload);
                                }
                                if let Some(delay_ms) = diagnostic_for_callback.auto_exit_ms {
                                    let app_handle = app_handle_for_callback.clone();
                                    thread::spawn(move || {
                                        thread::sleep(Duration::from_millis(delay_ms));
                                        app_handle.exit(0);
                                    });
                                }
                            }) {
                                if let Some(path) = diagnostic_path.as_ref() {
                                    let detail = format!(
                                        "attempt {attempt}/{}: {}",
                                        diagnostic.probe_retries, error
                                    );
                                    write_diagnostic_stage(path, "eval_error", Some(&detail));
                                }
                                break;
                            }
                            if callback_seen_for_eval.load(Ordering::SeqCst) {
                                break;
                            }
                            if let Some(path) = diagnostic_path.as_ref() {
                                let detail =
                                    format!("attempt {attempt}/{}", diagnostic.probe_retries);
                                write_diagnostic_stage(path, "probe_dispatched", Some(&detail));
                            }
                        }
                        if !callback_seen.load(Ordering::SeqCst) {
                            if let Some(path) = diagnostic_path.as_ref() {
                                let detail = format!(
                                    "no callback after {} attempt(s)",
                                    diagnostic.probe_retries
                                );
                                write_diagnostic_stage(path, "probe_timeout", Some(&detail));
                            }
                        }
                    });
                } else if let Some(path) = diagnostic.output_path.as_ref() {
                    write_diagnostic_stage(path, "missing_window", None);
                }
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            bridge::bridge_request,
            bridge::bridge_runtime_info,
            bridge::bridge_drain_events,
            bridge::bridge_report_diagnostic,
            bridge::bridge_shutdown_core
        ])
}

fn main() {
    configure_builder(tauri::Builder::default())
        .run(tauri::generate_context!())
        .expect("failed to run Yue Desktop");
}

#[cfg(test)]
mod tests {
    use std::path::PathBuf;

    use serde_json::{Value, json};
    use tauri::{
        ipc::{CallbackFn, InvokeBody},
        test::{INVOKE_KEY, get_ipc_response, mock_builder, mock_context, noop_assets},
        webview::InvokeRequest,
    };

    use super::DiagnosticConfig;
    use super::configure_builder;

    fn local_invoke_url() -> &'static str {
        if cfg!(windows) {
            "http://tauri.localhost"
        } else {
            "tauri://localhost"
        }
    }

    fn invoke_json(
        webview: &tauri::WebviewWindow<tauri::test::MockRuntime>,
        command: &str,
        body: Value,
    ) -> Result<Value, Value> {
        get_ipc_response(
            webview,
            InvokeRequest {
                cmd: command.into(),
                callback: CallbackFn(0),
                error: CallbackFn(1),
                url: local_invoke_url().parse().expect("invoke url"),
                body: InvokeBody::Json(body),
                headers: Default::default(),
                invoke_key: INVOKE_KEY.to_string(),
            },
        )
        .map(|payload| payload.deserialize::<Value>().expect("json response"))
    }

    #[test]
    fn tauri_invoke_commands_manage_bridge_lifecycle() {
        let app = configure_builder(mock_builder())
            .build(mock_context(noop_assets()))
            .expect("build mock app");
        let webview = tauri::WebviewWindowBuilder::new(&app, "main", Default::default())
            .build()
            .expect("build mock webview");

        let runtime_before = invoke_json(
            &webview,
            "bridge_runtime_info",
            Value::Object(Default::default()),
        )
        .expect("runtime info before attach");
        assert_eq!(runtime_before["process_started"], false);
        assert_eq!(runtime_before["core_transport"], "not_started");

        let attach = invoke_json(
            &webview,
            "bridge_request",
            json!({
                "payload": {
                    "method": "desktop.attach",
                    "params": {
                        "session_id": "tauri-ipc-test",
                        "metadata": {"surface": "mock-webview"}
                    },
                    "timeout_ms": 10_000
                }
            }),
        )
        .expect("desktop attach via invoke");
        assert_eq!(attach["ok"], true);
        assert_eq!(attach["result"]["session_id"], "tauri-ipc-test");

        let runtime_after_attach = invoke_json(
            &webview,
            "bridge_runtime_info",
            Value::Object(Default::default()),
        )
        .expect("runtime info after attach");
        assert_eq!(runtime_after_attach["process_started"], true);
        assert_eq!(runtime_after_attach["core_transport"], "spawned");

        let events = invoke_json(
            &webview,
            "bridge_drain_events",
            Value::Object(Default::default()),
        )
        .expect("drain events after attach");
        let drained = events["events"].as_array().expect("events array");
        assert!(
            drained
                .iter()
                .any(|event| event["topic"] == "desktop.session.attached")
        );
        assert!(
            drained
                .iter()
                .any(|event| event["topic"] == "desktop.state.changed")
        );

        let conversation = invoke_json(
            &webview,
            "bridge_request",
            json!({
                "payload": {
                    "method": "conversations.create",
                    "params": {"title": "Tauri IPC test"},
                    "timeout_ms": 10_000
                }
            }),
        )
        .expect("create conversation via invoke");
        assert_eq!(conversation["ok"], true);
        let conversation_id = conversation["result"]["id"]
            .as_str()
            .expect("conversation id");

        let send = invoke_json(
            &webview,
            "bridge_request",
            json!({
                "payload": {
                    "method": "conversations.send",
                    "params": {
                        "conversation_id": conversation_id,
                        "content": "hello from tauri invoke",
                        "run_id": "tauri-invoke-run"
                    },
                    "timeout_ms": 10_000
                }
            }),
        )
        .expect("send conversation via invoke");
        assert_eq!(send["ok"], true);
        assert_eq!(send["result"]["run_id"], "tauri-invoke-run");
        assert_eq!(
            send["result"]["message"]["content"],
            "Echo: hello from tauri invoke"
        );

        let conversation_events = invoke_json(
            &webview,
            "bridge_drain_events",
            Value::Object(Default::default()),
        )
        .expect("drain conversation events");
        let drained = conversation_events["events"]
            .as_array()
            .expect("conversation events array");
        assert!(
            drained
                .iter()
                .any(|event| event["topic"] == "conversation.created")
        );
        assert!(
            drained
                .iter()
                .any(|event| event["topic"] == "conversation.delta")
        );
        assert!(
            drained
                .iter()
                .any(|event| event["topic"] == "conversation.run.completed")
        );

        let shutdown = invoke_json(
            &webview,
            "bridge_shutdown_core",
            Value::Object(Default::default()),
        )
        .expect("shutdown bridge");
        assert_eq!(shutdown["ok"], true);
        assert_eq!(shutdown["result"]["stopped"], true);

        let runtime_after_shutdown = invoke_json(
            &webview,
            "bridge_runtime_info",
            Value::Object(Default::default()),
        )
        .expect("runtime info after shutdown");
        assert_eq!(runtime_after_shutdown["process_started"], false);
        assert_eq!(runtime_after_shutdown["core_transport"], "not_started");
    }

    #[test]
    fn diagnostic_config_defaults_to_disabled() {
        let config = DiagnosticConfig::default();
        assert!(!config.enabled());
        assert_eq!(config.sample_delay_ms, 0);
        assert_eq!(config.auto_exit_ms, None);
        assert_eq!(config.probe_retries, 0);
    }

    #[test]
    fn diagnostic_config_reports_enabled_when_output_path_present() {
        let config = DiagnosticConfig {
            emit_stdout: false,
            output_path: Some(PathBuf::from("diagnostic.json")),
            sample_delay_ms: 2_000,
            auto_exit_ms: Some(250),
            probe_retries: 4,
        };
        assert!(config.enabled());
        assert_eq!(config.sample_delay_ms, 2_000);
        assert_eq!(config.auto_exit_ms, Some(250));
        assert_eq!(config.probe_retries, 4);
    }
}
