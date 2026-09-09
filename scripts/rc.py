#!/usr/bin/env python3
"""Standard-library client for the running Rogue Collage local service."""
import argparse
import json
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen


class CLIError(Exception):
    pass


class Client:
    def __init__(self, url, timeout):
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https') or parsed.hostname not in ('localhost', '127.0.0.1'):
            raise CLIError('--url must point to the local Rogue Collage service (localhost or 127.0.0.1)')
        self.url = url.rstrip('/')
        self.timeout = timeout

    def request(self, path, body=None, headers=None):
        data = None if body is None else json.dumps(body, allow_nan=False).encode()
        request = Request(self.url + '/api/' + path, data=data, headers={'Content-Type': 'application/json', **(headers or {})})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.load(response)
        except HTTPError as exc:
            try:
                detail = json.loads(exc.read()).get('detail', exc.reason)
            except (ValueError, AttributeError):
                detail = exc.reason
            raise CLIError(f'HTTP {exc.code}: {detail}') from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise CLIError(f'Cannot reach {self.url}: {exc}. Start Rogue Collage with ./start.command.') from exc
        except ValueError as exc:
            raise CLIError('The service returned an invalid JSON response') from exc

    def preset(self, preset_id):
        result = next((p for p in self.request('presets') if p['id'] == preset_id), None)
        if result is None:
            raise CLIError(f'Unknown preset {preset_id!r}. Run ./rc models list to find its ID.')
        return result


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError('must be a positive integer')
    return number


def finite(value):
    number = float(value)
    if not math.isfinite(number):
        raise argparse.ArgumentTypeError('must be a finite number')
    return number


def parser():
    root = argparse.ArgumentParser(prog='rc', description='Rogue Collage local CLI. All results are JSON; configure provider credentials in the app Settings.')
    root.add_argument('--url', default=os.environ.get('RC_URL', 'http://127.0.0.1:8765'), help='local API base URL (or RC_URL)')
    root.add_argument('--timeout', type=positive, default=30, help='HTTP timeout in seconds')
    commands = root.add_subparsers(dest='command', required=True)
    commands.add_parser('health', help='check the API')
    commands.add_parser('status', help='API health and job counts')
    models = commands.add_parser('models', help='list, inspect, or import model/workflow presets').add_subparsers(dest='action', required=True)
    models.add_parser('list', help='list all available presets')
    models.add_parser('show', help='inspect a preset').add_argument('id')
    models.add_parser('import', help='import a preset object or array; existing IDs are updated').add_argument('file', help='JSON file, or - for stdin')
    sync = models.add_parser('sync-modelfiche', help='import compatible LoRA versions from explicit Modelfiche workspaces')
    sync.add_argument('--url', dest='modelfiche_url', default='http://127.0.0.1:8400', help='local Modelfiche API base URL')
    sync.add_argument('--workspace', action='append', help='workspace ID or slug for inventory; repeat for multiple workspaces')
    sync.add_argument('--selection-file', help='curated JSON array of {workspace, version_id, name?}; required to save presets')
    sync.add_argument('--dry-run', action='store_true', help='report counts and skips without saving presets')
    jobs = commands.add_parser('jobs', help='inspect or cancel queued generation').add_subparsers(dest='action', required=True)
    jobs.add_parser('list').add_argument('--status', help='filter by status, e.g. succeeded')
    jobs.add_parser('show').add_argument('id')
    jobs.add_parser('cancel', help='cancel locally; an already running provider request may still incur a charge').add_argument('id')
    generate = commands.add_parser('generate', help='submit one generation job (may incur provider charges)')
    generate.add_argument('--preset', required=True, help='preset ID from models list')
    generate.add_argument('--prompt', required=True)
    generate.add_argument('--width', type=positive, default=1024)
    generate.add_argument('--height', type=positive, default=1024)
    generate.add_argument('--aspect-ratio', default='1:1', help='for endpoints that choose their own pixel resolution')
    generate.add_argument('--seed', type=int)
    generate.add_argument('--lora', help='compatible weights URL or ComfyUI filename')
    generate.add_argument('--lora-scale', type=finite, default=1.0)
    generate.add_argument('--dry-run', action='store_true', help='resolve and display the job payload without submitting it')
    return root


