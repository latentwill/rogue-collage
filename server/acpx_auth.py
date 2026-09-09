"""Codex-owned login flow. Never return credentials or raw CLI output."""
import asyncio
import re
from urllib.parse import urlparse
from . import acpx_connector as bridge

_task = None
_state = {'state': 'idle'}

async def status():
    try:
        process = await asyncio.create_subprocess_exec(bridge.executable('codex'), 'login', 'status',
            cwd=bridge.ROOT, env=bridge.environment(), stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT, start_new_session=True)
        try:
            output, _ = await asyncio.wait_for(process.communicate(), 10)
        finally:
            await bridge.terminate(process)
        text = output.decode(errors='replace').lower()
        if process.returncode == 0 and 'chatgpt' in text:
            return {'ok': True, 'message': 'Signed in with ChatGPT on this Mac. Model access is checked when you send a request.'}
        if process.returncode == 0 and 'api key' in text:
            return {'ok': False, 'message': 'Codex is using an API key. Sign in with ChatGPT below to use your subscription.'}
        return {'ok': False, 'message': 'Codex is not signed in with ChatGPT. Choose a sign-in method below.'}
    except (bridge.ConnectorError, OSError, asyncio.TimeoutError):
        return {'ok': False, 'message': 'Cannot check Codex login. Re-run app setup, then check again.'}

def login_details(output):
    text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', output)
    result = {}
    for url in re.findall(r'https://[^\s<>]+', text):
        parsed = urlparse(url)
        if parsed.hostname == 'auth.openai.com' and parsed.path in ('/codex/device', '/oauth/authorize'):
            result['url'] = url
    code = re.search(r'\b[A-Z0-9]{4,6}-[A-Z0-9]{4,6}\b', text)
    if code:
        result['code'] = code.group()
    return result

async def _login(method):
    global _state
    process = None
    try:
        argv = [bridge.executable('codex'), 'login']
        if method == 'device': argv.append('--device-auth')
        process = await asyncio.create_subprocess_exec(*argv, cwd=bridge.ROOT, env=bridge.environment(),
            stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT, start_new_session=True)
        async def read():
            output = ''
            while chunk := await process.stdout.read(2048):
                output = (output + chunk.decode(errors='replace'))[-32768:]
                _state.update(login_details(output))
            await process.wait()
        await asyncio.wait_for(read(), 600)
        if process.returncode == 0:
            checked = await status()
            _state = {'state': 'complete' if checked['ok'] else 'failed', 'message': checked['message']}
        else:
            _state = {'state': 'failed', 'message': 'Sign-in failed. Try browser sign-in, or enable device-code login in ChatGPT security settings and try again.'}
    except asyncio.CancelledError:
        _state = {'state': 'cancelled', 'message': 'Sign-in cancelled. Your existing login was kept.'}
        raise
    except (OSError, bridge.ConnectorError, asyncio.TimeoutError):
        _state = {'state': 'failed', 'message': 'Sign-in could not finish. Check your connection and try again.'}
    finally:
        if process is not None: await bridge.terminate(process)

async def start(method):
    global _task, _state
    if method not in ('browser', 'device'): raise bridge.ConnectorError('Choose browser or device sign-in.')
    if _task is not None and not _task.done(): return dict(_state)
    bridge.executable('codex')
    _state = {'state': 'pending', 'method': method, 'message': 'Complete sign-in in your browser. Waiting for Codex…'}
    _task = asyncio.create_task(_login(method))
    return dict(_state)

async def cancel():
    if _task is not None and not _task.done():
        _task.cancel()
        await asyncio.gather(_task, return_exceptions=True)
    return dict(_state)

def progress():
    return dict(_state)
