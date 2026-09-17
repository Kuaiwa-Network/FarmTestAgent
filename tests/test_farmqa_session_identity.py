"""Session diagnostics reject stale/mismatched identities and never permit actions."""
import copy
import importlib.util
import sys
from pathlib import Path
import time
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))

class SessionIdentityTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('farmqa_session_identity'),
                             'Session diagnostic evaluator is not implemented')
        from farmqa_session_identity import evaluate
        self.evaluate = evaluate
        self.now = time.time()*1000
        self.expected = {'player_id':42, 'route_sha256':'a'*64}
        self.sample = {'schema_version':1, 'status':'observed', 'observed_at_ms':self.now,
            'is_playing':True, 'generation_before':3, 'generation_after':3,
            'authenticated':True, 'transport_connected':True, 'objects_stable':True,
            'player_id':42, 'route_sha256':'a'*64}

    def check(self):
        return self.evaluate(self.sample, self.expected, now_ms=self.now)

    def test_matching_session_is_only_diagnostic(self):
        result=self.check()
        self.assertEqual(result['session_match'], 'match')
        self.assertEqual(result['verdict'], 'BLOCKED')
        self.assertFalse(result['execution_enabled'])

    def test_disconnected_or_incomplete_session_never_matches(self):
        for key,value in [('authenticated',False),('transport_connected',False),
                          ('objects_stable',False),('is_playing',False),
                          ('generation_after',4),('generation_before',0),
                          ('generation_before',True),('player_id',0)]:
            with self.subTest(key=key):
                saved=copy.deepcopy(self.sample);self.sample[key]=value
                self.assertEqual(self.check()['session_match'],'unknown');self.sample=saved
        for key in list(self.sample):
            with self.subTest(missing=key):
                saved=self.sample.pop(key)
                self.assertEqual(self.check()['session_match'],'unknown');self.sample[key]=saved

    def test_wrong_player_and_route(self):
        for key,value in [('player_id',43),('route_sha256','b'*64)]:
            with self.subTest(key=key):
                saved=self.sample[key];self.sample[key]=value
                self.assertEqual(self.check()['session_match'],'mismatch');self.sample[key]=saved

    def test_stale_future_and_nonfinite_samples(self):
        for stamp in [self.now-10001,self.now+1,float('nan'),float('inf'),True]:
            self.sample['observed_at_ms']=stamp
            self.assertEqual(self.check()['session_match'],'unknown')

    def test_invalid_or_absent_expectations_fail_closed(self):
        for expected in [None,{}, {'player_id':True,'route_sha256':'a'*64},
                         {'player_id':42,'route_sha256':'token'}]:
            self.expected=expected
            self.assertEqual(self.check()['session_match'],'unknown')

    def test_outputs_discard_raw_objects_and_secrets(self):
        self.sample.update(token='DO-NOT-OUTPUT', endpoint='wss://secret/', account='private')
        self.expected['credential']='DO-NOT-OUTPUT'
        result=self.check()
        self.assertNotIn('DO-NOT-OUTPUT',str(result));self.assertNotIn('secret',str(result))
        self.assertNotIn('private',str(result))

    def test_edit_mode_is_not_an_authenticated_observation(self):
        self.sample={'schema_version':1,'status':'edit_mode','observed_at_ms':self.now,'is_playing':False}
        self.assertEqual(self.check()['session_match'],'unknown')

    def test_probe_entrypoint_exists(self):
        from farmqa_unity_identity import UnityIdentityClient
        self.assertTrue(callable(getattr(UnityIdentityClient,'session_probe',None)))

class SessionSelectionTests(unittest.TestCase):
    def test_wrong_project_does_not_call_probe(self):
        from unittest.mock import Mock, patch
        from farmqa_session_identity import inspect_session
        client=Mock()
        client.read.side_effect=[{}, {'instances':[{'id':'expected'}]}, {'projectRoot':'D:/other'}]
        with patch('farmqa_session_identity.source_snapshot',return_value={}):
            result=inspect_session('expected','D:/intended',None,client)
        client.session_probe.assert_not_called()
        self.assertEqual(result['session_match'],'unknown')

    def test_instance_change_discards_even_matching_sample(self):
        from unittest.mock import Mock, patch
        from farmqa_session_identity import inspect_session
        client=Mock()
        client.read.side_effect=[{}, {'instances':[{'id':'expected'}]},
            {'projectRoot':'D:/intended'}, {'instances':[{'id':'replacement'}]}]
        client.session_probe.return_value={'status':'observed'}
        with patch('farmqa_session_identity.source_snapshot',return_value={}):
            result=inspect_session('expected','D:/intended',None,client)
        self.assertEqual(result['session_match'],'unknown')
        self.assertNotIn('observation_status',result)

    def test_exception_details_are_not_returned(self):
        from unittest.mock import Mock, patch
        from farmqa_session_identity import inspect_session
        client=Mock();client.read.side_effect=RuntimeError('secret endpoint token')
        with patch('farmqa_session_identity.source_snapshot',return_value={}):
            result=inspect_session('expected','D:/intended',None,client)
        self.assertEqual(result['error_type'],'RuntimeError')
        self.assertNotIn('secret',str(result))
