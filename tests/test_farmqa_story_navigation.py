import importlib.util
import unittest

import test_farmqa_authenticated_fixture as auth


class StoryNavigationTests(unittest.TestCase):
    setUpBase = auth.AuthenticatedFixtureTests.setUpBase
    open_service = auth.AuthenticatedFixtureTests.open_service
    receive = auth.AuthenticatedFixtureTests.receive
    event = auth.AuthenticatedFixtureTests.event
    stop_event = auth.AuthenticatedFixtureTests.stop_event
    accept = auth.AuthenticatedFixtureTests.accept
    queue = auth.AuthenticatedFixtureTests.queue
    acquire = auth.AuthenticatedFixtureTests.acquire
    stop = auth.AuthenticatedFixtureTests.stop
    bind = auth.AuthenticatedFixtureTests.bind
    start = auth.AuthenticatedFixtureTests.start

    def setUp(self):
        auth.AuthenticatedFixtureTests.setUp(self)
        self.assertIsNotNone(importlib.util.find_spec('farmqa_story_navigation'))
        from farmqa_story_navigation import StoryNavigationAdapter
        self.adapter = StoryNavigationAdapter(self.service.controller, self.remote)
        self.remote.transform = lambda r: {**r, 'admission':'accepted', 'guard_lost':False,
                                          'story_step':10, 'outcome':'unchanged'}

    def test_requires_independent_session_binding_and_fixed_binding_shape(self):
        with self.assertRaises(ValueError): self.start()
        self.bind()
        self.binding['path']='skipBtn'
        with self.assertRaises(ValueError): self.start()
        self.assertEqual(self.remote.calls, [])

    def test_pointer_success_alone_does_not_claim_story_advanced(self):
        self.bind(); self.start()
        for row in self.remote.rows.values(): row.update(completed=True,quiescent=True)
        self.remote.transform=lambda r:{**r,'admission':'accepted','guard_lost':False,
            'story_step':10,'outcome':'unchanged','success':True}
        result=self.adapter.finish(self.request,self.owner['token'])
        self.assertTrue(result['success'])
        self.assertEqual(result['outcome'],'unchanged')

    def test_state_rejection_is_unstarted_and_closable(self):
        self.bind()
        self.remote.transform=lambda r:{**r,'started':False,'completed':True,'quiescent':True,
            'cancel_requested':True,'admission':'state_rejected','guard_lost':False,
            'events':[],'story_step':20,'outcome':'unexpected','success':None}
        self.assertEqual(self.start()['admission'],'state_rejected')
        for row in self.remote.rows.values(): row.update(completed=True,quiescent=True)
        self.assertTrue(self.adapter.finish(self.request,self.owner['token'])['closed'])

    def test_false_advanced_result_holds_uncertain_action(self):
        self.bind()
        self.remote.transform=lambda r:{**r,'admission':'accepted','guard_lost':False,
            'story_step':10,'outcome':'advanced'}
        with self.assertRaises(ValueError): self.start()
        self.assertEqual(self.service.db.execute('SELECT state FROM controller_actions').fetchone()[0],'uncertain')

    def test_lost_start_is_not_retried_and_stop_still_cancels(self):
        self.bind();self.remote.lose='start'
        with self.assertRaises(TimeoutError):self.start()
        with self.assertRaises(ValueError):self.start()
        self.stop()
        self.assertTrue(self.adapter.observe(self.request,self.owner['token'])['cancel_requested'])
        self.assertEqual(self.remote.calls.count('start'),1)

    def test_observation_excludes_raw_session_fields(self):
        self.bind()
        self.remote.transform=lambda r:{**r,'admission':'accepted','guard_lost':False,
            'story_step':10,'outcome':'unchanged','access_token':'private','player_id':42}
        result=self.start()
        self.assertNotIn('access_token',result)
        self.assertNotIn('player_id',result)

    def test_rejected_or_eventless_actions_cannot_report_advanced(self):
        self.bind()
        self.remote.transform=lambda r:{**r,'admission':'state_rejected','started':False,
            'completed':True,'quiescent':True,'cancel_requested':True,'guard_lost':False,
            'story_step':20,'outcome':'advanced','success':True,'events':[]}
        with self.assertRaises(ValueError):self.start()

    def test_missing_story_field_is_not_an_unavailable_observation(self):
        self.bind()
        self.remote.transform=lambda r:{**r,'admission':'accepted','guard_lost':False,'outcome':'unavailable'}
        with self.assertRaises(ValueError):self.start()


if __name__=='__main__':unittest.main()
