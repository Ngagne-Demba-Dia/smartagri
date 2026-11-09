"""Assistant : boucle d'outils avec un faux client Claude (aucun appel réseau, SDK non requis)."""

from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.services.assistant.gateway import (
    FALLBACK_BETA,
    AssistantGateway,
    build_gateway,
    build_params,
    echo_content,
    fallback_used,
    map_sdk_error,
)
from app.services.assistant.service import LIMIT_REPLY, REFUSAL_REPLY, TRUNCATED_NOTICE
from tests.conftest import SERIAL_A, World, make_settings

CHAT = "/v1/assistant/chat"


def text(value: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=value)


def block(kind: str) -> SimpleNamespace:
    return SimpleNamespace(type=kind)


def tool_use(name: str, args: Any, block_id: str = "toolu_1") -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", id=block_id, name=name, input=args)


def response(stop_reason: str, *blocks: Any, iterations: list[Any] | None = None, **extra: Any) -> SimpleNamespace:
    usage = SimpleNamespace(input_tokens=100, output_tokens=20, cache_read_input_tokens=80,
                            iterations=iterations or [])
    return SimpleNamespace(content=list(blocks), stop_reason=stop_reason, model="claude-opus-5-5", usage=usage,
                           **extra)


class FakeMessages:
    def __init__(self, owner: FakeClient, path: str) -> None:
        self._owner = owner
        self._path = path

    def create(self, **params: Any) -> Any:
        return self._owner.reply(self._path, params)


class FakeClient:
    """Faux client Anthropic : rejoue des réponses préparées et garde les paramètres reçus."""

    def __init__(self, *responses: Any) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []
        self.paths: list[str] = []
        self.messages = FakeMessages(self, "messages")
        self.beta = SimpleNamespace(messages=FakeMessages(self, "beta"))

    def reply(self, path: str, params: dict[str, Any]) -> Any:
        self.calls.append(params)
        self.paths.append(path)
        item = self.responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def install(app: Any, *responses: Any) -> FakeClient:
    fake = FakeClient(*responses)
    app.state.assistant_gateway = AssistantGateway(fake)
    return fake


def ask(client: TestClient, headers: dict[str, str], message: str = "Comment va mon sol ?",
        **extra: Any) -> Any:
    return client.post(CHAT, headers=headers, json={"message": message, **extra})


def tool_results(params: dict[str, Any]) -> list[dict[str, Any]]:
    last = params["messages"][-1]
    assert last["role"] == "user"
    return last["content"]


# --- Boucle complète via l'API ----------------------------------------------------------------

