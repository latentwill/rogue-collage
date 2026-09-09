"""Isolated diagnostics privacy and lifecycle checks; never submits inference."""
import asyncio
import json
import unittest
from unittest.mock import patch
import httpx
from .test_backend import m
from . import debug_log


class DebugLogging(unittest.TestCase):
    def setUp(self):
        m.initialize()
        m.write_settings({'debug_mode': False})
        debug_log.clear(m.DATA)

    def tearDown(self):
        m.write_settings({'debug_mode': False})

    def test_opt_in_sanitization_and_transitions(self):
        m.log_event('ignored', {'count': 1})
        self.assertEqual(debug_log.read(m.DATA), [])
        m.write_settings({'debug_mode': True})
        m.receive_debug_events({'events': [{'event': 'project.command', 'details': {'command': 'generate', 'prompt': 'private artwork', 'api_key': 'test-secret', 'path': 'https://weights.test/private?token=secret', 'count': 2}}]})
        m.save_job({'id': 'test-job', 'status': 'queued', 'params': {'prompt': 'private artwork'}})
        m.update_job('test-job', status='failed', error='test-secret')
        events = debug_log.read(m.DATA)
        serialized = json.dumps(events)
        for secret in ('private artwork', 'test-secret', 'weights.test'):
            self.assertNotIn(secret, serialized)
        self.assertEqual(events[-1]['details']['previous_status'], 'queued')
        self.assertEqual(events[-1]['details']['status'], 'failed')

    def test_http_correlation_routes_and_rotation(self):
        m.write_settings({'debug_mode': True})
        async def check():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=m.app), base_url='http://localhost:8765') as client:
                response = await client.get('/api/jobs/missing?token=private-query')
                self.assertEqual(response.status_code, 404)
                self.assertTrue(response.headers.get('X-Request-ID'))
        asyncio.run(check())
        event = debug_log.read(m.DATA)[-1]
        self.assertEqual(event['details']['path'], '/api/jobs/{jid}')
        self.assertNotIn('private-query', json.dumps(event))
        with patch.object(debug_log, 'MAX_BYTES', 250):
            for _ in range(5):
                debug_log.record(m.DATA, 'rotation.test', {'count': 1})
        self.assertTrue((m.DATA / 'debug.previous.jsonl').exists())
        debug_log.clear(m.DATA)
        self.assertEqual(debug_log.read(m.DATA), [])
