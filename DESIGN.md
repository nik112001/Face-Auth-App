# Design notes: embeddings, vector search, and RAG

## The retrieval problem

This app has two retrieval problems, not one. The first is **1:N face
identification**: given a frame, find which (if any) of N enrolled users it
belongs to, without being told a username up front. The second is **RAG over
the event log**: given a natural-language question, find which (if any) of
the logged register/login/identify events are relevant, and answer only from
those. Both are "find the nearest thing(s) in embedding space" problems, and
both are implemented the same way in this codebase for that reason: embed,
index, search top-K, then decide.

The original v1 (`/api/login`) was never a retrieval problem at all -- it was
1:1 verification, comparing exactly two things the caller already named
(a username and a frame). That's why it didn't need an index, and why
`store.verify()` still doesn't use one (see below).

## Why embeddings + ANN over pixel L2

v1 compared a flattened 100x100 grayscale crop by sum-of-squared-differences.
That "encoding" has no invariance to lighting, pose, expression, or camera
sensor -- two photos of the same person taken a minute apart can differ more,
in raw pixel space, than photos of two different people taken under similar
conditions. A learned embedding (here, FaceNet/InceptionResnetV1 pretrained
on VGGFace2) is trained specifically so that same-identity photos land close
together and different-identity photos land far apart, *despite* those
nuisance variations. Once embeddings are unit-normalized, "close together" is
just cosine similarity, i.e. a dot product -- which is also the operation
every ANN index (HNSW, IVF, etc.) is built to answer quickly at scale. That's
the real reason to make this swap: it's not just "a better distance metric,"
it's moving to a representation where fast approximate search is even
possible.

FaceNet was chosen over ArcFace/insightface specifically because it's pure
PyTorch (no ONNXRuntime dependency) -- see the comment at the top of
`embeddings.py`.

## Threshold calibration

`MATCH_THRESHOLD` (default 0.5) and `RELEVANCE_THRESHOLD` in `rag.py`
(default 0.55) are both **not calibrated** in the rigorous sense -- they're
each backed by exactly one sanity check (one genuine pair, one impostor pair
for faces; a handful of on-topic/off-topic queries for RAG), not an ROC
analysis over a real genuine-vs-impostor distribution. That's an honest gap,
not an oversight: doing this properly needs a labeled dataset of multiple
people with multiple photos each, and a threshold chosen to hit a target
false-accept rate for this app's actual risk tolerance (which is a product
decision, not just a math one). Until that exists, treat both thresholds as
reasonable-looking defaults, not verified guarantees.

## HNSW vs. IVF

`OpenSearchStore` indexes with HNSW (via `engine: nmslib`), which is the
right default here: it gives high recall at low latency for a corpus that's
small-to-medium and read-heavy (identify happens far more often than
enroll), at the cost of a larger in-memory graph and slower bulk inserts.
IVF (inverted file index) trades that around: cheaper to build and update,
and more memory-efficient at very large scale, but needs a training step
over representative vectors before it can be built at all, and recall
degrades unless the number of probed clusters is tuned as data grows. For
a face-enrollment corpus that grows by ones (a person registers, once) and
is queried constantly (every login/identify), HNSW's build cost is a
non-issue and its query-time behavior is exactly what matters. IVF would
make more sense if this were reindexing millions of vectors in bulk on a
schedule, which isn't this app's access pattern.

## Access control before retrieval

`/api/identify` currently returns a match to *anyone who calls it* -- there's
no check that the caller is allowed to run a 1:N search over the entire
enrolled population before the search happens. `/api/login`'s 1:1 shape
implicitly limits blast radius (you can only ever learn "does this face
match *this named user*"), but 1:N identification is a fundamentally
higher-privilege operation: it turns "whose face is this" into an oracle
against everyone in the system. In a real deployment, `/api/identify` (and
`/api/ask`, which can retrieve any user's login history) would need to sit
behind its own authorization check -- who is allowed to ask "who is this,"
not just "is this you" -- decided before the vector search runs, not
filtered from its results afterward.

## The open security gap: liveness

None of this -- better embeddings, an ANN index, RAG -- touches the
project's most exploitable weakness, carried over unchanged from v1: there
is no liveness check. A printed photo or a phone screen showing an enrolled
user's face still authenticates. Embedding quality and matching threshold
are irrelevant to this attack, because the attack targets the assumption
underneath both ("the pixels represent a live, present person"), not the
matching logic itself. This stays the top item in the Roadmap for a reason:
it's the gap most likely to matter in an actual incident, and the one this
branch does not close.

## What's implemented vs. planned

**Implemented:** FaceNet embeddings with cosine matching; a dual-backend
vector store (local numpy fallback, OpenSearch HNSW) behind one interface;
1:N `/api/identify`; an event log feeding a hybrid (semantic + lexical)
RAG index; `/api/ask` with one agentic tool (`search_events`) instead of
prompt-stuffing the whole log; a pluggable LLM backend for `/api/ask`
(hosted Claude or a local Ollama model, same tool contract either way);
graceful degradation with no OpenSearch and no LLM backend reachable at
all -- the endpoint returns raw retrieved snippets instead of failing.

The Ollama path also surfaced a real reliability gap worth naming: a
smaller local model is less disciplined about the tool's JSON schema than
a frontier hosted model -- it sent `since` as the literal string `"null"`
in testing, which `run_search_events` now sanitizes rather than trusting.
That's a concrete illustration of a broader point: model choice isn't just
an accuracy tradeoff, it's a tradeoff in how much defensive code the
calling application needs around it.

**Planned, not built:** calibrated thresholds from a real genuine/impostor
dataset; authorization in front of `/api/identify` and `/api/ask`; liveness
detection.

## Monitoring

If this ran for real, the metrics worth alerting on aren't generic API
metrics -- they're the ones that would catch the matcher silently degrading
or being attacked: the distribution of match scores over time (a sudden
shift suggests either a threshold problem or a spoofing attempt), the
`/api/identify` no-match rate (a spike suggests either a UX problem or
someone probing the system), and `search_events` tool-call latency/timeout
rate (a proxy for whether the event log has grown past what a per-request
in-memory rebuild can handle -- see `rag.py`'s `EventIndex` docstring).
