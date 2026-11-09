"""Client OctOpus : réessais, erreurs typées, clé jamais exposée, SSE, predict-file (httpx.MockTransport)."""

from __future__ import annotations

import json
import logging

import pytest

httpx = pytest.importorskip("httpx")

from agriml.octopus.client import (  # noqa: E402
    DiscoverRequest, OctopusAuthError, OctopusClient, OctopusError, OctopusUnavailable, RunRequest,
    ScheduleRequest, check_base_url, check_identifier, parse_sse, run_id_of,
)

API_KEY = "sk-test-SECRET-123456"


def make_client(handler, **kwargs):
    sleeps: list[float] = []
    client = OctopusClient(base_url="https://octopus.example", api_key=API_KEY, transport=httpx.MockTransport(handler),
                           sleep=sleeps.append, **kwargs)
    return client, sleeps


def test_start_run_sends_bearer_and_compact_body():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        seen["path"] = request.url.path
        return httpx.Response(200, json={"run_id": "run_42"})

    client, _ = make_client(handler)
    resp = client.start_run(RunRequest(dataset_uri="s3://b/k/", target="y", task="regression", metric="mae",
                                       objective="o", workspace="agri92-sandbox", hints=("h1",)))
    assert run_id_of(resp) == "run_42"
    assert seen["auth"] == f"Bearer {API_KEY}"
    assert seen["path"] == "/api/run"
    assert seen["body"]["hints"] == ["h1"] and "time_budget_min" not in seen["body"]


def test_retries_on_429_with_retry_after_then_succeeds():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) < 3:
            return httpx.Response(429, headers={"Retry-After": "2"})
        return httpx.Response(200, json={"status": "running"})

    client, sleeps = make_client(handler)
    assert client.status("run_1")["status"] == "running"
    assert len(calls) == 3 and sleeps == [2.0, 2.0]


def test_post_500_is_not_retried_but_get_500_is():
    calls = {"GET": 0, "POST": 0}

    def handler(request):
        calls[request.method] += 1
        return httpx.Response(500, text="boom")

    client, _ = make_client(handler, max_retries=2)
    with pytest.raises(OctopusUnavailable):
        client.cancel("run_1")
    with pytest.raises(OctopusUnavailable) as err:
        client.status("run_1")
    assert calls == {"GET": 3, "POST": 1}
    assert err.value.status_code == 500


def test_auth_error_not_retried_and_key_never_leaks(caplog):
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(401, text="invalid key")

    caplog.set_level(logging.DEBUG)
    client, _ = make_client(handler)
    with pytest.raises(OctopusAuthError) as err:
        client.status("run_1")
    assert len(calls) == 1
    assert API_KEY not in str(err.value) and API_KEY not in repr(client) and API_KEY not in caplog.text


def test_missing_key_raises_before_any_request(monkeypatch):
    monkeypatch.delenv("OCTOPUS_API_KEY", raising=False)
    client = OctopusClient(base_url="https://octopus.example", transport=httpx.MockTransport(
        lambda r: pytest.fail("aucune requête ne doit partir")))
    with pytest.raises(OctopusAuthError):
        client.status("run_1")


def test_verify_proof_is_public_endpoint(monkeypatch):
    monkeypatch.delenv("OCTOPUS_API_KEY", raising=False)

    def handler(request):
        assert "Authorization" not in request.headers
        return httpx.Response(200, json={"valid": True})

    client = OctopusClient(base_url="https://octopus.example", transport=httpx.MockTransport(handler))
    assert client.verify_proof({"run_id": "r", "sig": "x"}) == {"valid": True}


def test_transport_error_becomes_unavailable():
    def handler(request):
        raise httpx.ConnectError("down", request=request)

    client, sleeps = make_client(handler, max_retries=1)
    with pytest.raises(OctopusUnavailable):
        client.status("run_1")
    assert len(sleeps) == 1


