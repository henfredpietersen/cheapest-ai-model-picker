"""Probe behaviour. The fake server mimics Ollama's documented JSON shape so the
measured path can be tested without Ollama. Its numbers are test inputs, not results."""

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from router import probe as probe_mod


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_down_exits_zero_and_records_not_measured(tmp_path, capsys):
    out = tmp_path / "report.json"
    out.write_text(json.dumps({"policy_rows": [1]}))
    code = probe_mod.main(["--host", f"http://127.0.0.1:{_free_port()}", "--out", str(out)])
    assert code == 0
    report = json.loads(out.read_text())
    assert report["policy_rows"] == [1]  # existing sections preserved
    p = report["ollama_probe"]
    assert p["status"] == "not_measured"
    assert p["cost_usd"] is None and p["quality"] is None
    assert "latency_ms_median" not in p
    assert "not measured" in capsys.readouterr().out


class _FakeOllama(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body):
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send({"models": [{"name": "fake:1b"}]})

    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        self._send({"response": "billing", "total_duration": 5_000_000, "load_duration": 1_000_000,
                    "prompt_eval_count": 20, "eval_count": 4, "eval_duration": 2_000_000})


@pytest.fixture
def fake_ollama():
    srv = HTTPServer(("127.0.0.1", 0), _FakeOllama)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def test_measured_path_parses_ollama_fields(fake_ollama):
    r = probe_mod.probe(fake_ollama, runs=2)
    assert r["status"] == "measured"
    assert r["model"] == "fake:1b"
    assert len(r["samples"]) == 2
    assert r["samples"][0]["output_tokens"] == 4
    assert r["samples"][0]["tokens_per_s"] == 2000.0
    assert r["cost_usd"] is None  # never fabricated


def test_missing_model_is_not_measured(fake_ollama):
    r = probe_mod.probe(fake_ollama, model="llama3:8b")
    assert r["status"] == "not_measured"
    assert "not pulled" in r["reason"]
