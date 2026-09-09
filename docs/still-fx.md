# Still-image Shader / FX

Open **Shader / FX** in the left rail. Choose an object, selected area, or the whole canvas, then **Capture preview**. Adjust a look and compare with **Show original**. **Apply as new layer** renders at the captured source resolution and leaves originals unchanged. The result is undoable, saved in Assets, and included in PNG/project exports. Refresh the source after canvas edits; applying a stale capture is rejected.

Included: smooth/nearest retro downscaling, signal noise, chroma bleed, tracking damage, edge wave, head switching, scanlines, RGB phosphor mask, glow, and curvature. Four original presets cover clean CRT, worn tape, signal damage, and pixel monitor. Noise is seeded and repeatable. Processing stays in the browser; no video, GIF, animation, model, or provider call is required.

This is a minimal original implementation inspired by the still-image categories in [NTSCRT](https://github.com/finnmckenty/NTSCRT). It does not embed NTSCRT, ntsc-rs, librashader, upstream preset JSON, or RetroArch shaders. It is not a signal-accurate NTSC emulator or a pixel-identical port of NTSCRT's seven CRT presets. This keeps the application implementation MIT-licensed without importing third-party shader licenses.

# Local and compatible agents

In **Settings → Agent**, select **Local LLM · Ollama / LM Studio** or **OpenAI-compatible API**. Local presets fill the usual `/v1` endpoints. Start the chosen server and load a model first, then **Save & discover models**, choose or type its exact model ID, and test. The server must support `/chat/completions` and function/tool calling. Vision additionally requires a vision-capable model.

No LLM model is installed by Rogue Collage. API keys stay in the backend settings; local servers commonly need none. Switching connection presets clears the previous key to avoid sending it to a different server. ACPX subscription login remains a separate option. [Ollama compatibility documentation](https://docs.ollama.com/api/openai-compatibility).
