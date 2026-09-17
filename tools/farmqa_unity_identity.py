"""Narrow read-only client for the existing loopback Unity MCP HTTP service."""
import json
from pathlib import Path
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Unity MCP redirects are unsupported')


class UnityIdentityClient:
    """One synchronous inspection session; no reconnection or ambiguous retries.

    Supports the JSON/SSE request responses used by the installed server, not
    arbitrary MCP transports, subscriptions, authentication or server requests.
    """
    RESOURCES = frozenset('mcpforunity://'+suffix for suffix in
                         ('custom-tools','instances','project/info','editor/state'))

    def __init__(self, endpoint='http://127.0.0.1:9090/mcp'):
        url = urllib.parse.urlsplit(endpoint)
        if (url.scheme != 'http' or url.hostname != '127.0.0.1'
                or url.username or url.password or url.query or url.fragment
                or url.path != '/mcp' or url.port is None):
            raise ValueError('Explicit loopback Unity MCP endpoint required')
        self.endpoint, self.session, self.sequence = endpoint, None, 0
        self.initialized = False
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def _rpc(self, method, params, notification=False):
        self.sequence += 1
        payload = {'jsonrpc':'2.0', 'method':method, 'params':params}
        if not notification: payload['id'] = self.sequence
        headers = {'Content-Type':'application/json', 'Accept':'application/json, text/event-stream'}
        if self.session: headers['Mcp-Session-Id'] = self.session
        if self.initialized: headers['MCP-Protocol-Version'] = '2024-11-05'
        request = urllib.request.Request(self.endpoint, data=json.dumps(payload).encode(), headers=headers)
        with self.opener.open(request, timeout=20) as response:
            self.session = response.headers.get('Mcp-Session-Id', self.session)
            raw = response.read(1024*1024+1)
            content_type = response.headers.get_content_type()
        if len(raw) > 1024*1024: raise ValueError('Unity MCP response exceeds bound')
        if notification: return None
        if content_type == 'text/event-stream':
            messages = [json.loads(line[5:].strip()) for line in raw.decode('utf-8').splitlines()
                        if line.startswith('data:')]
            matches = [message for message in messages if message.get('id') == self.sequence]
            if len(matches) != 1: raise ValueError('Missing or ambiguous MCP reply')
            reply = matches[0]
        elif content_type == 'application/json':
            reply = json.loads(raw)
        else:
            raise ValueError('Unsupported MCP response format')
        if reply.get('id') != self.sequence or 'error' in reply or 'result' not in reply:
            raise ValueError('Unity MCP request failed')
        return reply['result']

    def _start(self):
        if self.initialized: return
        result = self._rpc('initialize', {'protocolVersion':'2024-11-05','capabilities':{},
            'clientInfo':{'name':'farmqa-readonly-identity','version':'1'}})
        if result.get('protocolVersion') != '2024-11-05':
            raise ValueError('Unsupported MCP protocol version')
        self.initialized = True
        self._rpc('notifications/initialized', {}, notification=True)

    @staticmethod
    def _payload(result, key):
        if result.get('isError'): raise ValueError('Unity MCP tool failed')
        blocks = result.get(key, [])
        texts = [item['text'] for item in blocks if 'text' in item]
        if len(texts) != 1: raise ValueError('Ambiguous Unity payload')
        value = json.loads(texts[0])
        if not isinstance(value, dict) or value.get('success') is False:
            raise ValueError('Unity observation failed')
        return value.get('data', value)

    def read(self, uri):
        if uri not in self.RESOURCES: raise ValueError('Unsupported identity resource')
        self._start()
        return self._payload(self._rpc('resources/read', {'uri':uri}), 'contents')

    def select(self, instance):
        self._start()
        self._payload(self._rpc('tools/call', {'name':'set_active_instance',
                                            'arguments':{'instance':instance}}), 'content')

    def probe(self):
        self._start()
        # The operator cannot supply code. This QA-owned probe only reads metadata.
        code = (Path(__file__).resolve().parents[1]/'tests/probes/editor-readiness.cs.txt').read_text(encoding='utf-8')
        result = self._payload(self._rpc('tools/call', {'name':'execute_code',
            'arguments':{'action':'execute','code':code,'safety_checks':True}}), 'content')
        return result['result']


    def session_probe(self):
        """Read the existing game session; never enters Play Mode or logs in."""
        self._start()
        code = (Path(__file__).resolve().parents[1]/'tests/probes/session-identity.cs.txt').read_text(encoding='utf-8-sig')
        result = self._payload(self._rpc('tools/call', {'name':'execute_code',
            'arguments':{'action':'execute','code':code,'safety_checks':True}}), 'content')
        return result['result']
