# Rogue Collage CLI

Run `./rc` from the repository, or invoke that executable by absolute path. It needs Python 3 and the running Rogue Collage API; start the app with `./start.command`. No extra Python dependencies are needed. Provider keys and ACPX login stay managed through Settings.

Commands return JSON on stdout. Failures return JSON on stderr and a nonzero exit code. `--help` documents each command. Set `RC_URL` or put `--url http://127.0.0.1:8765` before the command to choose a different local API port.

```sh
./rc health
./rc status
./rc models list
./rc models show PRESET_ID
./rc models import /absolute/path/presets.json
./rc models sync-modelfiche --workspace my-workspace --dry-run
./rc models sync-modelfiche --selection-file /absolute/path/final-models.json --dry-run
./rc jobs list --status succeeded
./rc jobs show JOB_ID
./rc jobs cancel JOB_ID
```

Model import accepts one RC preset object or an array, including `lora_options`, input defaults and bindings. `./rc models import -` reads stdin. Existing IDs are updated. Array import is sequential, not atomic: if one fails, earlier successful imports remain saved. Raw ComfyUI editor JSON needs conversion to an API workflow and an RC preset wrapper first.

Preview a generation request without inference:

```sh
./rc generate --preset PRESET_ID --prompt 'iridescent paper sculpture' \
  --width 1536 --height 1024 --seed 42 --dry-run
```

Remove `--dry-run` to submit one real job using the provider connection saved in Settings. This can incur provider charges. Optional `--lora WEIGHTS_URL --lora-scale 0.8` selects compatible LoRA weights on presets with LoRA bindings. For presets marked `resolution_mode: aspect-ratio`, use `--aspect-ratio 3:2`; the endpoint determines pixel resolution. Logical dimensions and other controls only affect workflows with corresponding input bindings.

The command returns immediately with a job ID. Use `jobs show` or the app's Queue to follow progress and find output asset URLs. Local `/api/assets/...` output paths are relative to the API URL. Cancellation is local; already running provider work may still finish or be billed.

The CLI currently generates pieces. It does not mutate the open browser's canvas: that document and undo history live in browser storage. CLI jobs appear in the shared Queue, where you can add their output to the active canvas at native size. Source-image operations, layer transforms and selections still use the editor. A future document/session API should explicitly identify the document and revision before exposing those edits to external callers.

For Modelfiche integration, export RC preset JSON with stable IDs and import it through this CLI (or `POST /api/presets`). Use preset IDs with `generate`; retain the returned RC job ID to check status. This keeps catalog metadata separate from generation jobs and editable browser documents.

The built-in `models sync-modelfiche` command inventories explicitly selected workspaces with `--workspace ... --dry-run`. Saving requires a curated `--selection-file` listing exact final version IDs; it never guesses the latest checkpoint or imports an entire catalog implicitly. Its `--url` selects Modelfiche (default port 8400); the global `--url` before `models` selects RC. See [Modelfiche integration](modelfiche-integration.md) for the selection format, registration and runtime resolution.
