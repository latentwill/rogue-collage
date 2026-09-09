# ACPX CLI subscription connector

Rogue Collage can run its studio agent through ACPX, using a locally signed-in Codex, Claude Code, or Gemini CLI. This follows OpenClaw's use of ACPX as an agent-runtime connector. OpenClaw itself is not required.

## Connect

1. Run app setup with Node.js **22.13 or newer**. ACPX and the official Codex/Claude ACP adapters are pinned local dependencies.
2. For Claude/Gemini, sign in through the chosen CLI on this Mac. Gemini also needs its CLI installed on PATH. Codex sign-in is available directly in Settings.
3. Open **Settings → Agent → Agent connection → ACPX · CLI subscription**.
4. Choose **Codex**, **Claude Code**, or **Gemini CLI**. Leave Model override empty to use the adapter default, or enter a model ID supported by that adapter/account.
5. For Codex, the **Sign in to OpenAI** panel checks the existing ChatGPT login. Use **Sign in with browser** or **Use a device code** if needed. The panel shows the login link/code and waits for completion; cancel or retry if needed. This uses the Codex login shared with other Codex tools on this Mac. See [official authentication guidance](https://developers.openai.com/codex/auth/).
6. Use **Save & check connection**. This checks the runtime/adapter and Codex local login without sending a prompt. Claude/Gemini login remains unverified by this check.
7. Send a message in the Agent dock or choose **Agent** in Generate's prompt section. This is the first operation that uses the CLI account.

CLI authentication, subscription eligibility, quotas, and any account billing are controlled by the CLI/provider. Sign into the intended subscription account; an existing CLI configuration can select another authentication or billing method. The connector does not convert a subscription into a generic API key.

The image providers remain separate: fal, Replicate and ComfyUI still perform image generation, cutout and upscaling. A CLI subscription does not supply credits for those providers.

## Behavior

- Each planning round uses a temporary ACPX `exec` session. Rogue Collage supplies the chat and current project metadata, then validates returned JSON with the same action validator as the LLM API connector.
- The generate–wait–arrange loop and undo history apply without an app-imposed action, job or planning-round cap. The loop stops on completion, an error, uncertain job status, an independent canvas change, or **Stop**. Submitted jobs remain in Queue.
- [Durable memory](agent-memory.md) and the current request and its execution outcomes are included in every planning request. The adapter/model's context and output limits and account quotas still apply.
- This connector is text/metadata-only. Canvas vision remains available through the LLM API connector.
- Prompts use stdin, not command-line arguments. Runtime output retains a byte-size guard and errors are sanitized. Planning requests have no app-imposed response deadline; Stop or disconnect stops the owned process group. Short non-generating setup checks still have a timeout.
- Agent executable choices are fixed, installed adapters; Settings cannot supply arbitrary shell commands. No prompt-time adapter downloads occur.
- ACP file/terminal capabilities and tool permissions are disabled, with an empty MCP list and zero automatic prompt retries. These are adapter controls, not an OS sandbox; use trusted CLI installations/configurations.
- Rogue Collage does not copy CLI login tokens into Settings or project exports. Saved studio API keys and ambient API-key environment variables are not forwarded to this connector. Native CLI configuration still applies.

## Dependencies

Pinned: `acpx` 0.15.1 (MIT), `@agentclientprotocol/codex-acp` 1.10.0 and `@agentclientprotocol/claude-agent-acp` 0.75.1 (Apache-2.0). Provider software and services retain their own terms.

References: [OpenClaw ACPX plugin](https://docs.openclaw.ai/plugins/reference/acpx), [ACPX](https://github.com/openclaw/acpx), [Codex ACP adapter](https://github.com/agentclientprotocol/codex-acp), [Claude ACP adapter](https://github.com/agentclientprotocol/claude-agent-acp), [Gemini CLI](https://github.com/google-gemini/gemini-cli).
