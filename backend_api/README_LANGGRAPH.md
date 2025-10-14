# LangGraph React Agent with Gemini API and Session-based RAG

This document describes the updated `llm_config.py` implementation that uses LangGraph React agents with Google's Gemini API and session-based RAG functionality.

## Features

- **LangGraph React Agent**: Implements the ReAct (Reasoning and Acting) pattern for intelligent tool usage
- **Gemini API Integration**: Uses Google's Gemini Pro model for natural language processing
- **Session-based RAG**: Maintains separate document collections per session
- **Backward Compatibility**: Maintains compatibility with the original `GenAIWrapper` interface
- **Tool Integration**: Built-in tools for RAG operations (search, add documents, clear, status)

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables by creating a `.env` file:
```bash
cp .env.example .env
```

3. Add your Google API key to the `.env` file:
```
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_MODEL_NAME=gemini-pro
```

## Usage

### Basic Usage

```python
from llm_config import LangGraphReactAgent

# Initialize the agent
agent = LangGraphReactAgent(
    system_prompt="You are a helpful AI assistant for UAV log analysis.",
    session_id="my_session_001"
)

# Generate a response
response = agent.generate("What are the different flight modes in UAV systems?")
print(response)
```

### RAG Functionality

```python
# Add documents to the session
documents = [
    "UAV flight logs contain telemetry data including GPS coordinates.",
    "MAVLink is a communication protocol for UAV systems.",
    "Flight modes include STABILIZE, LOITER, AUTO, and RTL."
]

agent.add_rag_documents(documents)

# Generate response with RAG context
rag_response = agent.generate_with_rag(
    "Explain MAVLink protocol", 
    top_k=2
)

print(rag_response['response'])
print(f"Used {rag_response['context_count']} context documents")
```

### Session Management

```python
# Get session information
session_info = agent.get_session_info()
print(f"Session ID: {session_info['session_id']}")
print(f"Documents: {session_info['rag_status']['document_count']}")

# Clear session documents
agent.clear_rag_documents()

# Check RAG status
status = agent.get_rag_status()
print(status)
```

### Backward Compatibility

The original `GenAIWrapper` interface is still supported:

```python
from llm_config import GenAIWrapper

# Use the old interface
wrapper = GenAIWrapper(
    system_prompt="You are a helpful assistant.",
    enable_rag=True,
    session_id="compat_session"
)

# All original methods work
wrapper.add_rag_documents(["Document text"])
response = wrapper.generate("Hello!")
status = wrapper.get_rag_status()
```

## Architecture

### LangGraph React Agent

The agent implements the ReAct pattern with the following components:

1. **State Management**: Uses `AgentState` to track conversation state, RAG context, and tool results
2. **Tool Integration**: Built-in tools for RAG operations
3. **Memory**: Conversation history is maintained using `MemorySaver`
4. **Conditional Flow**: Agent decides whether to use tools or provide direct responses

### Session-based RAG

Each session maintains its own:
- Document collection
- BM25 search index
- Document metadata
- Search history

### Available Tools

1. **search_rag_documents**: Search through session documents
2. **add_documents_to_rag**: Add new documents to the session
3. **clear_rag_documents**: Clear all session documents
4. **get_rag_status**: Get current RAG system status

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Google Gemini API key | Required |
| `GOOGLE_MODEL_NAME` | Gemini model name | `gemini-pro` |
| `SYSTEM_PROMPT` | Default system prompt | UAV analysis assistant |
| `API_HOST` | API host address | `0.0.0.0` |
| `API_PORT` | API port | `8000` |
| `SESSION_TIMEOUT_HOURS` | Session timeout | `24` |
| `MAX_SESSIONS` | Maximum concurrent sessions | `100` |

### Model Configuration

The agent uses Google's Gemini Pro model with:
- Temperature: 0.1 (for consistent responses)
- Tool binding: Enabled for ReAct pattern
- Memory: Persistent conversation history

## Testing

Run the test suite to verify the implementation:

```bash
python test_langgraph_agent.py
```

The test suite includes:
- Agent initialization
- RAG functionality
- Document retrieval
- Response generation
- Backward compatibility

## Error Handling

The implementation includes comprehensive error handling:
- API key validation
- Model initialization errors
- RAG operation failures
- Tool execution errors
- Network connectivity issues

## Performance Considerations

- **Memory Usage**: Each session maintains its own document index
- **API Limits**: Respects Google's API rate limits
- **Session Cleanup**: Automatic cleanup of expired sessions
- **Document Limits**: Configurable limits on document size and count

## Migration from Original Implementation

The new implementation is fully backward compatible. To migrate:

1. Update your `requirements.txt` with new dependencies
2. Set up environment variables
3. No code changes required for existing `GenAIWrapper` usage
4. Optionally upgrade to `LangGraphReactAgent` for enhanced features

## Troubleshooting

### Common Issues

1. **API Key Not Found**: Ensure `GOOGLE_API_KEY` is set in your `.env` file
2. **Import Errors**: Install all dependencies from `requirements.txt`
3. **Memory Issues**: Clear session documents when no longer needed
4. **Rate Limiting**: Implement appropriate delays between API calls

### Debug Mode

Enable debug logging by setting:
```
LOG_LEVEL=DEBUG
```

## Future Enhancements

- Multi-modal support (images, audio)
- Advanced RAG techniques (hybrid search, re-ranking)
- Custom tool development
- Integration with vector databases
- Real-time streaming responses
