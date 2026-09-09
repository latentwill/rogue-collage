"""No live Modelfiche state or provider calls are used by these tests."""
import asyncio
import copy
import unittest
from unittest.mock import patch

import httpx
from server import modelfiche as m

RealClient = httpx.AsyncClient
PRESET = {'provider': 'fal', 'model': 'fal-ai/krea-2/turbo/lora'}
REFERENCE = 'modelfiche://workspace-one/version-one'
URL = 'https://cdn.fal.media/weights.safetensors?token=ephemeral-secret'


class ModelficheContract(unittest.TestCase):
    def resolve(self, inputs, version=None, preset=None, status=200):
        requests = []
        def handler(request):
            requests.append(request)
            self.assertEqual(request.method, 'GET')
            self.assertEqual(request.headers['x-workspace-id'], 'workspace-one')
            self.assertNotIn('authorization', request.headers)
            return httpx.Response(status, json=version)
        with patch.object(m.httpx, 'AsyncClient', side_effect=lambda **kwargs: RealClient(transport=httpx.MockTransport(handler), **kwargs)):
            result = asyncio.run(m.resolve_loras(inputs, preset or PRESET))
        return result, requests

    def version(self, **extra):
        return {'base_model': 'Krea 2', 'filename': 'checkpoint.safetensors', 'fal_url': URL,
                'readiness': {'endpoint_id': PRESET['model']}, **extra}

    def test_ephemeral_resolution_does_not_mutate_inputs_and_deduplicates_reads(self):
        original = {'loras': [{'path': REFERENCE, 'scale': .7}, {'path': REFERENCE, 'scale': .2}], 'prompt': 'test'}
        saved = copy.deepcopy(original)
        result, requests = self.resolve(original, self.version())
        self.assertEqual(original, saved)
        self.assertEqual(len(requests), 1)
        self.assertEqual(result['loras'][0], {'path': URL, 'scale': .7})
        self.assertEqual(requests[0].url.path, '/api/model-versions/version-one')

    def test_summary_url_and_endpoint_are_supported(self):
        result, _ = self.resolve({'loras': [{'path': REFERENCE}]}, self.version(fal_url=None, readiness={}, readiness_summary={'fal': {'url': URL, 'endpoint_id': PRESET['model']}}))
        self.assertEqual(result['loras'][0]['path'], URL)

    def test_unregistered_and_private_urls_fail_without_echoing_tokens(self):
        for url in [None, 'http://localhost:8400/secret', 'https://127.0.0.1/secret', 'https://assets.local/secret']:
            with self.assertRaises(m.ModelficheError) as caught:
                self.resolve({'loras': [{'path': REFERENCE}]}, self.version(fal_url=url))
            self.assertIn('public HTTPS', str(caught.exception))
            self.assertNotIn('secret', str(caught.exception))

    def test_base_endpoint_and_embeddings_are_rejected(self):
        for changes in [{'base_model': 'Flux 2 Klein'}, {'filename': 'checkpoint_embeddings.safetensors'}, {'readiness': {'endpoint_id': 'ideogram/v4/lora'}}]:
            with self.assertRaises(m.ModelficheError):
                self.resolve({'loras': [{'path': REFERENCE}]}, self.version(**changes))

    def test_missing_version_errors_are_actionable_and_redacted(self):
        with self.assertRaisesRegex(m.ModelficheError, 'not found'):
            self.resolve({'loras': [{'path': REFERENCE}]}, {'secret': URL}, status=404)

    def test_ordinary_provider_inputs_require_no_modelfiche_connection(self):
        with patch.object(m.httpx, 'AsyncClient', side_effect=AssertionError('Unexpected network')):
            inputs = {'loras': [{'path': 'https://example.com/lora.safetensors'}]}
            self.assertEqual(asyncio.run(m.resolve_loras(inputs, PRESET)), inputs)


if __name__ == '__main__':
    unittest.main()
