import json
import os

import pytest

from rag import EventIndex, _clean_since, answer_question, run_search_events


@pytest.fixture
def events_log(tmp_path):
    events = [
        {"timestamp": "2026-09-08T20:00:00", "action": "register", "user_id": "alice", "score": None, "outcome": "success"},
        {"timestamp": "2026-09-08T20:05:00", "action": "login", "user_id": "alice", "score": 0.91, "outcome": "success"},
        {"timestamp": "2026-09-08T20:10:00", "action": "login", "user_id": "alice", "score": 0.22, "outcome": "denied"},
    ]
    path = tmp_path / "events.log"
    with open(path, "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
    return str(path)


def test_clean_since_sanitizes_junk_values():
    assert _clean_since(None) is None
    assert _clean_since("null") is None
    assert _clean_since("None") is None
    assert _clean_since("") is None
    assert _clean_since(123) is None  # not a string at all
    assert _clean_since("2026-09-08T20:00:00") == "2026-09-08T20:00:00"


def test_search_ranks_relevant_query_above_irrelevant_one(events_log):
    index = EventIndex(events_log)
    relevant, _ = run_search_events(index, "failed login for alice")
    irrelevant, _ = run_search_events(index, "what is the weather today")

    assert len(relevant) > 0
    assert len(irrelevant) == 0  # filtered out by RELEVANCE_THRESHOLD


def test_answer_question_refuses_when_nothing_relevant(events_log):
    result = answer_question("what is the weather today", events_log)
    assert result["answer"] is None
    assert result["citations"] == []
    assert "No relevant events found" in result["note"]


def test_answer_question_degrades_without_anthropic_key(events_log, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BACKEND", raising=False)  # defaults to "anthropic"

    result = answer_question("failed login for alice", events_log)

    assert result["answer"] is None
    assert "ANTHROPIC_API_KEY is not set" in result["note"]
    assert len(result["retrieved"]) > 0


def test_answer_question_degrades_when_ollama_unreachable(events_log, monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "ollama")
    # A model name that can't exist on any server -- exercises the same
    # degrade path whether or not a local Ollama server happens to be
    # running in the environment this test executes in.
    monkeypatch.setenv("OLLAMA_MODEL", "definitely-not-a-real-model-xyz")

    result = answer_question("failed login for alice", events_log)

    assert result["answer"] is None
    assert len(result["retrieved"]) > 0
