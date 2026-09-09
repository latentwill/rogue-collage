# Rogue Collage

A local web art tool for experimental AI collage: collect images, cut out and mask, compose editable layers, generate new material, and export a large finished image with its editable source project.

This MVP focuses on two-dimensional collage. Video, live performance, game mechanics, and 3D are future work.

## Run on your Mac

Prerequisites: Node.js 22.13 or newer with npm and Python 3.10 or newer. No GPU is required to use the editor or remote inference providers.

```sh
./scripts/setup.sh
./start.command
```

Open **http://127.0.0.1:5174**. Keep the launcher terminal open; Ctrl-C stops both services. The launcher binds the editor and API to this computer. Use the same browser and address to keep your locally saved project available.

For development, `npm run build` checks TypeScript and builds the frontend. The launcher runs Vite on port 5174 and FastAPI on port 8765. API documentation is at http://127.0.0.1:8765/docs while running.

## Configure inference

Open **Settings** to configure image providers and the separate language model used by the in-app agent. Do not put API keys into project files or source code.

- **fal**: enter your fal API key. Choose a shipped preset or configure an endpoint and input bindings.
- **Replicate**: enter your Replicate API token. Choose a shipped preset or configure a model and input bindings.
- **ComfyUI**: enter the URL of a running ComfyUI server (default `http://127.0.0.1:8188`). An API key can be configured for authenticated deployments. Install the checkpoint, upscale model and any custom nodes required by your chosen workflow in ComfyUI itself.
- **Agent via ACPX**: select ACPX in Settings to use a locally signed-in Codex, Claude Code, or Gemini CLI. [Setup and behavior](docs/acpx-connector.md).
- **Agent via API**: use an OpenAI-compatible chat-completions endpoint, model identifier and optional key. A local compatible server can be used. Image-provider keys do not configure the agent's language model.

Connection checks do not generate images. Actual image requests can incur provider charges. Remote provider credits are not included. Local background removal downloads its model on first use.

For ComfyUI, import an **API-format workflow** through Settings or place its JSON in `server/workflows/`. A normal editor graph must first be exported in API format. Logical bindings connect prompt, image, mask and other controls to workflow node inputs. Settings exposes the preset JSON for editing these mappings. Shipped presets are starting points; model availability and installed nodes depend on your provider/server.

## Text and studio decoration

**Text** in the left rail adds an editable text layer. Properties include multiline content, font, size, bold/italic, alignment, fill, outline, glow, and shadow. Text stays editable in project bundles and is rendered at export resolution for crisp large PNGs.

Paint splatter, crowns, and “Create Mix Mischief” decorate the pasteboard as four independent, proportional corner images, behind the document canvas. Each corner is capped at 380 pixels so it stays restrained on large displays. They never enter exported artwork. Selected green controls have small paint drips; reduced-motion preferences disable their settling animation.

## Canvas and asset controls

Drag an asset thumbnail onto the canvas to place it at its saved width and height, centered at the drop position. Shift-click objects or layer rows to add or remove them from the selection. Use **Group** in Properties (⌘/Ctrl+G) and **Ungroup** (⌘/Ctrl+Shift+G). Groups remain editable layers and select, move, resize, rotate, and reorder together. Drag a resize corner to scale; drag just outside it to rotate, holding Shift to snap to 15°.

Click assets to select them (Shift-click for multiple); use the contextual Delete action in the top bar. Double-click or drag to place, or use Add to canvas. Deleting selected assets removes the library entries, leaving placed layers and provider output files intact. This library deletion persists independently of canvas undo. Generated asset names use their request prompt; old automatic names are migrated while custom titles are preserved.

Your compatible custom LoRAs appear under **Generate pieces → Krea 2 Turbo · LoRA**. Other actions show only compatible workflows; their panel offers a link back to image-generation models.

Enable **Settings → Debug → Record app actions and service activity** for local UI, document, request, job, and agent diagnostics. Refresh, download, and clear logs in that panel. Logs omit prompts, image data, input values, and credentials, and rotate between `runtime-data/debug.jsonl` and `debug.previous.jsonl` at 2 MB each.

## Local processing and still effects

Background removal defaults to local U²-Net on CPU; the first run downloads its model. Local Lanczos upscaling is also available and is explicitly non-AI. Configure defaults in Settings → Connections. See [local image tools](docs/local-image-tools.md).

The left-rail **Shader / FX** panel adds still-image CRT and VHS effects as new layers. Settings → Agent includes local Ollama/LM Studio and OpenAI-compatible connections with model discovery. See [effects and local agents](docs/still-fx.md).

## Your work and credentials

The current collage and undo history are saved in the browser's IndexedDB. Export a `.collage.zip` project to make a portable backup containing project JSON, source assets, snippets, history and a flat PNG. Export PNG for a finished image; a 4K export is distinct from AI quality upscaling.

The local backend stores settings, generation jobs and downloaded outputs under `runtime-data/`. API keys remain on the local backend and are masked when returned to the browser. This directory is excluded from Git. It is local application storage, not an OS keychain. Set `COLLAGE_DATA_DIR` before launch to use a different storage directory.

Do not expose this development server to the public internet. The app is designed for a single user on localhost.

## Documentation

- [Image models and LoRAs](docs/image-models.md)
- [CLI](docs/cli.md)
- [Optional Modelfiche integration](docs/modelfiche-integration.md)
- [ACPX connector](docs/acpx-connector.md)
- [Agent memory](docs/agent-memory.md)
- [Local image tools](docs/local-image-tools.md)
- [Still-image effects and local agents](docs/still-fx.md)

## Development checks

```sh
npm run build
.venv/bin/python -m unittest discover -s server -t . -p 'test_*.py'
node scripts/test-canvas-geometry.mjs
```

Real provider inference requires your own credentials or local installation. Automated checks do not establish compatibility with every third-party model or workflow.

## Public source and local data

This public repository contains application source and usage documentation. It does not include personal model catalogs, research/planning notes, reference mockups, saved projects, agent conversations, memory contents, credentials, or runtime outputs. Configure your own providers and custom models in Settings.

## License

Original repository material is MIT-licensed; see [LICENSE](LICENSE). Dependencies, model weights, hosted services and imported artwork have their own terms. Model weights and third-party artwork are not bundled.
