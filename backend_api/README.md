## UAV Log Viewer - Backend API

Agentic chatbot backend that ingests UAV flight logs, builds retrieval context, and answers questions with grounded, friendly responses.

## End-to-End Request Cycle

### 1) Client uploads a flight log
```http
POST /api/flight-data
Headers: X-Session-ID: <session_id>
Body: JSON flight data
```
What happens:
- Session is created/updated and raw `flight_data` is stored.
- TelemetryService derives per-stream data (GPS, ALTITUDE, BATTERY, ATTITUDE, EVENTS) with statistics and rich metadata (time range, sampling rate, missingness, GPS bbox, units).
- Two kinds of RAG artifacts are produced for this session:
  - Text dumps (for transparency and debugging) written to `rag_docs/session_<session_id>/` (e.g., `000_summary.txt`, `..._points.txt`, etc.).
  - Structured "stream cards" and derived summaries written as JSON to the same folder (e.g., `900_session_meta.json`, `901_stream_gps.json`, `930_flight_overview.json`, etc.).
- All artifacts are embedded and upserted into Qdrant under a per-session collection `session_<session_id>` (if Qdrant is configured).

Details on artifacts:
- Text dumps are human-friendly and mirror the telemetry (e.g., `GPS POINTS CHUNK N` with CSV-like rows). These help you audit exactly what goes into retrieval.
- Stream cards are compact JSON facts designed for LLMs: consistent keys (`stream`, `statistics`, `units`, `time`, `metadata`) so the agent can quote precise values (min/max/mean, sampling rate, missingness, bbox).
- Derived cards (e.g., `flight_overview`, `data_quality_overview`, `gps_issues_overview`, `anomalies_overview`) are higher-level summaries that answer common “overview” questions quickly.

### 2) User asks a question
```http
POST /api/chat
Headers: X-Session-ID: <session_id>
Body: {
  "message": "What was the maximum altitude?",
  "sessionId": "<session_id>",
  "timestamp": 1234567890
}
```
What happens:
- The message is appended to the session conversation.
- The agent starts a single-step RAG answer flow:
  1. Embed the user question.
  2. Retrieve from the per-session Qdrant collection (and optionally the global docs collection), then apply thresholds: `RETRIEVAL_MIN_SCORE` and `RETRIEVAL_MIN_HITS`.
  3. Build a compact context from the top matches (stream cards first, then text dumps); redact session identifiers.
  4. Ask Gemini to answer strictly from the context (temperature 0.0). If the facts are missing, the model is instructed to say what is needed.
  5. Run a verification pass to ensure the answer is supported by the context; if not, abstain.
  6. Sanitize for plain text output (no markdown bullets or escaped characters); never show session IDs.
- The final answer is returned and appended to the conversation history.

### 3) Optional web/doc search (opt-in)
- If `WEB_TOOL_ENABLED=true` and the user explicitly requests a web/doc search (configurable triggers), a small snippet list is appended to the context before answering.

## Grounding, Safety, and Output Controls

- Grounding: `GROUNDING_REQUIRED=true`, `RETRIEVAL_MIN_SCORE`, `RETRIEVAL_MIN_HITS` enforce answer-from-context-or-abstain.
- Verification: answers are fact-checked against the same context.
- Redaction: `REDACT_SESSION_IDS=true` strips session identifiers from both context and answers.
- Plain text: `SANITIZE_OUTPUT=true` removes markdown bullets, backticks, brackets, and escape characters.
- Citations: `REQUIRE_CITATIONS` can enable/disable minimal source tags in answers (disabled by default).

Verification specifics:
- Verification runs a second deterministic pass (“OK/UNSUPPORTED”) against the exact RAG context. Any unsupported claims force a safe abstention with a request for more data.
- This dramatically reduces hallucinations at the cost of sometimes asking you to clarify or upload more data.

## Key Endpoints

- Health: `GET /api/health`
- Upload flight data: `POST /api/flight-data`
- Chat: `POST /api/chat`
- Session summary: `GET /api/session/<session_id>/summary`
- Telemetry by parameter: `GET /api/telemetry/<session_id>/<parameter>`
- Anomalies: `GET /api/anomalies/<session_id>`

## Configuration (excerpt)

Add to `.env`:
```bash
# Required
GOOGLE_API_KEY=your_gemini_api_key

QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=...
FLASK_PORT=8000

# Guardrails & Output
GROUNDING_REQUIRED=true
RETRIEVAL_MIN_SCORE=0.75
RETRIEVAL_MIN_HITS=2
REQUIRE_CITATIONS=false
DISABLE_SECOND_PASS_ON_RAG=true
SANITIZE_OUTPUT=true
REDACT_SESSION_IDS=true
WEB_TOOL_ENABLED=false
```

## Running Locally

```bash
cd backend_api
cp .env.example .env
# edit .env with your keys

conda activate arena
pip install -r requirements.txt
python app.py  # or: flask run --host=0.0.0.0 --port=8000
```

## Observability Tips

- Check `rag_docs/session_<session_id>/` to see exactly what was indexed (both text and JSON stream cards).
- Use `GET /api/health` to confirm Qdrant availability.
- To clear all Qdrant collections: `python backend_api/clear_qdrant.py --dry-run` (or `--yes` to delete).

Telemetry and indexing notes:
- Each session creates/uses its own Qdrant collection `session_<session_id>` to isolate retrieval by user/session.
- Vector size is governed by the embeddings model (Google `text-embedding-004`). Distance is COSINE by default.

## Project Structure (abridged)

```
backend_api/
├── app.py                 # Flask app & endpoints
├── agent.py               # RAG-first agent with grounding & verification
├── telemetry_service.py   # Rich extraction + metadata
├── ingestion_agent.py     # Stream cards & derived overviews + indexing
├── gemini_service.py      # Gemini chat, embeddings, sanitization, redaction
├── qdrant_service.py      # Vector DB integration
├── session_manager.py     # Session store & summaries
├── config.py              # Feature flags & settings
└── clear_qdrant.py        # Utility script to wipe Qdrant collections
```

## Example Queries

- What was the highest altitude?
- Are there any anomalies in this flight?
- Can you spot any issues in the GPS data?
- How long was the total flight time?

The agent answers in a friendly, interactive tone, grounded strictly on retrieved context.

Production recommendation:
- Enable Qdrant for best accuracy and lowest hallucination rate. Keep `GROUNDING_REQUIRED=true` and sensible `RETRIEVAL_MIN_*` thresholds. Reserve `GROUNDING_REQUIRED=false` only for exploratory/testing scenarios.

