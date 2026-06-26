# Plugin development

Start from `plugins/example_greeter`.

## Rules

- Use a unique reverse-domain-like ID or project namespace.
- Import public types only from `yue_core.contracts`.
- Namespace every tool with the plugin ID.
- Keep `setup()` registration-only and fast.
- Acquire resources in `start()`.
- Release resources idempotently in `stop()`.
- Never perform hidden network, filesystem, process, or screen operations.
- Declare the correct capability and risk for every tool.
- Check `context.cancelled()` in long-running operations.
- Emit progress events with the tool request as `correlation_id`.
- Keep outputs bounded and JSON-serializable.
- Register model providers through `context.register_model_provider(provider)`.
- Providers must emit model events and must never execute tools directly.

## Example configuration

```toml
[plugins]
roots = ["plugins"]
enabled = ["example.greeter"]
```

Then run:

```powershell
$env:PYTHONPATH="src"
python -m yue_core --config config.example.toml list-tools
python -m yue_core --config config.example.toml invoke example.greeter.greet --arguments '{"name":"Yue"}'
```