# Matches the supported adapters in Modelfiche integrations/fal/adapters.py.
MF_ENDPOINTS = {
    'krea': 'fal-ai/krea-2/turbo/lora',
    'ideogram': 'ideogram/v4/lora',
    'z-image': 'fal-ai/z-image/turbo/lora',
    'z image': 'fal-ai/z-image/turbo/lora',
    'klein': 'fal-ai/flux-2/klein/9b/base/lora',
}


def modelfiche_preset(model, version, workspace, url):
    filename = str(version.get('filename') or (version.get('artifact') or {}).get('filename') or '').lower()
    base = str(version.get('base_model') or '').lower()
    embedding_pattern = r'(?:^|[_. -])(?:embeddings?|textual[-_ ]?inversion)(?:[_. -]|$)'
    names = ' '.join(str(value or '').lower() for value in (model.get('name'), version.get('name')))
    if re.search(embedding_pattern, filename) or re.search(embedding_pattern, names) or 'kef' in base or re.search(r'(?:^|[_. -])kef(?:[_. -]|$)', names) or str(version.get('artifact_type') or '').lower() != 'lora':
        return None, 'not a supported LoRA (embedding or other artifact)'
    endpoint = next((endpoint for marker, endpoint in MF_ENDPOINTS.items() if marker in base), None)
    if base in ('qwen-image', 'qwen/qwen-image'):
        endpoint = 'fal-ai/qwen-image'
    if not endpoint:
        return None, 'unsupported base model'
    fal = (version.get('readiness_summary') or {}).get('fal') or {}
    registered_endpoint = fal.get('endpoint_id') or (version.get('readiness') or {}).get('endpoint_id')
    if registered_endpoint and registered_endpoint != endpoint:
        return None, 'registered endpoint does not match the supported base model'
    ready = bool(fal.get('url') or version.get('fal_url'))
    reference = 'modelfiche://' + quote(workspace, safe='') + '/' + quote(version['id'], safe='')
    name = str(version.get('name') or model.get('name') or version['id'])
    model_name = str(model.get('name') or '')
    if model_name and model_name.casefold() not in name.casefold():
        name = model_name + ' · ' + name
    trigger_words = version.get('trigger_words') or []
    readiness = 'Registered with fal' if ready else 'Needs fal registration in Modelfiche'
    inputs = {'image_size': {'width': 1024, 'height': 1024}, 'num_images': 1, 'output_format': 'png',
              'loras': [{'path': reference, 'scale': 1}], 'sync_mode': False, 'enable_safety_checker': True}
    if endpoint == 'fal-ai/krea-2/turbo/lora':
        inputs.update(acceleration='none', enable_prompt_expansion=False)
    elif endpoint == 'fal-ai/z-image/turbo/lora':
        inputs.update(acceleration='regular', enable_prompt_expansion=False, num_inference_steps=8)
    elif endpoint == 'fal-ai/flux-2/klein/9b/base/lora':
        inputs.update(acceleration='regular', guidance_scale=5, num_inference_steps=28, negative_prompt='')
    elif endpoint == 'ideogram/v4/lora':
        inputs.update(expansion_model='Medium', rendering_speed='BALANCED', acceleration='none')
    return {'id': 'mf-' + version['id'], 'name': name, 'provider': 'fal', 'operation': 'generate-piece',
            'model': endpoint, 'inputs': inputs,
            'bindings': {'prompt': 'prompt', 'width': 'image_size.width', 'height': 'image_size.height', 'seed': 'seed', 'loras': 'loras'},
            'lora_options': [{'name': name, 'path': reference}], 'default_lora': reference,
            'description': f'{readiness}. Modelfiche workspace: {workspace}. Trigger words: ' + (', '.join(trigger_words) if isinstance(trigger_words, list) else str(trigger_words)),
            'modelfiche_url': url.rstrip('/'),
            'modelfiche': {'workspace': workspace, 'model_id': model['id'], 'version_id': version['id'],
                           'project_id': model.get('project_id'), 'checkpoint_id': version.get('checkpoint_id'),
                           'base_model': version.get('base_model'), 'trigger_words': trigger_words,
                           'registration_status': 'registered' if ready else 'pending'}}, None


