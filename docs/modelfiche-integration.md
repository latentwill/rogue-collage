# Modelfiche and Rogue Collage

Modelfiche owns the training catalog and LoRA registration. Rogue Collage owns composition and its generation queue. Sync their catalog through the supported local HTTP API without copying weights or opening Modelfiche's database.

## Sync the catalog

Start both apps. Choose workspace IDs or slugs from Modelfiche's `uv run mfiche --json workspace list` in its checkout, then preview:

```sh
./rc models sync-modelfiche --workspace my-workspace --dry-run
```

This is inventory only. The report includes version IDs, model names, checkpoint steps, lifecycle state and registration status so the artist can choose final artist and merge checkpoints. It never chooses the latest or highest step automatically.

To save a small curated picker, write a selection file with exact versions:

```json
[
  {"workspace": "my-workspace", "version_id": "EXACT-FINAL-VERSION-ID", "name": "Artist name · final step 3000"},
  {"workspace": "my-workspace", "version_id": "EXACT-MERGE-VERSION-ID", "name": "Selected artist merge"}
]
```

```sh
./rc models sync-modelfiche --selection-file final-models.json --dry-run
./rc models sync-modelfiche --selection-file final-models.json
```

`name` is optional. Saving requires this explicit selection file; `--workspace` inventory cannot be turned into a bulk import by removing `--dry-run`. Do not combine `--workspace` with `--selection-file`, since the file already scopes each version. Missing or unsupported selected versions prevent any writes; preview explains unsupported entries. Keep the file to reproduce or update precisely the same curated selection.

To select another Modelfiche port, add `--url http://127.0.0.1:8400` after `sync-modelfiche`. Every request carries `X-Workspace-ID`; no unscoped catalog fallback is used. RC reads all pages of `GET /api/models` and each `GET /api/models/{id}`. There are no Modelfiche writes, uploads or generation requests during sync.

Each selected compatible version becomes an RC preset with ID `mf-<version-id>`, preserving workspace, project, model, version, checkpoint, base-model and trigger-word metadata. Repeating sync updates the same IDs; it does not duplicate presets. The report lists counts and skipped versions without weight URLs. Sync updates imported presets, so keep deliberate manual variants under their own IDs. It does not remove presets omitted from a later selection file or whose source disappears.

Supported endpoint mappings come from Modelfiche's current fal adapters:

| Base family | fal endpoint |
| --- | --- |
| Krea | `fal-ai/krea-2/turbo/lora` |
| Ideogram | `ideogram/v4/lora` |
| Z Image | `fal-ai/z-image/turbo/lora` |
| FLUX.2 Klein | `fal-ai/flux-2/klein/9b/base/lora` |
| Qwen Image (original base only) | `fal-ai/qwen-image` |

The original Qwen Image mapping is supported by the [official fal input schema](https://fal.ai/models/fal-ai/qwen-image/api), rather than a current Modelfiche adapter. Qwen Edit, 2512 and embedding variants are excluded. Until Modelfiche supports Qwen registration, a compatible public weights URL can be configured directly in RC Settings → Models.

Unknown base families, non-LoRA artifacts and KEF embeddings are skipped. Embedding and textual-inversion tokens anywhere in filenames or model/version names are excluded, including names such as `3500-embedding_step3500`; nested artifact filenames are checked when the top-level filename is absent. An explicitly registered endpoint that conflicts with the mapping is also skipped. Endpoint compatibility is catalog-level validation; it does not claim a live inference test.

## Generate with a version

In RC choose the imported model under Generate and its named LoRA. Provider credentials still come from RC Settings. Trigger words are shown in the model description so the artist can include them intentionally.

Preset weights use a stable `modelfiche://<workspace>/<version-id>` reference and `modelfiche_url` API base. RC resolves the current registered weights through Modelfiche when executing the job; signed delivery URLs are not copied into the preset catalog. Keep Modelfiche running when using these references.

Versions without registered fal weights are still imported and marked **Needs fal registration in Modelfiche**. Register them through Modelfiche before generating. Sync does not upload weights or infer that an image-delivery URL can serve model weights. Re-run sync after registration to refresh the label.

The CLI can submit the same presets:

```sh
./rc generate --preset mf-VERSION_ID --prompt 'your trigger words and composition' --width 1024 --height 1024 --dry-run
```

Remove `--dry-run` for generation, then inspect the returned job ID through `./rc jobs show JOB_ID`. The result appears in RC's Queue; the artist chooses when to place it on the active canvas.

## Integration boundaries

This integration is one-way catalog sync plus runtime weight lookup. RC does not currently send output images, ratings or collage documents back to Modelfiche. A follow-up bridge should use Modelfiche's supported image import/provenance APIs and retain the source version ID and RC job ID; no direct storage or database writes are needed.

The open collage document lives in browser storage. A future canvas automation API needs explicit document IDs, revisions and undoable commands before Modelfiche or a CLI can safely transform open layers.
