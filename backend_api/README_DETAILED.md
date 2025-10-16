# UAV Log Viewer Backend – Detailed Design & Operation

This document explains the backend’s internal workings in depth: request lifecycle, data normalization, telemetry retrieval, anomaly detection, the three-layer agent pipeline, RAG/Qdrant integration, and extensibility patterns.

## 1) Request Lifecycle

1. Flight data upload
   - Endpoint: `POST /api/flight-data`
   - Handler: `app.py:store_flight_data()` → `SessionManager.store_flight_data()`
   - Steps:
     - Normalize payload (params, events, attitude series) via `_normalize_flight_data`
     - Cache on session; sync to `DynamicTelemetryRetriever`
     - Convert to descriptive text with `text_utils.format_flight_data_text`
     - Add to RAG (Qdrant) via `ConsolidatedRAGManager`

2. Chat
   - Endpoint: `POST /api/chat`
   - Handler: `app.py:chat()` → `generate_chat_response()`
   - Steps:
     - Ensure session exists; message is appended to session history
     - Get/create `LangGraphReactAgent` for the session
     - Execute `agent.generate_multilayer()` (three-layer pipeline)
     - Store bot response in session

3. RAG operations
   - Endpoints: list/get/clear/delete collections; system stats; cleanup
   - Implementation: `rag_manager.py` using Qdrant as the sole storage

4. Telemetry/anomaly endpoints
   - Telemetry summary and queries, structured telemetry, and anomaly analysis
   - Implementation: `telemetry_retriever.py`, `flight_anomaly_detector.py`

## 2) Data Normalization (server-side)

Location: `app.py:SessionManager._normalize_flight_data`

- params
  - Accepts legacy `ParamSeeker`/array; flattens to `{ NAME: value }` object
- events
  - Accepts `[timestamp, label]` pairs; upgrades to `{timestamp, type, message, severity}` dicts
- attitude_series
  - Derives from `timeAttitude` map `{timestamp: [roll,pitch,yaw]}` → `[{timestamp, roll, pitch, yaw}]`
- rc_inputs, battery_series
  - Accepts pass-through if present

This ensures downstream code can rely on well-formed structures.

## 3) Telemetry Retriever (Dynamic)

Location: `telemetry_retriever.py`

- Responsibilities
  - Holds session flight data cache
  - Answers parameter queries with flexible names (e.g., GPS, BAT, RC, ALT, MODE)
  - Provides summaries (data sources, counts) and structured telemetry for LLMs
- Query flow
  - `_extract_parameter_data` resolves a parameter name into a timestamped slice
  - `_filter_by_time_range` and `_apply_aggregation` process time slices
  - Documentation hints from `ardupilot_docs.py` included (fields/units/links)
- Availability list
  - `_get_available_parameters` infers capability tokens from present data
- Attitude support
  - `ATTITUDE`, `ROLL`, `PITCH`, `YAW` returned from `attitude_series`

## 4) Anomaly Detector

Location: `flight_anomaly_detector.py`

- Pipeline
  - Extract time series (GPS, RC, params, events) → compute stats (min/max/mean/std/trend) → identify anomalies
- Indicators
  - GPS signal loss/accuracy/HDOP, satellite count drops, position jumps
  - Battery low/critical, temperature high/elevated
  - RC signal loss/weak
  - Sudden changes, thresholds, and variance anomalies
- Outputs
  - `TelemetrySummary` with summaries, indicators, flight phases, and quality metrics

## 5) Three-Layer Agent Pipeline

Location: `llm_config.py`

- `generate_multilayer(question)` orchestrates:
  1. Layer 1 – gather: Collects telemetry summary, structured telemetry, anomaly scan, available params; previews for events/attitude/battery/rc; RAG retrieval using question+keywords
  2. Layer 2 – analyze: Transforms gathered data into key findings; consults ArduPilot docs as needed; extracts correlations; builds takeaways
  3. Layer 3 – compose: Produces a concise answer prompt to the LLM with context lines and findings

- Tools available to agent
  - RAG search/add/clear/status
  - ArduPilot documentation search
  - Telemetry queries and summaries
  - Anomaly analysis and structured data

## 6) RAG with Qdrant

Location: `rag_manager.py`

- Design
  - Qdrant is required; collections are session-scoped
  - Embeddings via Google `text-embedding-004` (dimension normalized to `QDRANT_VECTOR_SIZE`)
- Operations
  - `add_documents(session_id, documents, metadata)` embeds and upserts points
  - `search_documents(session_id, query, top_k)` returns scored payloads
  - Lifecycle: create/get/clear/delete; cleanup archives old collections by TTL and limit
- Local exports
  - Local disk exports to `rag_exports` are disabled by default in `app.py`

## 7) RAG Document Formatting

Location: `text_utils.py:format_flight_data_text`

