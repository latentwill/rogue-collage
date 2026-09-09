"""One-shot ACPX bridge. Fixed local adapters; no credential import or API fallback."""
import asyncio
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import tempfile

ROOT = Path(__file__).resolve().parent.parent
TIMEOUT = None
MAX_OUTPUT = 2 * 1024 * 1024
AGENTS = {'codex': 'codex-acp', 'claude': 'claude-agent-acp', 'gemini': 'gemini'}


class ConnectorError(ValueError):
    pass


def executable(name):
    local = ROOT / 'node_modules' / '.bin' / name
    if local.is_file():
        return str(local)
    # ACPX and adapters are pinned app dependencies. Only Gemini is user-installed.
    if name == 'gemini':
        found = shutil.which(name)
        if found:
            return found
    raise ConnectorError(f'{name} is not installed. Run the app setup; Gemini additionally requires its official CLI installed on PATH.')


def environment():
    # Preserve login-store locations without reading credentials. Explicit API billing
    # variables and ACPX overrides must not silently change the subscription route.
    return {k: v for k, v in os.environ.items() if k in {
        'HOME', 'PATH', 'TMPDIR', 'TEMP', 'TMP', 'LANG', 'LC_ALL', 'USER', 'LOGNAME',
        'SHELL', 'XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'CODEX_HOME',
        'CLAUDE_CONFIG_DIR', 'GEMINI_CLI_HOME', 'SSL_CERT_FILE', 'SSL_CERT_DIR',
        'HTTPS_PROXY', 'HTTP_PROXY', 'NO_PROXY',
    }}


