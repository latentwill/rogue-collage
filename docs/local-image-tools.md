# Local image tools

The standard setup installs `rembg[cpu]`, ONNX Runtime and Pillow. Background removal defaults to **Local CPU · U²-Net**. The first queued cutout downloads the approximately 176 MB ONNX model beneath `runtime-data/models/rembg/`; the queue reports preparation and inference stages. Later cutouts run offline. Source images stay on the service machine. CPU processing runs in a worker thread so the web service stays responsive. Cancelling discards the result; an already-running CPU operation finishes before its thread is released.

Upscale defaults to **Local CPU · Lanczos upscale (non-AI)**. It preserves transparency and applies light RGB sharpening. This resamples pixels rather than reconstructing learned detail. Choose an existing cloud or ComfyUI upscale preset for learned upscaling. Scale supports any factor of at least 1× with a 64 megapixel output memory guard, including enlarging small clippings to a 4K long edge.

Settings store `default_presets.cutout` and `default_presets.upscale`. Existing installations inherit these defaults if absent. Local jobs use the existing durable queue, history, provenance, and asset storage. `GET /api/local/status` reports installation and model cache readiness without downloading anything.

## Dependencies and model provenance

- [rembg](https://github.com/danielgatis/rembg/blob/main/LICENSE.txt): MIT. We use its U²-Net adapter and CPU execution provider.
- [U²-Net upstream](https://github.com/xuebinqin/U-2-Net): Apache-2.0; upstream distributes its pretrained salient-object models alongside the implementation. The ONNX conversion is downloaded by rembg from [its release](https://github.com/danielgatis/rembg/releases/tag/v0.0.0), with rembg's model hash verification. No model weights are bundled in this repository.
- [ONNX Runtime](https://github.com/microsoft/onnxruntime/blob/main/LICENSE): MIT.
- [Pillow](https://github.com/python-pillow/Pillow/blob/main/LICENSE): MIT-CMU.

If distributing a packaged application with dependencies or weights, retain their license and attribution files. The local model selection deliberately excludes models carrying noncommercial weight restrictions.
