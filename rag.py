"""RAG over the enrollment/auth event log, plus one agentic tool
(search_events) the LLM calls to fetch snippets instead of the whole log
being stuffed into the prompt.

Tool contract -- search_events:
  input:  {"query": str, "since": str | null}   # since: ISO-8601 timestamp
  output: up to 5 {"timestamp", "text"} snippets, most relevant first
  Every invocation is logged (query, since, result count); a call that
  doesn't finish within TOOL_TIMEOUT_SECONDS is aborted and reported back
  to the model as an error rather than hanging the request.
"""

import concurrent.futures
import json
import logging
import os

import numpy as np

logger = logging.getLogger("rag.search_events")

TOOL_TIMEOUT_SECONDS = 5
TOOL_CALL_ROUNDS = 3  # cap so a misbehaving model can't loop forever

# The hybrid score (0.5*cosine + 0.5*keyword-overlap) sits around 0.45-0.5
# even for genuinely unrelated queries, because short-sentence embeddings
# rarely score near zero. On this project's own tiny sample, on-topic
# queries scored 0.6+ and off-topic ones topped out at ~0.5 -- 0.55 splits
# that gap. Empirically chosen from a handful of examples, not a
# calibrated benchmark; same caveat as MATCH_THRESHOLD in app.py.
RELEVANCE_THRESHOLD = 0.55

SEARCH_EVENTS_SCHEMA = {
    "name": "search_events",
    "description": (
        "Search the face-auth event log (register/login/identify actions) for "
        "snippets relevant to a natural-language query. Returns up to 5 "
        "matching events with timestamps, for citing in the final answer."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "What to search for, e.g. 'failed logins for alice'.",
            },
            "since": {
                "type": ["string", "null"],
                "description": "Optional ISO-8601 timestamp; only events at or after this time.",
            },
        },
        "required": ["query"],
    },
}

_embedder = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer

        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def _event_to_text(event):
    score = event.get("score")
    score_str = f"{score:.3f}" if isinstance(score, (int, float)) else "n/a"
    return (
        f"At {event['timestamp']}, a '{event['action']}' event for user "
        f"'{event['user_id']}' resulted in '{event['outcome']}' (score={score_str})."
    )


def load_events(events_log_path):
    events = []
    if not os.path.exists(events_log_path):
        return events
    with open(events_log_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


class EventIndex:
    """Hybrid (semantic + lexical) search over event-log snippets.

    Rebuilt from events.log on every /api/ask call: the log here is a
    small demo audit trail, not a production-scale corpus, so a full
    rebuild per request is simpler than maintaining a persistent,
    incrementally-updated index. See DESIGN.md for how this would need to
    change (persistent OpenSearch index, incremental ingestion) at scale.
    """

    def __init__(self, events_log_path="events.log"):
        self.events = load_events(events_log_path)
        self.texts = [_event_to_text(e) for e in self.events]
        if self.texts:
            self.vectors = _get_embedder().encode(self.texts, normalize_embeddings=True)
        else:
            self.vectors = np.zeros((0, 384))

    def search(self, query, since=None, top_k=5):
        candidates = list(range(len(self.events)))
        if since:
            candidates = [i for i in candidates if self.events[i]["timestamp"] >= since]
        if not candidates:
            return []

        q_vec = _get_embedder().encode([query], normalize_embeddings=True)[0]
        knn_scores = self.vectors[candidates] @ q_vec

        query_terms = set(query.lower().split())
        bm25_scores = np.array(
            [len(query_terms & set(self.texts[i].lower().split())) for i in candidates],
            dtype=float,
        )
        if bm25_scores.max() > 0:
            bm25_scores = bm25_scores / bm25_scores.max()

        # Simple hybrid: average normalized semantic + lexical scores. A
        # real OpenSearch setup would do this inside the engine (a bool
        # query mixing `knn` and `match` clauses) instead of in Python.
        hybrid = 0.5 * knn_scores + 0.5 * bm25_scores
        order = np.argsort(-hybrid)[:top_k]

        return [
            {
                "text": self.texts[candidates[i]],
                "event": self.events[candidates[i]],
                "score": float(hybrid[i]),
            }
            for i in order
            if hybrid[i] >= RELEVANCE_THRESHOLD
        ]


def run_search_events(index, query, since=None):
    """Execute the search_events tool with a hard timeout and invocation
    logging. Returns (results, error) -- error is a string on timeout."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(index.search, query, since)
        try:
            results = future.result(timeout=TOOL_TIMEOUT_SECONDS)
            logger.info(
                "search_events(query=%r, since=%r) -> %d results", query, since, len(results)
            )
            return results, None
        except concurrent.futures.TimeoutError:
            logger.warning(
                "search_events(query=%r, since=%r) timed out after %ss",
                query, since, TOOL_TIMEOUT_SECONDS,
            )
            return [], f"search_events timed out after {TOOL_TIMEOUT_SECONDS}s"


def answer_question(question, events_log_path="events.log"):
    index = EventIndex(events_log_path)

    initial_results, _ = run_search_events(index, question)
    if not initial_results:
        return {"answer": None, "citations": [], "note": "No relevant events found."}

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "answer": None,
            "citations": [r["event"]["timestamp"] for r in initial_results],
            "retrieved": [r["text"] for r in initial_results],
            "note": "ANTHROPIC_API_KEY is not set; returning retrieved snippets without generation.",
        }

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    messages = [
        {
            "role": "user",
            "content": (
                "Answer the question using only the search_events tool to look up "
                "the face-auth event log. Cite the timestamp of every event you "
                "rely on. If nothing relevant turns up, say so plainly instead of "
                f"guessing.\n\nQuestion: {question}"
            ),
        }
    ]

    citations = set()
    for _ in range(TOOL_CALL_ROUNDS):
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=1024,
            tools=[SEARCH_EVENTS_SCHEMA],
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            text = "".join(block.text for block in response.content if block.type == "text")
            return {"answer": text, "citations": sorted(citations)}

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            results, error = run_search_events(
                index, block.input.get("query", ""), block.input.get("since")
            )
            for r in results:
                citations.add(r["event"]["timestamp"])
            if error:
                payload = {"error": error}
            elif not results:
                payload = {"results": [], "note": "No relevant events found."}
            else:
                payload = {
                    "results": [
                        {"timestamp": r["event"]["timestamp"], "text": r["text"]} for r in results
                    ]
                }
            tool_results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(payload)}
            )
        messages.append({"role": "user", "content": tool_results})

    return {"answer": None, "citations": sorted(citations), "note": "Tool-call budget exhausted."}
