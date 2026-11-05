"""Tests for scripts/mock_session.py — keyless, local-first mock interviews.

The network-dependent pieces are exercised against a tiny fake
OpenAI-compatible endpoint started on 127.0.0.1, so no Ollama install is
needed and nothing leaves the machine.
"""

import json
import sys
import threading
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import mock_session as ms  # noqa: E402


class FakeEndpoint(BaseHTTPRequestHandler):
    """Speaks enough of the OpenAI dialect for this tool."""

    seen_requests: list[dict] = []

    def log_message(self, *args):  # silence test output
        pass

    def do_GET(self):
        if self.path.endswith("/models"):
            body = {"data": [{"id": "fake-1"}, {"id": "fake-2"}]}
            self._json(body)
        else:
            self._json({}, status=404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        self.__class__.seen_requests.append(
            {"path": self.path, "headers": dict(self.headers), "body": payload}
        )
        if self.path.endswith("/chat/completions"):
            prompt = json.dumps(payload)
            if "KEPT:" in prompt:
                content = (
                    "KEPT: Answered in two calm sentences each time\n"
                    "PRACTICE: Add one concrete detail per answer\n"
                    "RERUN: Q2"
                )
            else:
                content = "Q1. Tell me about a time you solved a problem."
            self._json(
                {"choices": [{"message": {"content": content}}]}
            )
        else:
            self._json({}, status=404)

    def _json(self, body, status=200):
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class EndpointTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeEndpoint)
        cls.base = f"http://127.0.0.1:{cls.server.server_port}/v1"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_list_models(self):
        self.assertEqual(
            ms.list_models(self.base), ["fake-1", "fake-2"]
        )

    def test_chat_roundtrip(self):
        reply = ms.chat(
            self.base, "fake-1",
            [{"role": "system", "content": "hi"}],
        )
        self.assertIn("Q1.", reply)

    def test_no_authorization_header_ever(self):
        reqs = FakeEndpoint.seen_requests
        self.assertGreater(len(reqs), 0)
        for r in reqs:
            self.assertIsNone(
                r["headers"].get("Authorization"),
                "Authorization header must never be sent",
            )
            self.assertIsNone(r["headers"].get("api-key"))

    def test_request_shape_is_openai_dialect(self):
        reqs = FakeEndpoint.seen_requests
        chat_reqs = [r for r in reqs if r["path"].endswith("/chat/completions")]
        self.assertGreater(len(chat_reqs), 0)
        body = chat_reqs[-1]["body"]
        for key in ("model", "messages", "temperature", "max_tokens", "stream"):
            self.assertIn(key, body)
        self.assertFalse(body["stream"])


class BankParsingTest(unittest.TestCase):
    def test_parse_real_early_career_bank(self):
        text = (Path(ms.DOCS) / ms.BANKS["early-career"]).read_text(
            encoding="utf-8"
        )
        qs = ms.parse_bank_questions(text)
        self.assertGreaterEqual(len(qs), 10)
        self.assertTrue(all(q.startswith("Q") for q in qs))
        # candidate-side duplicates of hiring-side questions are deduped
        lower = [q.lower() for q in qs]
        self.assertEqual(len(lower), len(set(lower)))


class PromptAndDebriefTest(unittest.TestCase):
    def test_format_history_shape(self):
        h = ms.format_history(["Q1. hello?", []][1:], [])
        self.assertEqual(h[0]["role"], "system")
        self.assertEqual(h[-1]["role"], "user")

    def test_format_history_persona_and_bank(self):
        h = ms.format_history(["Q1. Why here?", "Q2. Time story?"], [])
        blob = h[1]["content"]
        self.assertIn("Q1. Why here?", blob)
        h2 = ms.format_history([], [], persona="RN, 3 yoe")
        self.assertIn("RN, 3 yoe", h2[1]["content"])

    def test_parse_debrief_full_shape(self):
        kept, practice, rerun = ms.parse_debrief(
            "KEPT: calm tone\nspecific examples\n"
            "PRACTICE: shorten the opener\n"
            "RERUN: Q3. What would make you quit?"
        )
        self.assertIn("calm tone", kept)
        self.assertIn("examples", kept)
        self.assertEqual(practice, "shorten the opener")
        self.assertIn("Q3", rerun)

    def test_parse_debrief_fallback(self):
        kept, practice, rerun = ms.parse_debrief("no structured text here")
        self.assertIn("no structured", kept)
        self.assertEqual(rerun, "?")


class NoSecretsTest(unittest.TestCase):
    def test_no_api_key_flag(self):
        argv = ["mock_session.py", "--help"]
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                ms.main()
            except SystemExit:
                pass
        self.assertNotIn("api-key", buf.getvalue().lower())
        self.assertNotIn("--key", buf.getvalue().lower())


if __name__ == "__main__":
    unittest.main()
