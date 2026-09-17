from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import unittest

import test_farmqa_controller as fixtures


class InertWorkerTests(unittest.TestCase):
    setUp = fixtures.ControllerQueueTests.setUp
    open_service = fixtures.ControllerQueueTests.open_service
    receive = fixtures.ControllerQueueTests.receive
    event = fixtures.ControllerQueueTests.event
    stop_event = fixtures.ControllerQueueTests.stop_event
    restart = fixtures.ControllerQueueTests.restart
    accept = fixtures.ControllerQueueTests.accept
    queue = fixtures.ControllerQueueTests.queue

    @property
    def worker(self):
        path = Path(__file__).resolve().parents[1]/'tools/farmqa_worker.py'
        self.assertTrue(path.is_file(), 'Inert worker has not been implemented')
        return path

    def launch(self, seconds=1, db=None):
        process = subprocess.Popen([sys.executable,str(self.worker),'--db',str(db or self.db),
                                    '--seconds',str(seconds)],stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,text=True)
        def cleanup():
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)
        self.addCleanup(cleanup)
        return process

    def collect(self, process):
        out, err = process.communicate(timeout=8)
        return process.returncode, [json.loads(line) for line in out.splitlines()], err

    def wait_active(self, request_id):
        deadline = time.monotonic()+5
        while time.monotonic() < deadline:
            row = self.service.db.execute('SELECT state FROM controller_requests WHERE request_id=?',(request_id,)).fetchone()
            if row['state']=='active':
                return
            time.sleep(.02)
        self.fail('Worker did not acquire the queued request within fixture deadline')

    def test_bounded_wait_releases_one_request_and_reports_no_gameplay(self):
        first = self.queue(); self.queue(session='b',activity='two')
        code, messages, err = self.collect(self.launch(.15))
        self.assertEqual(code,0,err)
        self.assertEqual(messages[0]['event'],'acquired')
        self.assertEqual(messages[-1]['outcome'],'released')
        self.assertEqual(messages[-1]['request_id'],first)
        self.assertGreaterEqual(messages[-1]['elapsed_seconds'], .15)
        self.assertLess(messages[-1]['elapsed_seconds'], 5)
        self.assertEqual([r['state'] for r in self.service.controller.status()],['released','queued'])
        self.assertTrue(all(m['mode']=='inert' and m['game_actions']==0 for m in messages))

    def test_signed_stop_stops_wait_and_other_session_can_then_run(self):
        first=self.queue(); second=self.queue(session='b',activity='two')
        process=self.launch(30);self.wait_active(first)
        started=time.monotonic()
        self.assertEqual(self.receive(self.stop_event(createdAt='2026-09-17T01:00:01Z'))[0],200)
        code,messages,err=self.collect(process)
        self.assertEqual(code,0,err)
        self.assertEqual(messages[-1]['outcome'],'cancelled')
        self.assertLess(time.monotonic()-started,3)  # fixture bound, not production SLA
        code,messages,err=self.collect(self.launch(0))
        self.assertEqual(code,0,err)
        self.assertEqual(messages[-1]['request_id'],second)
        self.assertEqual(messages[-1]['outcome'],'released')

    def test_crash_and_restart_keep_slot_held_without_retry(self):
        first=self.queue();self.queue(session='b',activity='two')
        process=self.launch(30);self.wait_active(first)
        process.kill();process.communicate(timeout=5)
        self.restart()
        code,messages,err=self.collect(self.launch(0))
        self.assertEqual(code,0,err)
        self.assertEqual(messages[-1]['outcome'],'blocked')
        self.assertEqual([r['state'] for r in self.service.controller.status()],['active','queued'])

    def test_other_session_stop_does_not_interrupt_active_wait(self):
        first=self.queue();self.queue(session='b',activity='two')
        process=self.launch(30);self.wait_active(first)
        stop=self.stop_event(createdAt='2026-09-17T01:00:01Z')
        stop['agentSession']={'id':'b'}
        self.assertEqual(self.receive(stop)[0],200)
        time.sleep(.25)  # More than two poll intervals in this inert fixture.
        self.assertIsNone(process.poll())
        self.assertEqual([r['state'] for r in self.service.controller.status()],['active','cancelled'])
        stop=self.stop_event(createdAt='2026-09-17T01:00:01Z');stop['agentActivity']['id']='stop-own'
        self.receive(stop)
        self.assertEqual(self.collect(process)[1][-1]['outcome'],'cancelled')

    def test_competing_worker_cannot_run_while_first_is_waiting(self):
        first=self.queue();self.queue(session='b',activity='two')
        running=self.launch(30);self.wait_active(first)
        code,messages,err=self.collect(self.launch(0))
        self.assertEqual(code,0,err)
        self.assertEqual(messages[-1]['outcome'],'blocked')
        self.receive(self.stop_event(createdAt='2026-09-17T01:00:01Z'))
        self.assertEqual(self.collect(running)[1][-1]['outcome'],'cancelled')

    def test_empty_queue_is_idle(self):
        code,messages,err=self.collect(self.launch(0))
        self.assertEqual(code,0,err)
        self.assertEqual(messages[-1]['outcome'],'idle')

    def test_database_error_does_not_release_or_report_success(self):
        first=self.queue()
        process=self.launch(30);self.wait_active(first)
        with closing(sqlite3.connect(self.db,timeout=2)) as locked:
            locked.execute('BEGIN EXCLUSIVE')
            code,messages,err=self.collect(process)
            locked.rollback()
        self.assertNotEqual(code,0)
        self.assertEqual(messages[-1]['outcome'],'unconfirmed')
        self.assertEqual(messages[-1]['error_type'],'OperationalError')
        self.assertEqual(err,'')
        self.assertNotIn(str(self.db),json.dumps(messages))
        self.assertEqual(self.service.controller.status()[0]['state'],'active')

    def test_invalid_duration_cannot_acquire(self):
        self.queue()
        for seconds in ('nan','inf',-1,61):
            with self.subTest(seconds=seconds):
                code,messages,err=self.collect(self.launch(seconds))
                self.assertNotEqual(code,0)
                self.assertNotIn('acquired',[m.get('event') for m in messages])
        self.assertEqual(self.service.controller.status()[0]['state'],'queued')

    def test_missing_database_is_not_created(self):
        missing=Path(self.temp.name)/'missing.sqlite'
        code,messages,err=self.collect(self.launch(0,missing))
        self.assertNotEqual(code,0)
        self.assertFalse(missing.exists())
        self.assertNotIn(str(missing),json.dumps(messages)+err)

    def test_missing_schema_is_not_initialized(self):
        empty=Path(self.temp.name)/'empty.sqlite'
        with closing(sqlite3.connect(empty)): pass
        code,_,_=self.collect(self.launch(0,empty))
        self.assertNotEqual(code,0)
        with closing(sqlite3.connect(empty)) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM sqlite_master').fetchone()[0],0)

    def test_output_allowlist_excludes_tokens_prompt_and_target(self):
        self.queue()
        code,messages,err=self.collect(self.launch(0))
        self.assertEqual(code,0,err)
        allowed={'event','mode','game_actions','request_id','outcome','elapsed_seconds'}
        for m in messages:self.assertLessEqual(set(m),allowed)
        self.assertNotIn('private fixture prompt',json.dumps(messages))
        self.assertNotIn(self.target['repository'],json.dumps(messages))


if __name__=='__main__': unittest.main()