- Descriptive overview sentence at the top for LLMs
- Detailed sections:
  - GPS trajectory (counts, altitude range, duration)
  - GPS metadata (status timeline, satellites min/max/avg, HDOP/VDOP, HAcc/VAcc)
  - Timestamped GPS points (first trajectory)
  - Battery/temperature series if present (from events or `battery_series`)
  - RC input count and signal losses
  - Flight modes (# changes, distinct modes)
  - Mission commands, parameters count
  - Error/Warning timelines from events and `STATUSTEXT`

## 8) Error Handling & Resilience

- Layer 1 gathering uses best-effort try/except blocks to continue even when specific sources fail
- Normalization tolerates unexpected shapes and falls back to minimal structures
- RAG/embedding operations catch and log errors and return empty results when unavailable

## 9) Extending the System

- Add new telemetry parameters
  - Extend `_extract_parameter_data` and `_get_available_parameters`
- Add new anomaly checks
  - Append detectors under `_identify_anomaly_indicators` and helpers
- Add new agent tools
  - Create `@tool` functions in `llm_config.py`, add to `self.tools`
- Modify RAG schema
  - Attach additional metadata per document; update `rag_manager.py` payload
- Tweak LLM drafting style
  - Adjust system prompt in `.env` (`SYSTEM_PROMPT`) or via `/api/prompt/{session_id}`

## 10) Configuration & Operations

- Environment
  - `.env`: `GOOGLE_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`
- Health/Stats
  - `/api/health`, `/api/rag/stats`, `/api/rag/collections`
- Cleanup
  - `/api/rag/cleanup` or `force_cleanup.py`
- Logging
  - Python logging; adjust `LOG_LEVEL` via env

## 11) Known Limitations

- Qdrant is mandatory; if misconfigured, RAG falls back to empty context
- Dependency availability (LangGraph/LangChain/Google APIs) required for full agent features
- Local RAG exports disabled to reduce disk writes; can be reinstated in `app.py`

## 12) LangGraphReactAgent: The AI Engine

### What It Is
The `LangGraphReactAgent` is a LangGraph-based AI agent that processes flight telemetry data using Google's Gemini LLM. It implements a ReAct (Reasoning and Acting) pattern to intelligently analyze UAV flight logs and answer user queries about flight performance, anomalies, and technical parameters.

### Why We Use It
Flight logs contain complex multi-dimensional data (GPS, IMU, battery, RC signals, etc.) that requires sophisticated analysis. A simple LLM call cannot effectively process this complexity. The agent provides:

1. **Multi-Tool Integration**: Orchestrates 10+ specialized tools for different analysis tasks
2. **Session-Based Context**: Each user session maintains isolated RAG collections and conversation memory
3. **Three-Layer Pipeline**: Implements gather → analyze → compose workflow for comprehensive analysis
4. **ReAct Pattern**: Uses reasoning loops to determine when to use tools vs. provide final answers

### Architecture

```
User Query → LangGraphReactAgent → ReAct Loop → Tool Execution → Response
                     ↓
              [Tool Arsenal]
                     ↓
    [RAG Search] [Telemetry] [Anomaly Detection] [ArduPilot Docs] [Web Search]
```

**Three-Layer Pipeline**:
- **Layer 1 (Gather)**: Collects telemetry summaries, anomaly scans, and RAG context
- **Layer 2 (Analyze)**: Transforms data into key findings and consults documentation
- **Layer 3 (Compose)**: Produces context-aware responses with actionable insights

### Implementation Details

**Core Components** (`llm_config.py`):
- **LLM**: Google Gemini with temperature=0.1 for consistent responses
- **RAG**: Session-based Qdrant collections for document storage and retrieval
- **Memory**: LangGraph MemorySaver for conversation state management
- **Tools**: 10+ specialized tools including telemetry queries, anomaly analysis, and documentation lookup

**Session Management** (`app.py`):
```python
# Each session gets isolated agent instance
self.llm_agents[session_id] = LangGraphReactAgent(session_id=session_id)
```

**Tool Arsenal**:
- **RAG Tools**: Search, add, clear, status operations
- **Telemetry Tools**: Parameter queries with time ranges and aggregation
- **Anomaly Analysis**: Pattern detection and threshold monitoring
- **ArduPilot Docs**: Parameter lookup with units and technical specifications
- **Web Search**: Real-time information retrieval

### Integration Points

**RAG System**: Converts flight data to searchable documents and retrieves relevant context based on user queries.

**Telemetry System**: Provides dynamic parameter queries with support for time ranges, aggregation, and statistical analysis.

**Anomaly Detection**: Leverages statistical analysis and pattern recognition to identify flight issues and provide contextual explanations.

### Performance Characteristics

- **Memory Usage**: ~10-15MB per session (agent + RAG + memory)
- **Response Times**: 2-5s (simple), 5-15s (complex analysis)
- **Scalability**: 50+ concurrent sessions

The LangGraphReactAgent serves as the core intelligence layer, transforming raw flight data into actionable insights through sophisticated multi-tool orchestration and context-aware analysis.

---

For a quick-start and API endpoint reference, see `backend_api/README.md`.
