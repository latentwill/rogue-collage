"""Local adapter checks use a temporary project database and no model download."""
import asyncio
import io
import json
import unittest
from unittest.mock import patch
from PIL import Image
from .test_backend import m
from . import local_inference


class LocalInferenceTest(unittest.TestCase):
    def setUp(self):
        m.initialize()
        with m.db() as c:
            c.execute('DELETE FROM jobs')
            c.execute('UPDATE settings SET body=?', (json.dumps(m.DEFAULTS),))

    def source(self):
        image = Image.new('RGBA', (11, 7), (255, 0, 0, 80))
        value = io.BytesIO()
        image.save(value, format='PNG')
        return value.getvalue()

    def test_upscale_queue_without_credentials_preserves_alpha(self):
        src = m.store_asset(self.source(), 'image/png')
        job = m.create_job({'operation': 'upscale', 'preset': 'local-upscale-lanczos', 'params': {'image': src, 'scale': 3}})
        asyncio.run(m.run_job(job))
        done = m.get_job(job['id'])
        self.assertEqual(done['status'], 'succeeded')
        image = Image.open(io.BytesIO(m.asset_bytes(done['outputs'][0])[0]))
        self.assertEqual(image.size, (33, 21))
        self.assertEqual(image.getchannel('A').getextrema(), (80, 80))

    def test_cancelled_local_result_is_not_published(self):
        job = m.create_job({'operation': 'cutout', 'preset': 'local-cutout-u2net', 'params': {'image': m.store_asset(self.source(), 'image/png')}})
        def cancelled(*args):
            m.update_job(job['id'], status='cancelled')
            return self.source()
        with patch.object(local_inference, 'process', side_effect=cancelled):
            asyncio.run(m.run_job(job))
        self.assertEqual(m.get_job(job['id'])['outputs'], [])

    def test_old_settings_gain_local_defaults(self):
        with m.db() as c:
            c.execute('UPDATE settings SET body=?', (json.dumps({'providers': {'fal': {'api_key': 'private'}}}),))
        settings = m.public_settings()
        self.assertTrue(settings['providers']['local']['configured'])
        self.assertEqual(settings['default_presets']['cutout'], 'local-cutout-u2net')
        self.assertNotIn('private', json.dumps(settings))

    def test_cpu_runtime_failure_is_actionable_and_safe_to_retry(self):
        import httpx
        for failure in (RuntimeError('internal tensor data'), httpx.ConnectError('download unavailable')):
            job = m.create_job({'operation': 'cutout', 'preset': 'local-cutout-u2net', 'params': {'image': m.store_asset(self.source(), 'image/png')}})
            with patch.object(local_inference, 'process', side_effect=failure):
                asyncio.run(m.run_job(job))
            done = m.get_job(job['id'])
            self.assertEqual(done['status'], 'failed')
            self.assertTrue(done['terminal_confirmed'])
            self.assertIn('Local CPU processing failed', done['error'])
            self.assertNotIn('provider', done['error'])
            self.assertNotIn('internal tensor data', done['error'])

    def test_default_preset_rejects_wrong_operation(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException):
            m.write_settings({'default_presets': {'cutout': 'local-upscale-lanczos'}})
