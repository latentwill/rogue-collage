Drop ComfyUI API-format workflow JSON files here. A matching `name.bindings.json` can supply `name`, `operation`, `bindings`, and `output_nodes`. This directory is rescanned when presets are requested. Editor-format JSON (`nodes`/`links`) is rejected with API export instructions. Imported executable graphs run only when a generation is queued.

Example sidecar:
```json
{"operation":"generate-piece","bindings":{"prompt":"6.inputs.text","seed":"3.inputs.seed","width":"5.inputs.width","height":"5.inputs.height"},"output_nodes":["9"]}
```
