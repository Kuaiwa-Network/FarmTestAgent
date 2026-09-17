import importlib.util
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))


class WireTests(unittest.TestCase):
    def client_type(self):
        self.assertIsNotNone(importlib.util.find_spec('farmqa_unity_identity'),
                             'Read-only Unity transport is not implemented')
        from farmqa_unity_identity import UnityIdentityClient
        return UnityIdentityClient

    def test_remote_and_credential_urls_rejected_without_connecting(self):
        client = self.client_type()
        for url in ('https://example.com/mcp', 'http://localhost.evil/mcp',
                    'http://user:secret@127.0.0.1:9090/mcp', 'file:///etc/passwd',
                    'http://127.0.0.1:9090/mcp?secret=1'):
            with self.subTest(url=url), self.assertRaises(ValueError): client(url)

    def exercise(self, *, sse=False, wrong_id=False, tool_error=False, redirect=False):
        client_type = self.client_type()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if redirect:
                    self.send_response(302); self.send_header('Location','https://example.invalid/mcp')
                    self.end_headers(); return
                if payload['method'] == 'notifications/initialized':
                    self.send_response(202); self.end_headers(); return
                result = {'protocolVersion':'2024-11-05'}
                if payload['method'] == 'resources/read':
                    if self.headers.get('Mcp-Session-Id') != 'fixture-session':
                        self.send_error(400); return
                    result = {'contents':[{'text':json.dumps({'success':True,'data':{'projectRoot':'fixture'}})}]}
                if payload['method'] == 'tools/call':
                    result = {'isError':tool_error, 'content':[{'type':'text','text':json.dumps(
                        {'success':not tool_error,'data':{'result':{'isPlaying':False}}})}]}
                body = json.dumps({'jsonrpc':'2.0','id':999 if wrong_id else payload['id'], 'result':result})
                body = ('event: message\r\ndata: '+body+'\r\n\r\n') if sse else body
                raw = body.encode()
                self.send_response(200)
                self.send_header('Content-Type','text/event-stream' if sse else 'application/json')
                self.send_header('Mcp-Session-Id','fixture-session')
                self.send_header('Content-Length',str(len(raw))); self.end_headers()
                self.wfile.write(raw)
        server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread = threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        try:
            client = client_type('http://127.0.0.1:'+str(server.server_port)+'/mcp')
            if wrong_id or redirect:
                with self.assertRaises(Exception): client.read('mcpforunity://project/info')
            else:
                self.assertEqual(client.read('mcpforunity://project/info'), {'projectRoot':'fixture'})
                if tool_error:
                    with self.assertRaises(ValueError): client.probe()
                else:
                    self.assertEqual(client.probe(), {'isPlaying':False})
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_json_response_and_session_header(self): self.exercise()
    def test_sse_response(self): self.exercise(sse=True)
    def test_wrong_response_id_rejected(self): self.exercise(wrong_id=True)
    def test_tool_failure_rejected(self): self.exercise(tool_error=True)
    def test_redirect_rejected(self): self.exercise(redirect=True)


if __name__ == '__main__': unittest.main()
