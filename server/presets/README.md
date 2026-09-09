# Built-in presets

Starter presets cover four operations through local CPU tools, fal, Replicate, and ComfyUI. They are request configurations; no model weights or third-party node code are bundled. Provider execution is not automatically tested and paid services require the artist's key and account balance.

## ComfyUI

- Pieces/composition: install an SD or SDXL checkpoint in `models/checkpoints`. The starter chooses the first installed checkpoint unless a `checkpoint` parameter is supplied or you edit the preset. FLUX and other architectures need their own API workflow.
- Cutout: update ComfyUI to a version containing `LoadBackgroundRemovalModel` and `RemoveBackground`, then install [BiRefNet](https://huggingface.co/Comfy-Org/BiRefNet/resolve/main/background_removal/birefnet.safetensors) in `models/background_removal`. The API graph uses native nodes, based on the [official template](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/utility_birefnet_remove_background.json).
- Upscale: install `4x-UltraSharp.pth` in `models/upscale_models`, or change `model_name` in this preset to a model you have. This performs learned model upscaling, not browser resampling.

Missing nodes are detected before the prompt is submitted. ComfyUI validates missing model files. Its basic composition preset is image-to-image; import an inpainting workflow to give an explicit mask to the sampler. Selected-area capture is still supported by all image-to-image presets.

## Cloud requests

Every preset includes the official model API source URL. Replicate community models resolve their current `latest_version` before submission; the actual version is recorded in the job. You can pin a version with `owner/model:version` in an edited preset. fal mappings use the model's advertised field names. Model licenses are separate from this application's MIT license.

## Extending

Edit a copy in Settings or import a JSON preset. `bindings` maps shared inputs (`prompt`, `image`, `mask`, `seed`, `denoise`, `scale`, `width`, `height`) to dotted paths in `inputs` or the ComfyUI API `workflow`. `required_params` optionally lists mandatory inputs. `output_nodes` restricts ComfyUI output nodes; `output_path` optionally identifies a cloud output field. Settings imports override built-ins by matching ID. Deleting the local import restores the built-in on rescan.

Drop raw API-format ComfyUI JSON in `server/workflows`, or choose another existing folder in Settings. An optional `.bindings.json` sidecar supplies bindings/name/operation/output nodes. The regular ComfyUI editor format is rejected with API-export instructions; it cannot reliably execute without conversion and installed node metadata.