def sync_modelfiche(args, client):
    selections = {}
    if args.selection_file:
        rows = json.loads(Path(args.selection_file).read_text())
        if not isinstance(rows, list) or not rows:
            raise CLIError('Selection file must be a nonempty JSON array of {workspace, version_id, name?}')
        for row in rows:
            if not isinstance(row, dict) or any(not isinstance(row.get(key), str) or not row[key].strip() for key in ('workspace', 'version_id')):
                raise CLIError('Each selection needs explicit workspace and version_id strings')
            if 'name' in row and (not isinstance(row['name'], str) or not row['name'].strip()):
                raise CLIError('Selection name must be a nonempty string when provided')
            key = (row['workspace'], row['version_id'])
            if key in selections:
                raise CLIError('Duplicate version in selection file: ' + row['version_id'])
            selections[key] = row
    if not args.dry_run and not selections:
        raise CLIError('Saving requires --selection-file with explicit final version IDs. Use --workspace WORKSPACE --dry-run to inventory; checkpoints are never selected automatically.')
    if selections and args.workspace:
        raise CLIError('Use --selection-file by itself; its entries supply the explicit workspaces')
    if not selections and not args.workspace:
        raise CLIError('Choose --selection-file or --workspace WORKSPACE --dry-run')
    source = Client(args.modelfiche_url, args.timeout)
    planned, skipped, seen, matched, inventory = [], [], set(), set(), []
    model_count = version_count = 0
    workspaces = list(dict.fromkeys(row['workspace'] for row in selections.values())) if selections else list(dict.fromkeys(args.workspace))
    for workspace in workspaces:
        headers = {'X-Workspace-ID': workspace}
        offset = 0
        while True:
            page = source.request(f'models?limit=250&offset={offset}&paginated=true', headers=headers)
            rows = page['items']
            for row in rows:
                model_count += 1
                model = source.request('models/' + quote(row['id'], safe=''), headers=headers)
                for version in model['versions']:
                    if version['id'] in seen:
                        continue
                    seen.add(version['id'])
                    version_count += 1
                    selection_key = (workspace, version['id'])
                    if selections and selection_key not in selections:
                        continue
                    matched.add(selection_key)
                    preset, reason = modelfiche_preset(model, version, workspace, source.url)
                    if preset:
                        if selections and selections[selection_key].get('name'):
                            preset['name'] = selections[selection_key]['name']
                            preset['lora_options'][0]['name'] = preset['name']
                        planned.append(preset)
                        inventory.append({'workspace': workspace, 'version_id': version['id'], 'model_id': model['id'],
                                          'name': preset['name'], 'checkpoint_step': version.get('checkpoint_step'),
                                          'lifecycle_state': version.get('lifecycle_state'),
                                          'registration_status': preset['modelfiche']['registration_status']})
                    else:
                        skipped.append({'workspace': workspace, 'version_id': version['id'], 'name': version.get('name'), 'reason': reason})
            offset += len(rows)
            if offset >= page['total']:
                break
            if not rows:
                raise CLIError('Modelfiche returned an incomplete catalog page; no presets imported')
    missing = set(selections) - matched
    if missing:
        raise CLIError('Selected versions not found in their explicit workspace; nothing imported: ' + ', '.join(version_id for _, version_id in sorted(missing)))
    if selections and skipped and not args.dry_run:
        raise CLIError('Selected versions include unsupported artifacts; nothing imported. Run with --dry-run to inspect skips.')
    saved = 0
    if not args.dry_run:
        for preset in planned:
            try:
                client.request('presets', preset)
                saved += 1
            except CLIError as exc:
                raise CLIError(f'{exc}. Sync stopped after {saved} saved preset(s); rerun to update the same stable IDs.') from exc
    registered = sum(p['modelfiche']['registration_status'] == 'registered' for p in planned)
    return {'dry_run': args.dry_run, 'workspaces': workspaces, 'models_scanned': model_count,
            'mode': 'curated-selection' if selections else 'inventory-only',
            'versions_scanned': version_count, 'compatible': len(planned), 'registered': registered,
            'pending_registration': len(planned) - registered, 'saved': saved,
            'skipped_count': len(skipped), 'skip_reasons': dict(Counter(s['reason'] for s in skipped)), 'skipped': skipped,
            'versions': inventory}


