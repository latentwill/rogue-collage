"""Local protocol checks; never invoke a provider or read subscription credentials."""
import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock
from . import acpx_connector as bridge


def events(data, stop='end_turn'):
    text=json.dumps(data)
    return '\n'.join(json.dumps(e) for e in [
        {'method':'session/update','params':{'update':{'sessionUpdate':'agent_message_chunk','content':{'type':'text','text':text[:12]}}}},
        {'method':'session/update','params':{'update':{'sessionUpdate':'agent_message_chunk','content':{'type':'text','text':text[12:]}}}},
        {'result':{'stopReason':stop}}])

class AcpxContract(unittest.IsolatedAsyncioTestCase):
    def test_chunks_and_incomplete_response(self):
        payload={'message':'Done','actions':[{'type':'export'}]}
        self.assertEqual(bridge.parse_response(events(payload)),payload)
        with self.assertRaises(bridge.ConnectorError): bridge.parse_response(events(payload,'cancelled'))
        with self.assertRaises(bridge.ConnectorError): bridge.parse_response('{"result":{}}')

    async def test_fixed_adapter_and_restricted_flags(self):
        runner=AsyncMock(return_value=events({'message':'Done','actions':[]}))
        with patch.object(bridge,'executable',side_effect=lambda n:'/local path/'+n),patch.object(bridge,'run_process',runner):
            await bridge.complete({'acpx_agent':'codex','acpx_model':'a model'},[],{})
        argv=runner.call_args.args[0]
        self.assertIn('--deny-all',argv);self.assertIn('--no-fs',argv);self.assertIn('--no-terminal',argv)
        self.assertEqual(argv[argv.index('--allowed-tools')+1],'')
        self.assertEqual(argv[argv.index('--prompt-retries')+1],'0')
        self.assertEqual(argv[argv.index('--model')+1],'a model')
        with self.assertRaises(bridge.ConnectorError): await bridge.complete({'acpx_agent':'sh -c anything'},[],{})

    async def test_preflight_does_not_infer(self):
        runner=AsyncMock(return_value='0.15.1\n')
        with patch.object(bridge,'executable',return_value='/test/acpx'),patch.object(bridge,'run_process',runner):
            result=await bridge.preflight({'acpx_agent':'claude'})
        self.assertTrue(result['ok']);self.assertIn('unverified',result['message'])
        self.assertEqual(runner.call_args.args[0],['/test/acpx','--version'])
        with patch.object(bridge,'executable',side_effect=bridge.ConnectorError('Missing adapter')):
            self.assertFalse((await bridge.preflight({}))['ok'])

    async def test_cleanup_permission_error_preserves_result(self):
        with tempfile.TemporaryDirectory() as cwd:
            with patch.object(bridge.os, 'killpg', side_effect=PermissionError('denied')):
                result = await bridge.run_process([sys.executable, '-c', 'print("done")'], cwd)
        self.assertEqual(result.strip(), 'done')

    def test_login_output_exposes_only_official_link_and_device_code(self):
        from .acpx_auth import login_details
        result = login_details('https://evil.example/ https://auth.openai.com/codex/device\nABCD-1234\naccess_token=secret')
        self.assertEqual(result, {'url':'https://auth.openai.com/codex/device','code':'ABCD-1234'})

    async def test_timeout_and_environment(self):
        with tempfile.TemporaryDirectory() as cwd:
            with self.assertRaisesRegex(bridge.ConnectorError,'timed out'):
                await bridge.run_process([sys.executable,'-c','import time;time.sleep(30)'],cwd,timeout=.05)
        with patch.dict(os.environ,{'OPENAI_API_KEY':'must-not-forward','ACPX_AUTH_TEST':'must-not-forward'}):
            self.assertNotIn('OPENAI_API_KEY',bridge.environment())
            self.assertNotIn('ACPX_AUTH_TEST',bridge.environment())

if __name__=='__main__':unittest.main()