def test_client_error_and_non_json():
    responses = iter([httpx.Response(422, text="bad body"), httpx.Response(200, text="<html>")])
    client, _ = make_client(lambda r: next(responses))
    with pytest.raises(OctopusError) as err:
        client.discover(DiscoverRequest(dataset_uri="s3://b/k/", description="d"))
    assert err.value.status_code == 422 and not isinstance(err.value, OctopusUnavailable)
    with pytest.raises(OctopusError, match="non JSON"):
        client.proof("run_1")


def test_predict_file_checks_row_count(tmp_path):
    csv = tmp_path / "x.csv"
    csv.write_text("id,a\n1,2\n2,3\n", encoding="utf-8")
    payloads = iter([{"predictions": [0.1, 0.2], "total_rows": 2}, {"predictions": [0.1], "total_rows": 2}])

    def handler(request):
        assert b'name="file"' in request.content and request.url.path.endswith("/predict-file")
        return httpx.Response(200, json=next(payloads))

    client, _ = make_client(handler)
    assert client.predict_file("run_1", csv).predictions == [0.1, 0.2]
    with pytest.raises(OctopusError):
        client.predict_file("run_1", csv)


def test_schedules_hint_guardrails_roundtrip():
    def handler(request):
        if request.url.path == "/api/schedules" and request.method == "GET":
            return httpx.Response(200, json={"schedules": [{"name": "s"}]})
        return httpx.Response(200, json={"ok": True, "path": request.url.path, "method": request.method})

    client, _ = make_client(handler)
    assert client.list_schedules() == [{"name": "s"}]
    assert client.create_schedule(ScheduleRequest(name="n", cron="0 2 * * 1", run_id="r1"))["method"] == "POST"
    assert client.hint("r1", "use GroupKFold")["path"].endswith("/hint")
    assert client.get_guardrails("agri92-sandbox")["method"] == "GET"
    assert client.set_guardrails("agri92-sandbox", {"drop": ["phone"]})["method"] == "PUT"


def test_wait_for_run_polls_until_terminal():
    states = iter(["queued", "running", "completed"])
    client, sleeps = make_client(lambda r: httpx.Response(200, json={"status": next(states)}))
    assert client.wait_for_run("run_1", poll_s=5)["status"] == "completed"
    assert sleeps == [5, 5]
    stuck, _ = make_client(lambda r: httpx.Response(200, json={"status": "running"}))
    with pytest.raises(TimeoutError):
        stuck.wait_for_run("run_1", poll_s=10, timeout_s=20)


def test_stream_events_parses_sse_and_sends_last_event_id():
    body = 'event: progress\ndata: {"pct": 10}\nid: 1\n\n: keepalive\n\nevent: done\ndata: {}\nid: 2\n\n'

    def handler(request):
        assert request.headers["Last-Event-ID"] == "0"
        return httpx.Response(200, text=body, headers={"Content-Type": "text/event-stream"})

    client, _ = make_client(handler)
    events = list(client.stream_events("run_1", last_event_id="0"))
    assert [e.event for e in events] == ["progress", "done"]
    assert events[0].json() == {"pct": 10} and events[1].id == "2"


def test_parse_sse_multiline_data_and_incomplete_tail():
    lines = ["data: a", "data: b", "", "event: x", "data: tail-without-blank-line"]
    events = list(parse_sse(lines))
    assert len(events) == 1 and events[0].data == "a\nb" and events[0].event == "message"


@pytest.mark.parametrize("url", ["http://octopus.ml", "ftp://x", "octopus.ml"])
def test_base_url_must_be_https(url):
    with pytest.raises(ValueError):
        check_base_url(url)


def test_base_url_allows_localhost_http_and_rejects_bad_ids():
    assert check_base_url("http://localhost:8080").startswith("http://localhost")
    with pytest.raises(ValueError):
        check_identifier("../etc/passwd")
    with pytest.raises(OctopusError, match="identifiant"):
        run_id_of({"status": "x"})