def execute(args, client):
    if args.command == 'health':
        return client.request('health')
    if args.command == 'status':
        return {'health': client.request('health'), 'jobs': dict(Counter(j['status'] for j in client.request('jobs')))}
    if args.command == 'models':
        if args.action == 'sync-modelfiche':
            return sync_modelfiche(args, client)
        if args.action == 'list':
            return client.request('presets')
        if args.action == 'show':
            return client.preset(args.id)
        raw = sys.stdin.read() if args.file == '-' else Path(args.file).read_text()
        payload = json.loads(raw)
        values = payload if isinstance(payload, list) else [payload]
        if not values or any(not isinstance(p, dict) for p in values):
            raise CLIError('Expected a preset JSON object or nonempty array of objects')
        imported = []
        for preset in values:
            try:
                imported.append(client.request('presets', preset))
            except CLIError as exc:
                raise CLIError(f'{exc}. Import stopped after {len(imported)} saved preset(s); those imports remain saved.') from exc
        return imported
    if args.command == 'jobs':
        if args.action == 'list':
            values = client.request('jobs')
            return [j for j in values if not args.status or j['status'] == args.status]
        path = 'jobs/' + quote(args.id, safe='')
        return client.request(path + '/cancel', {}) if args.action == 'cancel' else client.request(path)
    preset = client.preset(args.preset)
    if preset['operation'] != 'generate-piece':
        raise CLIError('generate supports generate-piece presets. Source-image operations currently require the editor.')
    bindings = preset.get('bindings', {})
    params = {'prompt': args.prompt, 'width': args.width, 'height': args.height, 'aspect_ratio': args.aspect_ratio}
    if args.seed is not None:
        params['seed'] = args.seed
    lora = args.lora or preset.get('default_lora')
    if lora:
        if not any(key in bindings for key in ('loras', 'lora_path')):
            raise CLIError('This preset has no LoRA input binding. Configure a compatible preset in Settings → Models.')
        params.update(loras=[{'path': lora, 'scale': args.lora_scale}], lora_path=lora, lora_scale=args.lora_scale)
    payload = {'preset': preset['id'], 'provider': preset['provider'], 'operation': preset['operation'], 'params': params,
               'target': {'type': 'canvas', 'nativeSize': True, 'x': 0, 'y': 0}}
    missing = [key for key in preset.get('required_params', []) if key not in params]
    if missing:
        raise CLIError('Preset requires additional inputs: ' + ', '.join(missing))
    return payload if args.dry_run else client.request('jobs', payload)


def main():
    args = parser().parse_args()
    try:
        result = execute(args, Client(args.url, args.timeout))
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    except (CLIError, OSError, ValueError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(json.dumps({'error': 'Interrupted. A submitted job may still be running; inspect jobs list.'}), file=sys.stderr)
        return 130


if __name__ == '__main__':
    sys.exit(main())
