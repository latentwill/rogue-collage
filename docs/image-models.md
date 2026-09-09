# Image model controls

Generation pixels are independent of the artboard. New pieces default to 1024 × 1024 and are inserted at the returned image's actual size, including outside the artboard. Export still crops to the artboard. **Fit result into selection** explicitly fits/clips the returned layer to the saved selection; it does not change the requested inference resolution. Use **Fit imports here** in the selection toolbar to fit imported images instead of placing their native pixels.

In **Settings → Models**, add a named fal or Replicate endpoint, choose its operation, configure default inputs/bindings, and save compatible LoRA choices. Existing ComfyUI workflows can also expose named LoRA choices through their node bindings. Provider credentials remain under Connections. Endpoints vary: inspect the endpoint's schema and map only supported fields. Native Krea API credentials are not used by the fal presets.

Built-in presets:
- [Krea 2 Large on fal](https://fal.ai/models/krea/v2/large/text-to-image/api): aspect-ratio controls; the provider determines pixel dimensions.
- [Krea 2 Turbo LoRA on fal](https://fal.ai/models/fal-ai/krea-2/turbo/lora/api): custom width/height and a compatible LoRA with adjustable strength.

The LoRA dropdown contains the names saved on that model. fal weights need downloadable URLs. Models using an array binding can send no LoRAs; scalar bindings retain their workflow default until a choice is selected. No weights are bundled. Provider/model compatibility and rights for personal weights remain specific to those assets.

Agent model selection is separate from image inference: choose or enter an exact model ID in Settings → Agent. Availability depends on the connected provider and account. ACPX passes an explicit model choice without app-level fallback.