def test_tool_loop_runs_tool_then_returns_final_text(client: TestClient, app: Any, world: World) -> None:
    fake = install(app,
                   response("tool_use", text("Je consulte le kit."),
                            tool_use("get_latest_measurements", {"device_id": SERIAL_A})),
                   response("end_turn", text("Le sol est correctement humide.")))
    body = ask(client, world.farmer_a).json()
    assert body["success"] is True
    data = body["data"]
    assert data["reply"] == "Le sol est correctement humide."
    assert data["tools_used"] == ["get_latest_measurements"]
    assert data["stop_reason"] == "end_turn" and data["limit_reached"] is False
    assert len(fake.calls) == 2 and fake.paths == ["beta", "beta"]
    [result] = tool_results(fake.calls[1])
    assert result["type"] == "tool_result" and result["tool_use_id"] == "toolu_1"
    assert result["is_error"] is False and json.loads(result["content"])["device"] == SERIAL_A
    first = fake.calls[0]
    assert first["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert first["tools"][-1]["cache_control"] == {"type": "ephemeral"}


def test_foreign_device_tool_call_is_an_error_result(client: TestClient, app: Any, world: World) -> None:
    fake = install(app,
                   response("tool_use", tool_use("get_latest_measurements", {"device_id": SERIAL_A})),
                   response("end_turn", text("Je n'ai pas accès à ce kit.")))
    assert ask(client, world.admin_b).status_code == 200
    [result] = tool_results(fake.calls[1])
    assert result["is_error"] is True
    assert "Kit 1" not in result["content"]


def test_all_tool_results_share_one_user_message(client: TestClient, app: Any, world: World) -> None:
    fake = install(app,
                   response("tool_use", tool_use("outil_inconnu", {}, "toolu_a"),
                            tool_use("get_open_alerts", "pas un objet", "toolu_b"),
                            tool_use("get_open_alerts", {}, "toolu_c")),
                   response("end_turn", text("Aucune alerte ouverte.")))
    assert ask(client, world.farmer_a).status_code == 200
    results = tool_results(fake.calls[1])
    assert [item["tool_use_id"] for item in results] == ["toolu_a", "toolu_b", "toolu_c"]
    assert [item["is_error"] for item in results] == [True, True, False]


def test_refusal_returns_neutral_french_reply(client: TestClient, app: Any, world: World) -> None:
    install(app, response("refusal", text("partiel"), stop_details=SimpleNamespace(category="cyber")))
    data = ask(client, world.farmer_a).json()["data"]
    assert data["reply"] == REFUSAL_REPLY
    assert data["stop_reason"] == "refusal" and data["refusal_category"] == "cyber"


def test_iteration_cap_stops_the_loop(client: TestClient, app: Any, world: World) -> None:
    fake = install(app, *[response("tool_use", tool_use("get_open_alerts", {})) for _ in range(3)])
    data = ask(client, world.farmer_a).json()["data"]
    assert len(fake.calls) == 3  # ASSISTANT_MAX_ITERATIONS=3 dans conftest
    assert data["reply"] == LIMIT_REPLY and data["stop_reason"] == "iteration_limit"
    assert data["limit_reached"] is True and data["tools_used"] == ["get_open_alerts"] * 3


def test_max_tokens_marks_reply_truncated(client: TestClient, app: Any, world: World) -> None:
    install(app, response("max_tokens", text("Début de réponse")))
    data = ask(client, world.farmer_a).json()["data"]
    assert data["reply"] == "Début de réponse" + TRUNCATED_NOTICE and data["truncated"] is True


def test_pause_turn_is_resumed_and_locale_notice_set(client: TestClient, app: Any, world: World) -> None:
    fake = install(app, response("pause_turn", text("…")), response("end_turn", text("Jàmm rekk.")))
    data = ask(client, world.farmer_a, locale="wo").json()["data"]
    assert data["reply"] == "Jàmm rekk." and len(fake.calls) == 2
    assert fake.calls[1]["messages"][-1]["role"] == "assistant"
    assert data["language_quality_notice"] is not None


def test_history_is_replayed_and_conversation_is_private(client: TestClient, app: Any, world: World) -> None:
    fake = install(app, response("end_turn", text("Réponse 1")), response("end_turn", text("Réponse 2")))
    conversation_id = ask(client, world.farmer_a, "Question 1").json()["data"]["conversation_id"]
    assert ask(client, world.farmer_a, "Question 2", conversation_id=conversation_id).status_code == 200
    roles = [(item["role"], item["content"]) for item in fake.calls[1]["messages"]]
    assert roles == [("user", "Question 1"), ("assistant", "Réponse 1"), ("user", "Question 2")]
    foreign = ask(client, world.admin_b, "Intrusion", conversation_id=conversation_id)
    assert foreign.status_code == 404 and foreign.json()["error"]["code"] == "NOT_FOUND"
    assert len(fake.calls) == 2


def test_missing_gateway_answers_503(client: TestClient, world: World) -> None:
    response_ = ask(client, world.farmer_a)
    assert response_.status_code == 503
    assert response_.json()["error"]["code"] == "ASSISTANT_UNAVAILABLE"


@pytest.mark.parametrize("message", ["   ", "x" * 2001])
def test_invalid_message_is_rejected_before_any_call(client: TestClient, app: Any, world: World,
                                                     message: str) -> None:
    fake = install(app)
    response_ = ask(client, world.farmer_a, message)
    assert response_.status_code == 400 and response_.json()["error"]["code"] == "MESSAGE_INVALID"
    assert fake.calls == []


def test_sdk_error_is_mapped_to_stable_code(client: TestClient, app: Any, world: World) -> None:
    class RateLimitError(Exception):
        pass

    install(app, RateLimitError("429"))
    response_ = ask(client, world.farmer_a)
    assert response_.status_code == 503
    assert response_.json()["error"]["code"] == "ASSISTANT_RATE_LIMITED"


# --- Paramètres et utilitaires de la passerelle -----------------------------------------------

def test_build_params_adaptive_thinking_effort_and_fallback() -> None:
    params = build_params(make_settings(ASSISTANT_EFFORT="high"), [{"type": "text", "text": "s"}], [],
                          [{"role": "user", "content": "q"}])
    assert params["thinking"] == {"type": "adaptive"}
    assert params["output_config"] == {"effort": "high"}
    assert params["betas"] == [FALLBACK_BETA] and params["fallbacks"] == "default"
    assert "temperature" not in params and "budget_tokens" not in json.dumps(params)


def test_build_params_without_server_fallback_uses_standard_endpoint() -> None:
    params = build_params(make_settings(ASSISTANT_SERVER_FALLBACK="false"), [], [], [])
    assert "betas" not in params and "fallbacks" not in params
    fake = FakeClient(response("end_turn", text("ok")))
    AssistantGateway(fake).create(params)
    assert fake.paths == ["messages"]


def test_echo_content_drops_internal_blocks_before_fallback() -> None:
    before, after = text("avant"), text("après")
    blocks = [before, block("thinking"), block("redacted_thinking"), tool_use("x", {}), block("fallback"), after]
    assert echo_content(blocks) == [before, after]
    plain = [block("thinking"), before]
    assert echo_content(plain) == plain


def test_fallback_used_reads_usage_iterations() -> None:
    assert fallback_used(response("end_turn", iterations=[SimpleNamespace(type="fallback_message")])) is True
    assert fallback_used(response("end_turn", iterations=[SimpleNamespace(type="message")])) is False
    assert fallback_used(SimpleNamespace(usage=None)) is False


def test_map_sdk_error_follows_class_hierarchy() -> None:
    class APIConnectionError(Exception):
        pass

    class APITimeoutError(APIConnectionError):
        pass

    class NotFoundError(Exception):
        pass

    timeout = map_sdk_error(APITimeoutError())
    assert timeout is not None and (timeout.status, timeout.code) == (503, "ASSISTANT_UNREACHABLE")
    missing = map_sdk_error(NotFoundError())
    assert missing is not None and (missing.status, missing.code) == (502, "ASSISTANT_MODEL_NOT_FOUND")
    assert map_sdk_error(ValueError("autre")) is None


def test_build_gateway_disabled_without_key_or_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    assert build_gateway(make_settings()) is None
    monkeypatch.setitem(sys.modules, "anthropic", None)  # import impossible, que le SDK soit installé ou non
    assert build_gateway(make_settings(ANTHROPIC_API_KEY="sk-ant-test")) is None
