import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
import unittest
import test_farmqa_story_navigation as navigation


class StorySequenceTests(unittest.TestCase):
    setUpBase=navigation.StoryNavigationTests.setUpBase
    open_service=navigation.StoryNavigationTests.open_service
    receive=navigation.StoryNavigationTests.receive
    event=navigation.StoryNavigationTests.event
    stop_event=navigation.StoryNavigationTests.stop_event
    accept=navigation.StoryNavigationTests.accept
    queue=navigation.StoryNavigationTests.queue
    acquire=navigation.StoryNavigationTests.acquire
    stop=navigation.StoryNavigationTests.stop
    bind=navigation.StoryNavigationTests.bind
    start=navigation.StoryNavigationTests.start
    def setUp(self):
        navigation.StoryNavigationTests.setUp(self)
        self.assertIsNotNone(importlib.util.find_spec('farmqa_story_sequence'))
        from farmqa_story_sequence import StorySequenceAdapter
        self.adapter=StorySequenceAdapter(self.service.controller,self.remote)
        self.binding['story_step']=20
        self.remote.transform=lambda r:{**r,'admission':'accepted','guard_lost':False,
            'story_step':20,'outcome':'unchanged','view':'StoryPlayView','guide_group':10,
            'guide_step':1,'checkpoint_reached':False,'dialogue_visible':False}

    # The parent tests cover the original fixed adapter, not this new binding.
    def test_step_binding_is_validated_before_dispatch(self):
        self.bind()
        for step in [True,0,25,70,'20']:
            self.binding['story_step']=step
            with self.assertRaises(ValueError):self.start()
        self.assertEqual(self.remote.calls,[])

    def test_unchanged_is_relative_to_the_pinned_step(self):
        self.bind();self.assertEqual(self.start()['outcome'],'unchanged')

    def test_next_step_must_match_this_actions_binding(self):
        self.bind()
        self.remote.transform=lambda r:{**r,'admission':'accepted','guard_lost':False,
            'completed':True,'success':True,'events':['down','up','click'],
            'story_step':40,'outcome':'advanced','view':'StoryPlayView',
            'guide_group':10,'guide_step':1,'checkpoint_reached':False,'dialogue_visible':False}
        with self.assertRaises(ValueError):self.start()

    def test_finish_requires_main_view_and_expected_guide_step(self):
        self.bind();self.binding['story_step']=60
        self.remote.transform=lambda r:{**r,'admission':'accepted','guard_lost':False,
            'completed':True,'success':True,'events':['down','up','click'],
            'story_step':None,'outcome':'finished','view':'MainView',
            'guide_group':10,'guide_step':3,'checkpoint_reached':False,'dialogue_visible':False}
        with self.assertRaises(ValueError):self.start()

    def test_incomplete_navigation_cannot_release_early(self):
        self.bind();self.start()
        with self.assertRaises(ValueError):self.adapter.finish(self.request,self.owner['token'])

    def test_pending_then_completed_input_without_dialogue_does_not_release(self):
        self.bind();self.binding['story_step']=60
        self.remote.transform=lambda r:{**r,'admission':'accepted','guard_lost':False,
            'story_step':60,'outcome':'unchanged','view':'StoryPlayView','guide_group':10,
            'guide_step':1,'checkpoint_reached':False,'dialogue_visible':False}
        self.start()
        for row in self.remote.rows.values():row.update(completed=True,quiescent=True)
        calls=[]
        def observation(r):
            calls.append(1)
            pending=len(calls)==1
            return {**r,'completed':not pending,'quiescent':not pending,'success':None if pending else True,
                'events':[] if pending else ['down','up','click'],'admission':'accepted','guard_lost':False,
                'story_step':None,'outcome':'unavailable','view':'MainView','guide_group':10,
                'guide_step':2,'checkpoint_reached':False,'dialogue_visible':False}
        self.remote.transform=observation
        with self.assertRaises(ValueError):self.adapter.finish(self.request,self.owner['token'])
        self.assertNotIn('close',self.remote.calls)

    def test_finish_accepts_only_the_verified_final_dialogue(self):
        self.bind();self.binding['story_step']=60
        self.remote.transform=lambda r:{**r,'completed':True,'quiescent':True,'success':True,
            'events':['down','up','click'],'admission':'accepted','guard_lost':False,
            'story_step':None,'outcome':'finished','view':'MainView','guide_group':10,
            'guide_step':2,'checkpoint_reached':False,'dialogue_visible':True}
        self.assertEqual(self.start()['outcome'],'finished')
        for row in self.remote.rows.values():row.update(completed=True,quiescent=True)
        self.assertEqual(self.adapter.finish(self.request,self.owner['token'])['reservation_state'],'released')

    def test_late_cancel_after_click_retains_owner_for_manual_recovery(self):
        self.bind();self.start()
        for row in self.remote.rows.values():row.update(completed=True,quiescent=True,cancel_requested=True)
        self.remote.transform=lambda r:{**r,'success':False,'events':['down','up','click'],
            'admission':'accepted','guard_lost':False,'story_step':None,'outcome':'unavailable',
            'view':'MainView','guide_group':10,'guide_step':2,'checkpoint_reached':False,'dialogue_visible':False}
        with self.assertRaises(ValueError):self.adapter.finish(self.request,self.owner['token'])
        self.assertNotIn('close',self.remote.calls)

    def test_close_result_must_still_confirm_transition(self):
        self.bind();self.binding['story_step']=60
        original=self.remote.transform
        self.remote.transform=lambda r:{**original(r),'story_step':60}
        self.start()
        for row in self.remote.rows.values():row.update(completed=True,quiescent=True)
        self.remote.transform=lambda r:{**r,'success':True,'events':['down','up','click'],
            'admission':'accepted','guard_lost':False,'story_step':None,
            'outcome':'unavailable' if r['closed'] else 'finished','view':'MainView',
            'guide_group':10,'guide_step':2,'checkpoint_reached':False,'dialogue_visible':not r['closed']}
        with self.assertRaises(ValueError):self.adapter.finish(self.request,self.owner['token'])
        self.assertEqual(self.service.controller._owned(self.request,self.owner['token'])['state'],'active')

    def test_harness_records_and_closes_verified_action_before_console_failure(self):
        spec=importlib.util.spec_from_file_location('story_sequence_replay',Path(__file__).parent/'probes/run_story_sequence.py')
        replay=importlib.util.module_from_spec(spec);spec.loader.exec_module(replay)
        binding={**self.binding,'story_step':10}
        temp=TemporaryDirectory();self.addCleanup(temp.cleanup)
        path=Path(temp.name)/'sequence-binding.json'
        path.write_text(json.dumps(binding),encoding='utf-8')
        output=path.parent/'sequence-output'
        client=Mock();client.session_probe.return_value={'generation_before':binding['generation']}
        adapter=Mock()
        result={'completed':True,'quiescent':True,'success':True,'events':['down','up','click'],
            'guard_lost':False,'outcome':'advanced','closed':True,'new_console_errors':1}
        adapter.start.return_value={};adapter.observe.return_value=result;adapter.finish.return_value=result
        with patch.object(replay,'StorySequenceClient',return_value=client), \
                patch.object(replay,'StorySequenceAdapter',return_value=adapter), \
                patch.object(replay,'source_snapshot',return_value={}), \
                patch.object(replay,'evaluate',return_value={'session_match':'match'}), \
                patch('sys.argv',['replay','--binding',str(path),'--output',str(output)]):
            with self.assertRaisesRegex(RuntimeError,'Console errors observed'):replay.main()
        adapter.finish.assert_called_once()
        adapter.start.assert_called_once()
        trace=json.loads((output/'trace.json').read_text())
        self.assertEqual(trace[-1]['label'],'transition_10')
        self.assertEqual(trace[-1]['value']['result']['new_console_errors'],1)
