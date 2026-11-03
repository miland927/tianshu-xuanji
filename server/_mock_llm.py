"""假的 DeepSeek 端点：验证 server/app.py 的流式转发与出口校验真的能跑通。

不是产品的一部分。用法：
  $env:MOCK_REPLY='...'   # 可选，默认这段故意带违规内容
  python server/_mock_llm.py 8799
  $env:DEEPSEEK_API_KEY='test'
  $env:DEEPSEEK_BASE_URL='http://127.0.0.1:8799'
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEFAULT = ('此局大凶，恐有血光之灾。《玉匣记》云：此日不宜出行。'
           '2027年你会升职，建议你加仓，别错过。'
           '这一层是〔旺衰·中和〕，算得准；至于灵不灵，我不知道。')

REPLY = os.environ.get('MOCK_REPLY', DEFAULT)


class H(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_POST(self):
        n = int(self.headers.get('content-length', 0))
        json.loads(self.rfile.read(n) or b'{}')
        self.send_response(200)
        self.send_header('content-type', 'text/event-stream')
        self.send_header('transfer-encoding', 'chunked')
        self.end_headers()
        for i in range(0, len(REPLY), 10):
            piece = {'choices': [{'delta': {'content': REPLY[i:i + 10]}}]}
            self._chunk('data: ' + json.dumps(piece, ensure_ascii=False) + '\n\n')
        self._chunk('data: [DONE]\n\n')
        self._chunk('')

    def _chunk(self, payload: str):
        raw = payload.encode('utf-8')
        self.wfile.write(f'{len(raw):X}\r\n'.encode() + raw + b'\r\n')
        self.wfile.flush()

    def log_message(self, *a):
        pass


if __name__ == '__main__':
    port = int(sys.argv[1] if len(sys.argv) > 1 else 8799)
    ThreadingHTTPServer(('127.0.0.1', port), H).serve_forever()
