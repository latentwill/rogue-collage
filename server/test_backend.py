"""Deterministic adapter contracts. Run: .venv/bin/python -m unittest server.test_backend"""
import asyncio
import importlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Never open the artist's real settings/database in tests.
_fixture = tempfile.TemporaryDirectory()
os.environ['COLLAGE_DATA_DIR'] = _fixture.name
import httpx
m = importlib.import_module('server.app')
RealClient = httpx.AsyncClient
PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aQ2kAAAAASUVORK5CYII='

class BackendContract(unittest.TestCase):
    def setUp(self):
        m.initialize()
        with m.db() as c:
            c.execute('DELETE FROM jobs')
            c.execute('UPDATE settings SET body=?', (json.dumps(m.DEFAULTS),))
        m.write_settings({'providers': {'fal': {'api_key':'test-secret'}, 'replicate': {'api_key':'test-secret'}, 'comfyui': {'api_key':'test-secret'}}, 'paused':True})

    def client(self, handler):
        return patch.object(m.httpx, 'AsyncClient', side_effect=lambda **kwargs: RealClient(transport=httpx.MockTransport(handler), **kwargs))

    def test_settings_redaction_clear_and_hostile_origin(self):
        self.assertNotIn('test-secret', json.dumps(m.public_settings()))
        m.write_settings({'providers': {'comfyui': {'clear_api_key':True}}})
        self.assertFalse(m.public_settings()['providers']['comfyui']['has_api_key'])
        async def check():
            async with RealClient(transport=httpx.ASGITransport(app=m.app), base_url='http://localhost:8765') as c:
                r=await c.put('/api/settings',headers={'origin':'http://evil.example'},json={'paused':False})
                self.assertEqual(r.status_code,403)
        asyncio.run(check())

    def test_allowed_origins_parsing(self):
        self.assertEqual(m.parse_allowed_origins(''), ())
        self.assertEqual(m.parse_allowed_origins(' https://Mac.Tail.ts.net:8446/ , https://mac.tail.ts.net:8446,*,ftp://x,https://a.example/path,http://b.example?q=1 '), ('https://mac.tail.ts.net:8446',))

    def test_configured_remote_origin_is_trusted_and_others_are_not(self):
        async def check():
            async with RealClient(transport=httpx.ASGITransport(app=m.app), base_url='http://localhost:8765') as c:
                self.assertEqual((await c.put('/api/settings',headers={'origin':'https://mac.tail.ts.net:8446'},json={'paused':True})).status_code,403)
                with patch.object(m,'EXTRA_ORIGINS',('https://mac.tail.ts.net:8446',)), patch.object(m,'EXTRA_HOSTS',('mac.tail.ts.net',)):
                    self.assertEqual((await c.put('/api/settings',headers={'origin':'https://mac.tail.ts.net:8446'},json={'paused':True})).status_code,200)
                    self.assertEqual((await c.put('/api/settings',headers={'origin':'https://other.tail.ts.net:8446'},json={'paused':True})).status_code,403)
            async with RealClient(transport=httpx.ASGITransport(app=m.app), base_url='http://mac.tail.ts.net') as c:
                self.assertEqual((await c.get('/api/health')).status_code,403)
                with patch.object(m,'EXTRA_ORIGINS',('https://mac.tail.ts.net:8446',)), patch.object(m,'EXTRA_HOSTS',('mac.tail.ts.net',)):
                    self.assertEqual((await c.get('/api/health')).status_code,200)
        asyncio.run(check())

    def test_all_presets_validate_and_bind_without_mutating(self):
        presets, errors=m.presets(); self.assertFalse(errors)
        self.assertEqual(len(presets),16)
        for p in presets:
            original=json.dumps(p)
            m.bound_inputs(p,{'prompt':'paint','image':'image.png','seed':12,'denoise':.5})
            self.assertEqual(json.dumps(p),original)
        with self.assertRaises(ValueError): m.validate_preset({'workflow':{'nodes':[]}})

    def test_replicate_submission_download_and_retry_provenance(self):
        job=m.create_job({'operation':'generate-piece','preset':'replicate-flux-schnell','params':{'prompt':'hello'}})
        requests=[]
        def handler(r):
            requests.append(r)
            if r.method=='POST':
                self.assertEqual(r.headers['authorization'],'Bearer test-secret')
                return httpx.Response(201,json={'id':'prediction1'})
            if r.url.host=='api.replicate.com':return httpx.Response(200,json={'status':'succeeded','output':['https://cdn.example/image.png']})
            self.assertNotIn('authorization',r.headers)
            return httpx.Response(200,content=b'fake-image',headers={'content-type':'image/png'})
        with self.client(handler): asyncio.run(m.run_job(job))
        done=m.get_job(job['id']);self.assertEqual(done['status'],'succeeded');self.assertEqual(len(done['outputs']),1)
        retried=m.retry(job['id']);self.assertEqual(retried['retry_of'],job['id']);self.assertNotIn('provider_id',retried)
        self.assertNotIn('test-secret',json.dumps(done))

    def test_fal_recovery_never_resubmits(self):
        job=m.create_job({'operation':'generate-piece','preset':'fal-flux-schnell','params':{'prompt':'hello'}})
        m.update_job(job['id'],status='running',provider_id='known',tracking={'status_url':'https://queue.fal.run/status','response_url':'https://queue.fal.run/result'})
        m.initialize();self.assertEqual(m.get_job(job['id'])['status'],'recovering')
        def handler(r):
            self.assertEqual(r.method,'GET')
            return httpx.Response(200,json={'status':'COMPLETED'} if r.url.path=='/status' else {'images':[{'url':PNG}]})
        with self.client(handler):asyncio.run(m.run_job(m.get_job(job['id'])))
        self.assertEqual(m.get_job(job['id'])['status'],'succeeded')

    def test_cancellation_during_submission_is_not_overwritten(self):
        job=m.create_job({'operation':'generate-piece','preset':'replicate-flux-schnell','params':{}})
        seen=[]
        def handler(r):
            seen.append(r.url.path)
            if r.url.path.endswith('/cancel'):return httpx.Response(200,json={})
            m.cancel(job['id']);return httpx.Response(201,json={'id':'cancel-me'})
        with self.client(handler):asyncio.run(m.run_job(job))
        self.assertEqual(m.get_job(job['id'])['status'],'cancelled')
        self.assertTrue(any(x.endswith('/cancel') for x in seen))

    def test_transient_poll_failure_reconciles_without_new_submission(self):
        job=m.create_job({'operation':'generate-piece','preset':'replicate-flux-schnell','params':{'prompt':'hello'}})
        submits=[]
        first_poll=True
        def handler(r):
            nonlocal first_poll
            if r.method=='POST':
                submits.append(r.url.path)
                return httpx.Response(201,json={'id':'already-paid'})
            if first_poll:
                first_poll=False
                return httpx.Response(503,json={'detail':'Temporary outage'})
            return httpx.Response(200,json={'status':'succeeded','output':[PNG]})
        with self.client(handler):
            asyncio.run(m.run_job(job))
            interrupted=m.get_job(job['id'])
            self.assertEqual(interrupted['status'],'interrupted')
            self.assertEqual(interrupted['provider_id'],'already-paid')
            with self.assertRaises(m.HTTPException) as error:
                m.retry(job['id'])
            self.assertEqual(error.exception.status_code,409)
            m.reconcile(job['id'])
            asyncio.run(m.run_job(m.get_job(job['id'])))
        self.assertEqual(m.get_job(job['id'])['status'],'succeeded')
        self.assertEqual(len(submits),1)

    def test_agent_rejects_unknown_layers_without_job_or_turn_caps(self):
        m.write_settings({'llm':{'model':'test','max_jobs':1}})
        actions=[{'type':'delete-layer','layerId':'missing'},{'type':'transform-layer','layerId':'a','opacity':7}]+[{'type':'generate','operation':'generate-piece','preset':'fal-flux-schnell','prompt':'x'}]*20
        def handler(r):
            self.assertEqual(len(json.loads(r.content)['messages']),32)
            return httpx.Response(200,json={'choices':[{'message':{'tool_calls':[{'function':{'name':'edit_collage','arguments':json.dumps({'actions':actions,'message':'done'})}}]}}]})
        with self.client(handler): result=asyncio.run(m.agent({'project':{'layers':[{'id':'a'}]},'messages':[{'role':'user','content':'make art'}]*30}))
        self.assertEqual(len(result['actions']),21);self.assertEqual(result['actions'][0]['opacity'],1)

    def test_agent_cutout_infers_operation_provider_and_selected_source(self):
        from unittest.mock import AsyncMock
        m.write_settings({'llm':{'connector':'acpx'}})
        reply={'message':'Remove background','actions':[{'type':'generate','preset':'fal-birefnet'}]}
        with patch.object(m.acpx_connector,'complete',AsyncMock(return_value=reply)):
            result=asyncio.run(m.agent({'project':{'layers':[{'id':'portrait'}]},'selectedLayerIds':['portrait']}))
        self.assertEqual(result['actions'][0],{'type':'generate','operation':'cutout','preset':'fal-birefnet','provider':'fal','prompt':'','target':'object','layerId':'portrait'})

    def test_generate_agent_requires_structured_action_and_inherits_form_controls(self):
        m.write_settings({'llm': {'connector': 'api', 'model': 'test'}})
        def handler(r):
            payload = json.loads(r.content)
            self.assertEqual(payload['tool_choice']['function']['name'], 'edit_collage')
            data = {'message': 'Generate a landscape', 'actions': [{'type': 'generate', 'prompt': 'a misty forest'}]}
            return httpx.Response(200, json={'choices': [{'message': {'tool_calls': [{'function': {'name': 'edit_collage', 'arguments': json.dumps(data)}}]}}]})
        with self.client(handler):
            result = asyncio.run(m.agent({'project': {}, 'generation': {'preset': 'fal-flux-schnell', 'width': 1536, 'height': 1024}}))
        action = result['actions'][0]
        self.assertEqual((action['preset'], action['width'], action['height']), ('fal-flux-schnell', 1536, 1024))
        self.assertFalse(result['needs_attention'])
        # The planning endpoint must not execute inference itself.
        self.assertEqual(m.jobs(), [])

    def test_generate_agent_prose_cannot_report_success_or_trigger_inference(self):
        m.write_settings({'llm': {'connector': 'api', 'model': 'test'}})
        def handler(r):
            return httpx.Response(200, json={'choices': [{'message': {'content': 'Done! I created the image.'}}]})
        with self.client(handler):
            result = asyncio.run(m.agent({'project': {}, 'generation': {'preset': 'fal-flux-schnell'}, 'execution': {'jobCount': 0}}))
        self.assertTrue(result['needs_attention'])
        self.assertEqual(result['actions'], [])
        self.assertIn('No generation job was submitted', result['warnings'][0])
        self.assertEqual(m.jobs(), [])

    def test_generate_agent_clarification_and_observed_completion(self):
        from unittest.mock import AsyncMock
        m.write_settings({'llm': {'connector': 'acpx'}})
        reply = {'message': 'Which image should I edit?', 'actions': []}
        with patch.object(m.acpx_connector, 'complete', AsyncMock(return_value=reply)):
            first = asyncio.run(m.agent({'project': {}, 'generation': {}}))
            finished = asyncio.run(m.agent({'project': {}, 'generation': {}, 'execution': {'jobCount': 1}}))
        self.assertTrue(first['needs_attention'])
        self.assertEqual(first['message'], reply['message'])
        self.assertFalse(finished['needs_attention'])

    def test_memory_is_persisted_and_injected_on_next_request(self):
        from unittest.mock import AsyncMock
        m.write_settings({'llm':{'connector':'acpx'}})
        with patch.object(m, 'MEMORY', Path(_fixture.name)/'test-memory.md'):
            self.assertIn('Artist preferences',m.agent_memory()['content'])
            m.write_agent_memory({'content':'# Memory\nPrefer pastel collages.'})
            self.assertEqual(m.agent_memory()['content'],'# Memory\nPrefer pastel collages.')
            with patch.object(m.acpx_connector,'complete',AsyncMock(return_value={'message':'ok','actions':[]})) as complete:
                asyncio.run(m.agent({'project':{},'messages':[]}))
            self.assertIn('Prefer pastel collages.',complete.call_args.args[1][0]['content'])

    def test_acpx_uses_shared_action_validation_without_api_model(self):
        from unittest.mock import AsyncMock
        m.write_settings({'llm':{'connector':'acpx','acpx_agent':'codex','model':''}})
        reply={'message':'Arrange','actions':[{'type':'transform-layer','layerId':'a','opacity':8},{'type':'delete-layer','layerId':'missing'}]}
        with patch.object(m.acpx_connector,'complete',AsyncMock(return_value=reply)) as complete:
            result=asyncio.run(m.agent({'project':{'layers':[{'id':'a'}]},'messages':[]}))
        self.assertEqual(result['actions'],[{'type':'transform-layer','layerId':'a','opacity':1}])
        self.assertEqual(complete.call_args.args[0]['connector'],'acpx')
        with self.assertRaises(m.HTTPException): m.write_settings({'llm':{'acpx_agent':'custom-command'}})

if __name__=='__main__':unittest.main()
