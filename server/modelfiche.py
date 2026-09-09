"""Resolve durable Modelfiche references into ephemeral provider inputs.

Call immediately before submission. Persist the original inputs, never this return
value: registered URLs may carry temporary access tokens.
"""
from copy import deepcopy
import ipaddress
import re
from urllib.parse import unquote, urlparse

import httpx


class ModelficheError(ValueError):
    """Actionable failure safe to put in the local job history."""


def _public_https(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = urlparse(value)
        host = (parsed.hostname or '').lower().rstrip('.')
        if parsed.scheme != 'https' or not host or parsed.username or parsed.password:
            return False
        if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')) or '.' not in host:
            return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            return True
    except ValueError:
        return False


def _reference(value):
    try:
        parsed = urlparse(value)
        workspace, version = parsed.netloc, parsed.path.lstrip('/')
        if (parsed.scheme != 'modelfiche' or parsed.query or parsed.fragment
                or not re.fullmatch(r'[A-Za-z0-9_-]+', workspace)
                or not re.fullmatch(r'[A-Za-z0-9_-]+', version)):
            raise ValueError()
        return workspace, version
    except ValueError:
        raise ModelficheError('Invalid Modelfiche LoRA reference. Sync the model again from Modelfiche.') from None


def _validate_version(version, preset):
    filename = str(version.get('filename') or (version.get('artifact') or {}).get('filename') or '')
    if re.search(r'(?:^|[_. -])(?:embeddings?|textual[-_ ]?inversion)(?:[_. -]|$)', filename, re.I):
        raise ModelficheError('This Modelfiche artifact is an embedding, not LoRA weights. Select the LoRA checkpoint file.')
    readiness = version.get('readiness') or {}
    fal = (version.get('readiness_summary') or {}).get('fal') or {}
    endpoint = fal.get('endpoint_id') or readiness.get('endpoint_id') or readiness.get('endpoint') or readiness.get('fal_endpoint')
    selected = preset.get('model')
    if endpoint and endpoint != selected:
        raise ModelficheError('The LoRA is registered for a different fal endpoint. Select its synced custom model or update its endpoint registration in Modelfiche.')
    base = str(version.get('base_model') or '').casefold()
    # These are Modelfiche's current adapter contracts. Unknown endpoints need
    # an explicit matching registration rather than guessed compatibility.
    markers = {
        'ideogram/v4/lora': ('ideogram',),
        'fal-ai/krea-2/turbo/lora': ('krea',),
        'fal-ai/z-image/turbo/lora': ('z-image', 'z image'),
        'fal-ai/flux-2/klein/9b/base/lora': ('klein',),
    }.get(selected)
    if markers and not any(marker in base for marker in markers):
        raise ModelficheError('The LoRA base model is incompatible with this fal endpoint. Select the matching model family in Modelfiche and sync again.')
    if selected == 'fal-ai/qwen-image' and base not in ('qwen-image', 'qwen/qwen-image'):
        raise ModelficheError('This endpoint requires original Qwen-Image LoRA weights. Qwen Image Edit and 2512 weights need their own compatible endpoint.')
    if not endpoint and not markers and selected != 'fal-ai/qwen-image':
        raise ModelficheError('Register this model version with a fal endpoint in Modelfiche, then retry the queued request.')
    for candidate in (version.get('fal_url'), fal.get('url'), readiness.get('fal_url'), readiness.get('fal_path')):
        if _public_https(candidate):
            filename = unquote(urlparse(candidate).path).rsplit('/', 1)[-1]
            if re.search(r'(?:^|[_. -])(?:embeddings?|textual[-_ ]?inversion)(?:[_. -]|$)', filename, re.I):
                raise ModelficheError('The registered URL points to embedding weights. Register the LoRA checkpoint file in Modelfiche.')
            return candidate
    # The current /assets/{id}/delivery API only serves image revisions; it
    # explicitly rejects checkpoints. Do not upload or hydrate large weights as
    # an implicit consequence of queuing an image.
    raise ModelficheError('This LoRA has no public HTTPS weights URL. Upload/register its weights with fal in Modelfiche, then retry. Local storage and localhost delivery URLs cannot be fetched by fal.')


async def resolve_loras(inputs: dict, preset: dict) -> dict:
    """Return a copy with modelfiche://workspace/version paths resolved.

    Only GETs the documented model-version API with its workspace header. No
    provider credentials, asset uploads, or user database changes occur here.
    Network errors never include response bodies, credentials, or signed URLs.
    """
    resolved = deepcopy(inputs)
    loras = resolved.get('loras')
    if not isinstance(loras, list):
        return resolved
    refs = [lora for lora in loras if isinstance(lora, dict) and str(lora.get('path', '')).startswith('modelfiche:')]
    if not refs:
        return resolved
    if preset.get('provider') != 'fal':
        raise ModelficheError('Modelfiche LoRA references currently require a fal custom model.')
    base = str(preset.get('modelfiche_url') or 'http://127.0.0.1:8400').rstrip('/')
    try:
        parsed = urlparse(base)
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in ('', '/api')):
            raise ValueError()
    except ValueError:
        raise ModelficheError('Set modelfiche_url to the Modelfiche server origin, such as http://127.0.0.1:8400.') from None
    if base.endswith('/api'):
        base = base[:-4]
    cache = {}
    async with httpx.AsyncClient(timeout=15, follow_redirects=False, trust_env=False) as client:
        for lora in refs:
            workspace, version_id = _reference(lora['path'])
            key = (workspace, version_id)
            if key not in cache:
                try:
                    response = await client.get(f'{base}/api/model-versions/{version_id}', headers={'X-Workspace-ID': workspace})
                except httpx.HTTPError:
                    raise ModelficheError('Cannot reach Modelfiche. Start its local server, check modelfiche_url, then retry.') from None
                if response.status_code == 404:
                    raise ModelficheError('The Modelfiche model version was not found in this workspace. Sync the model catalog again.')
                if response.status_code != 200:
                    raise ModelficheError(f'Modelfiche could not read the model version (HTTP {response.status_code}). Check its local server and workspace access.')
                try:
                    version = response.json()
                    if not isinstance(version, dict):
                        raise ValueError()
                    cache[key] = _validate_version(version, preset)
                except (TypeError, KeyError, AttributeError):
                    raise ModelficheError('Modelfiche returned incomplete model metadata. Update Modelfiche and sync the catalog again.') from None
                except ValueError as error:
                    if isinstance(error, ModelficheError):
                        raise
                    raise ModelficheError('Modelfiche returned invalid model metadata. Check its local server and sync again.') from None
            lora['path'] = cache[key]
    return resolved