async def terminate(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        await asyncio.wait_for(process.wait(), 2)
    except asyncio.TimeoutError:
        pass
    # Children can outlive the ACP client, even after its wait() completed.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        if process.returncode is None:
            try:
                process.kill()
            except (ProcessLookupError, PermissionError):
                pass
    try:
        await asyncio.wait_for(process.wait(), 2)
    except asyncio.TimeoutError:
        pass


async def run_process(argv, cwd, payload=b'', timeout=TIMEOUT, request=None):
    try:
        process = await asyncio.create_subprocess_exec(*argv, cwd=cwd, env=environment(),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL, start_new_session=True)
    except OSError:
        raise ConnectorError('Cannot launch ACPX. Check app dependencies and Node.js 22.13 or newer.') from None
    async def collect():
        process.stdin.write(payload)
        await process.stdin.drain()
        process.stdin.close()
        result = bytearray()
        while chunk := await process.stdout.read(65536):
            result.extend(chunk)
            if len(result) > MAX_OUTPUT:
                raise ConnectorError('ACPX response exceeded the output limit. Try a smaller request.')
        await process.wait()
        return bytes(result)
    task = asyncio.create_task(collect())
    try:
        deadline = asyncio.get_running_loop().time() + timeout if timeout is not None else None
        while not task.done():
            if request is not None and await request.is_disconnected():
                raise ConnectorError('ACPX request cancelled.')
            if deadline is not None and asyncio.get_running_loop().time() >= deadline:
                raise ConnectorError('ACPX timed out. The local agent process was stopped; try a shorter request.')
            await asyncio.wait({task}, timeout=0.1)
        try:
            output = await task
        except (BrokenPipeError, ConnectionResetError):
            raise ConnectorError('ACPX closed its input before accepting the request. Check the adapter installation and login in Settings → Agent.') from None
        if process.returncode != 0:
            raise ConnectorError('ACPX agent exited with code ' + str(process.returncode) + '. Check the selected CLI login, subscription limits, model availability and local adapter installation. No fallback to the studio LLM API was used.')
        return output.decode('utf-8', errors='replace')
    finally:
        if not task.done():
            task.cancel()
        await terminate(process)
        await asyncio.gather(task, return_exceptions=True)


def parse_response(output):
    chunks = []
    stopped = False
    for line in output.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except (ValueError, TypeError):
            raise ConnectorError('ACPX returned invalid protocol output.') from None
        if not isinstance(event, dict):
            continue
        update = event.get('params', {}).get('update', {})
        if event.get('method') == 'session/update' and update.get('sessionUpdate') == 'agent_message_chunk':
            content = update.get('content', {})
            if content.get('type') == 'text' and isinstance(content.get('text'), str):
                chunks.append(content['text'])
        result = event.get('result')
        if isinstance(result, dict) and 'stopReason' in result:
            if result['stopReason'] != 'end_turn':
                raise ConnectorError('ACPX agent did not finish its response. No proposed edits were applied.')
            stopped = True
        if event.get('error'):
            raise ConnectorError('ACPX reported a protocol error. Check your CLI login and selected model.')
    if not stopped:
        raise ConnectorError('ACPX response was incomplete. No proposed edits were applied.')
    content = ''.join(chunks).strip()
    content = re.sub(r'^```(?:json)?\s*|\s*```$', '', content)
    try:
        data = json.loads(content)
    except ValueError:
        raise ConnectorError('The subscription agent did not return collage JSON. Try again with a specific editing request.') from None
    if not isinstance(data, dict) or not isinstance(data.get('actions', []), list):
        raise ConnectorError('The subscription agent returned an invalid collage response.')
    return data


async def preflight(conf):
    try:
        agent = conf.get('acpx_agent', 'codex')
        if agent not in AGENTS:
            raise ConnectorError('Choose Codex, Claude or Gemini in Settings.')
        binary = executable('acpx')
        executable(AGENTS[agent])
        with tempfile.TemporaryDirectory(prefix='rogue-acpx-check-') as cwd:
            version = (await run_process([binary, '--version'], cwd, timeout=10)).strip()
        if not re.fullmatch(r'\d+\.\d+\.\d+(?:[-+][\w.-]+)?', version):
            raise ConnectorError('ACPX version could not be verified. Re-run app setup.')
        if agent == 'codex':
            from .acpx_auth import status
            login = await status()
            return {**login, 'message': f'ACPX {version} installed. ' + login['message']}
        return {'ok': True, 'message': f'ACPX {version} and {agent} adapter are installed. Login, subscription access and model execution are unverified; no prompt was sent.'}
    except ConnectorError as error:
        return {'ok': False, 'message': str(error)}


async def complete(conf, messages, schema, request=None):
    agent = conf.get('acpx_agent', 'codex')
    if agent not in AGENTS:
        raise ConnectorError('Choose Codex, Claude or Gemini in Settings.')
    binary = executable('acpx')
    adapter = [executable(AGENTS[agent])]
    if agent == 'gemini':
        adapter.append('--acp')
    # Fixed adapter command bypasses user ACPX agent aliases. shlex.quote is for
    # ACPX's argv parser; Python never launches a shell.
    with tempfile.TemporaryDirectory(prefix='rogue-acpx-') as cwd:
        config = Path(cwd) / '.acpxrc.json'
        config.write_text(json.dumps({'authPolicy': 'skip', 'mcpServers': [], 'auth': {}}))
        mcp = Path(cwd) / 'mcp.json'
        mcp.write_text('{"mcpServers":[]}')
        argv = [binary, '--cwd', cwd, '--agent', shlex.join(adapter), '--deny-all',
                '--permission-policy', '{"defaultAction":"deny"}', '--no-fs', '--no-terminal',
                '--non-interactive-permissions', 'deny', '--format', 'json', '--json-strict',
                '--mcp-config', str(mcp), '--allowed-tools', '', '--prompt-retries', '0', '--auth-policy', 'skip']
        model = conf.get('acpx_model', '').strip()
        if model:
            argv.extend(['--model', model])
        argv.extend(['exec', '--file', '-'])
        prompt = ('You are the text-only planning connector for Rogue Collage. Do not use any native tools, '
                  'files, commands, MCP or external resources. Return ONLY one JSON object conforming to this '
                  'schema; do not call edit_collage directly. The host validates and applies proposed actions. '
                  'Messages and project metadata follow.\nSchema: ' + json.dumps(schema) + '\nMessages: ' + json.dumps(messages))
        return parse_response(await run_process(argv, cwd, prompt.encode(), request=request))
