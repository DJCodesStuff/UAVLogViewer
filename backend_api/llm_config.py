# llm_config.py - LangGraph React Agent with Gemini API and Session-based RAG

import os
import re
from typing import Dict, List, Any, Optional, TypedDict, Annotated
from dotenv import load_dotenv
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from rag_manager import ConsolidatedRAGManager, get_global_rag_manager
from prompts import get_prompt, ARDUPILOT_DATA_ANALYST_PROMPT
from text_utils import clean_llm_response, sanitize_text
from conversation_state import get_global_conversation_manager, ConversationIntent, ConversationState
from telemetry_retriever import get_global_telemetry_retriever, TelemetryQuery

# Load environment variables
load_dotenv()

class AgentState(TypedDict):
    """State for the LangGraph agent"""
    messages: Annotated[List, add_messages]
    session_id: str
    rag_context: List[str]
    current_tool: Optional[str]
    tool_result: Optional[str]

class SessionBasedRAG:
    """Session-based RAG implementation using the consolidated system"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.rag_manager = get_global_rag_manager()
        self.session_documents = []
        self.document_count = 0
    
    def add_documents(self, texts: List[str]) -> str:
        """Add documents to the session-based RAG engine"""
        if isinstance(texts, str):
            texts = [texts]
        
        # Use the consolidated RAG manager
        result = self.rag_manager.add_documents(
            session_id=self.session_id,
            documents=texts
        )
        
        # Update local tracking
        self.session_documents.extend(texts)
        self.document_count += len(texts)
        
        return result
    
    def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        """Retrieve relevant documents from the session-based RAG engine"""
        results = self.rag_manager.search_documents(
            session_id=self.session_id,
            query=query,
            top_k=top_k
        )
        
        # Extract document text from results
        return [result["document"] for result in results]
    
    def clear_documents(self) -> str:
        """Clear all documents from the session-based RAG engine"""
        result = self.rag_manager.clear_collection(self.session_id)
        self.session_documents = []
        self.document_count = 0
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the session-based RAG engine"""
        status = self.rag_manager.get_collection_status(self.session_id)
        return {
            "session_id": self.session_id,
            "document_count": status.get("document_count", 0),
            "session_documents": len(self.session_documents),
            "has_documents": status.get("has_documents", False),
            "engine_ready": status.get("has_documents", False),
            "collection_id": status.get("collection_id"),
            "status": status.get("status", "unknown")
        }

class LangGraphReactAgent:
    """LangGraph React Agent with Gemini API and Session-based RAG"""
    
    def __init__(self, system_prompt: Optional[str] = None, session_id: Optional[str] = None):
        # Load configuration from environment
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.model_name = os.getenv("GOOGLE_MODEL_NAME", "gemini-pro")
        self.system_prompt = system_prompt or os.getenv(
            "SYSTEM_PROMPT", 
            ARDUPILOT_DATA_ANALYST_PROMPT
        )
        
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables.")
        
        # Initialize Gemini model
        genai.configure(api_key=self.api_key)
        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=self.api_key,
            temperature=0.1
        )
        
        # Initialize session-based RAG
        self.session_id = session_id or "default_session"
        self.rag = SessionBasedRAG(self.session_id)
        
        # Initialize memory for conversation history
        self.memory = MemorySaver()
        
        # Define tools for the agent
        self.tools = [
            self._create_rag_search_tool(),
            self._create_rag_add_documents_tool(),
            self._create_rag_clear_tool(),
            self._create_rag_status_tool(),
            self._create_ardupilot_docs_tool(),
            self._create_web_search_tool(),
            self._create_telemetry_tool(),
            self._create_telemetry_summary_tool(),
            self._create_anomaly_analysis_tool(),
            self._create_structured_data_tool()
        ]
        
        # Create the agent graph
        self.agent = self._create_agent_graph()
    
    def _create_rag_search_tool(self):
        """Create a tool for searching RAG documents"""
        @tool
        def search_rag_documents(query: str, top_k: int = 3) -> str:
            """Search through session documents using RAG. Use this when you need to find relevant information from uploaded documents.
            
            Args:
                query: The search query
                top_k: Number of top results to return (default: 3)
            """
            results = self.rag.retrieve(query, top_k)
            if results:
                return f"Found {len(results)} relevant documents:\n" + "\n\n".join(results)
            else:
                return "No relevant documents found for the query."
        
        return search_rag_documents
    
    def _create_rag_add_documents_tool(self):
        """Create a tool for adding documents to RAG"""
        @tool
        def add_documents_to_rag(texts: str) -> str:
            """Add documents to the session-based RAG system for later retrieval.
            
            Args:
                texts: Document text to add (can be multiple documents separated by newlines)
            """
            # Split by double newlines to separate documents
            documents = [doc.strip() for doc in texts.split('\n\n') if doc.strip()]
            return self.rag.add_documents(documents)
        
        return add_documents_to_rag
    
    def _create_rag_clear_tool(self):
        """Create a tool for clearing RAG documents"""
        @tool
        def clear_rag_documents() -> str:
            """Clear all documents from the session-based RAG system."""
            return self.rag.clear_documents()
        
        return clear_rag_documents
    
    def _create_rag_status_tool(self):
        """Create a tool for checking RAG status"""
        @tool
        def get_rag_status() -> str:
            """Get the current status of the session-based RAG system."""
            status = self.rag.get_status()
            return f"RAG Status: {status}"
        
        return get_rag_status

    def _create_ardupilot_docs_tool(self):
        """Create ArduPilot documentation search tool"""
        @tool
        def search_ardupilot_documentation(query: str) -> str:
            """Search ArduPilot documentation for parameter information. Use this when you need detailed information about ArduPilot log message parameters, their meanings, units, and usage."""
            try:
                from ardupilot_docs import get_global_docs_retriever
                docs_retriever = get_global_docs_retriever()
                
                # Search for parameters matching the query
                results = docs_retriever.search_parameters(query)
                
                if not results:
                    return f"No ArduPilot parameters found matching '{query}'. Try searching for common parameters like GPS, BAT, ATT, MODE, ERR, RCIN, RSSI."
                
                response = f"ArduPilot Documentation Search Results for '{query}':\n\n"
                
                for result in results[:5]:  # Show top 5 results
                    response += f"Parameter: {result['parameter']}\n"
                    response += f"Description: {result['description']}\n"
                    response += f"Fields: {', '.join(result['fields']) if result['fields'] else 'No field details'}\n"
                    response += f"Documentation: https://ardupilot.org/plane/docs/logmessages.html#{result['parameter'].lower()}\n\n"
                
                response += "For more detailed information, visit: https://ardupilot.org/plane/docs/logmessages.html"
                
                return response
                
            except Exception as e:
                return f"Error searching ArduPilot documentation: {str(e)}"
        
        return search_ardupilot_documentation

    def _create_web_search_tool(self):
        """Create web search tool"""
        @tool
        def web_search(query: str) -> str:
            """Search the web for current information about a topic. Use this when you need up-to-date information that might not be in your training data."""
            try:
                import requests
                from bs4 import BeautifulSoup
                
                # Use DuckDuckGo for search (no API key required)
                search_url = f"https://html.duckduckgo.com/html/?q={query}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                response = requests.get(search_url, headers=headers, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                results = soup.find_all('div', class_='result')
                
                search_results = []
                for result in results[:3]:  # Limit to top 3 results
                    title_elem = result.find('a', class_='result__a')
                    snippet_elem = result.find('div', class_='result__snippet')
                    
                    if title_elem and snippet_elem:
                        title = title_elem.get_text().strip()
                        snippet = snippet_elem.get_text().strip()
                        search_results.append(f"Title: {title}\nSnippet: {snippet}")
                
                if search_results:
                    return "Search Results:\n" + "\n\n".join(search_results)
                else:
                    return "No search results found for the query."
                    
            except Exception as e:
                return f"Error performing web search: {str(e)}"
        
        return web_search

    def _create_telemetry_tool(self):
        """Create telemetry data retrieval tool"""
        @tool
        def get_telemetry_data(parameter: str, time_range: Optional[str] = None, aggregation: str = "raw") -> str:
            """Retrieve telemetry data for a specific parameter. Use this when the user asks about specific flight data parameters like GPS, ATT, BAT, etc."""
            try:
                telemetry_retriever = get_global_telemetry_retriever()
                
                # Map common parameter names to our internal names
                parameter_mapping = {
                    'BAT.Voltage': 'battery_voltage',
                    'BAT.Volt': 'battery_voltage',
                    'BAT.Temperature': 'temperature',
                    'BAT.Temp': 'temperature',
                    'GPS.NSats': 'satellites',
                    'GPS.Satellites': 'satellites',
                    'GPS.HDop': 'hdop',
                    'GPS.VDop': 'vdop',
                    'GPS.HAcc': 'hacc',
                    'GPS.VAcc': 'vacc',
                    'GPS.Status': 'gps_status',
                    'GPS.Fix': 'gps_status',
                    'RC.RSSI': 'rc_signal_strength',
                    'RC.Signal': 'rc_signal_strength',
                    'RC.Loss': 'rc_signal_lost',
                    'ALT': 'altitude',
                    'GPS.Alt': 'altitude',
                    'FLIGHT_TIME': 'flight_duration',
                    'DURATION': 'flight_duration'
                }
                
                # Use mapped parameter if available, otherwise use original
                mapped_parameter = parameter_mapping.get(parameter, parameter)
                
                # Parse time range if provided
                time_range_tuple = None
                if time_range:
                    try:
                        start, end = time_range.split(',')
                        time_range_tuple = (float(start), float(end))
                    except:
                        pass
                
                query = TelemetryQuery(
                    parameter=mapped_parameter,
                    time_range=time_range_tuple,
                    aggregation=aggregation
                )
                
                result = telemetry_retriever.query_telemetry(self.session_id, query)
                
                if "error" in result:
                    return f"I couldn't find that data: {result['error']}. {result.get('suggestion', '')}"
                
                # Format the response with comprehensive documentation
                response = f"Telemetry: {parameter}. "
                response += f"{result['documentation']['description']}. "
                response += f"Data points: {result['data_points']}.\n"
                
                # Add field-specific documentation
                if 'field_documentation' in result and result['field_documentation']:
                    response += f"\nFields:\n"
                    for field, doc in result['field_documentation'].items():
                        response += f"- {field}: {doc.get('description', 'No description')} ({doc.get('units', 'unknown units')})\n"
                
                # Add ArduPilot reference
                if 'ardupilot_reference' in result:
                    response += f"\nArduPilot Documentation: {result['ardupilot_reference']}\n"
                
                if result['data']:
                    if isinstance(result['data'], list) and len(result['data']) > 0:
                        # Show first few data points
                        sample_data = result['data'][:3]
                        response += f"Sample data: {sample_data}\n"
                    else:
                        response += f"Data: {result['data']}\n"
                
                return response
                
            except Exception as e:
                return f"Error retrieving telemetry data: {str(e)}"
        
        return get_telemetry_data

    def _create_telemetry_summary_tool(self):
        """Create telemetry summary tool"""
        @tool
        def get_telemetry_summary() -> str:
            """Get a brief, plain summary of what data is available for this session."""
            try:
                telemetry_retriever = get_global_telemetry_retriever()
                summary = telemetry_retriever.get_telemetry_summary(self.session_id)
                
                if "error" in summary:
                    return f"I couldn't get the data summary: {summary['error']}"
                
                bullets = []
                for source in summary.get('data_sources', [])[:3]:
                    bullets.append(f"- {source['type']}: {source['count']}")

                takeaway = "Data loaded."
                if bullets:
                    return takeaway + "\n" + "\n".join(bullets) + "\nNext: ask for a parameter you care about."
                return takeaway + "\nNext: ask for a parameter you care about."
                
            except Exception as e:
                return f"Error getting telemetry summary: {str(e)}"
        
        return get_telemetry_summary

    def _create_anomaly_analysis_tool(self):
        """Create anomaly analysis tool"""
        @tool
        def analyze_flight_anomalies(user_question: str = "") -> str:
            """Give a brief, plain-language anomaly check with up to 3 bullets and one next step."""
            try:
                telemetry_retriever = get_global_telemetry_retriever()
                analysis_result = telemetry_retriever.analyze_flight_anomalies(self.session_id, user_question)
                
                if "error" in analysis_result:
                    return f"I couldn't analyze the flight yet: {analysis_result['error']}. Try uploading the log or asking again."
                
                duration = analysis_result['telemetry_summary']['flight_duration']
                indicators = analysis_result['telemetry_summary']['anomaly_indicators_count']
                takeaway = (
                    "Bottom line: nothing clearly concerning." if indicators == 0 else
                    "Bottom line: a few things to look at."
                )

                bullets = []
                bullets.append(f"- Flight length: ~{duration:.0f}s")
                if indicators > 0:
                    for indicator in analysis_result['anomaly_indicators'][:2]:
                        bullets.append(f"- {indicator['type'].capitalize()}: {indicator['description']}")

                next_step = "Next: tell me what system to focus on (e.g., GPS, battery)."
                return takeaway + ("\n" + "\n".join(bullets) if bullets else "") + "\n" + next_step
                
            except Exception as e:
                return f"Error analyzing flight anomalies: {str(e)}"
        
        return analyze_flight_anomalies

    def _create_structured_data_tool(self):
        """Create structured telemetry data tool"""
        @tool
        def get_structured_flight_data() -> str:
            """Give a short summary of key flight stats with up to 3 bullets and one next step."""
            try:
                telemetry_retriever = get_global_telemetry_retriever()
                structured_data = telemetry_retriever.get_structured_telemetry_data(self.session_id)
                
                if "error" in structured_data:
                    return f"Error getting structured data: {structured_data['error']}"
                
                overview = structured_data['flight_overview']
                takeaway = "Quick summary: data is ready."
                bullets = [
                    f"- Duration: ~{overview['duration_seconds']:.0f}s",
                    f"- Data points: {overview['total_data_points']:,}",
                    f"- Parameters: {len(overview['parameters_available'])}"
                ]
                next_step = "Next: ask about a specific parameter (e.g., GPS altitude, battery)."
                return takeaway + "\n" + "\n".join(bullets[:3]) + "\n" + next_step
                
            except Exception as e:
                return f"Error getting structured flight data: {str(e)}"
        
        return get_structured_flight_data
    
    def _create_agent_graph(self) -> StateGraph:
        """Create the LangGraph agent with React pattern"""
        
        # Create tool node
        tool_node = ToolNode(self.tools)
        
        def should_continue(state: AgentState) -> str:
            """Determine whether to continue with tools or end"""
            messages = state["messages"]
            last_message = messages[-1]
            
            # If the last message is from the AI and contains tool calls, continue to tools
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "tools"
            # Otherwise, end the conversation
            return END
        
        def call_model(state: AgentState) -> Dict[str, Any]:
            """Call the Gemini model with the current state"""
            messages = state["messages"]
            
            # Add system message if not present
            if not messages or not isinstance(messages[0], SystemMessage):
                system_msg = SystemMessage(content=self.system_prompt)
                messages = [system_msg] + messages
            
            # Add RAG context if available
            if state.get("rag_context"):
                context_msg = HumanMessage(
                    content=f"Relevant context from documents:\n{chr(10).join(state['rag_context'])}"
                )
                messages.append(context_msg)
            
            # Encourage the model to consult ArduPilot docs when relevant
            guidance = HumanMessage(content=(
                "Reminder: If the user asks about ArduPilot parameters, message names, fields, or units, "
                "consult the ArduPilot documentation tool before finalizing your answer."
            ))

            # Get response from model with guidance
            response = self.llm.bind_tools(self.tools).invoke(messages + [guidance])
            
            return {"messages": [response]}
        
        # Create the graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", tool_node)
        
        # Add edges
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {
                "tools": "tools",
                END: END
            }
        )
        workflow.add_edge("tools", "agent")
        
        # Compile the graph
        return workflow.compile(checkpointer=self.memory)
    
    def add_rag_documents(self, texts: List[str]) -> str:
        """Add documents to the session-based RAG system"""
        return self.rag.add_documents(texts)
    
    def clear_rag_documents(self) -> str:
        """Clear all documents from the session-based RAG system"""
        return self.rag.clear_documents()
    
    def get_rag_status(self) -> Dict[str, Any]:
        """Get the current status of the session-based RAG system"""
        return self.rag.get_status()
    
    def retrieve_documents(self, query: str, top_k: int = 3) -> List[str]:
        """Retrieve relevant documents from the session-based RAG system"""
        return self.rag.retrieve(query, top_k)
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response using the LangGraph React agent with agentic conversation management"""
        try:
            if not prompt or not isinstance(prompt, str):
                raise ValueError("Prompt must be a non-empty string.")
            
            # Sanitize input prompt
            sanitized_prompt = sanitize_text(prompt)
            
            # Get conversation manager and update state
            conversation_manager = get_global_conversation_manager()
            telemetry_retriever = get_global_telemetry_retriever()
            
            # Check if flight data is available
            flight_data_available = telemetry_retriever.get_flight_data(self.session_id) is not None
            
            # Create initial state
            initial_state = {
                "messages": [HumanMessage(content=sanitized_prompt)],
                "session_id": self.session_id,
                "rag_context": [],
                "current_tool": None,
                "tool_result": None
            }
            
            # Run the agent
            config = {"configurable": {"thread_id": self.session_id}}
            result = self.agent.invoke(initial_state, config=config)
            
            # Extract the final response
            messages = result["messages"]
            if messages:
                last_message = messages[-1]
                if hasattr(last_message, 'content'):
                    raw_response = last_message.content
                    # Clean the response to ensure plain text output
                    response = clean_llm_response(raw_response)
                else:
                    response = clean_llm_response(str(last_message))
                
                # Update conversation state
                conversation_manager.update_conversation_state(
                    self.session_id, 
                    sanitized_prompt, 
                    response, 
                    flight_data_available
                )

                # Ensure we always have a context object for downstream checks
                context = conversation_manager.get_or_create_context(self.session_id)
                
                # Check if clarification is needed (only if response is not comprehensive)
                if len(response.strip()) > 50:  # Only check if we have a substantial response
                    clarification_request = conversation_manager.should_request_clarification(context)
                    
                    if clarification_request:
                        # Add clarification request to response with proper paragraph formatting
                        response += f"\n\n🤔 Clarification needed: {clarification_request.question}\n\n"
                        response += f"Context: {clarification_request.context}\n\n"
                        response += f"Options: {', '.join(clarification_request.options)}"
                
                # Add proactive suggestions if available with proper paragraph formatting
                if context and getattr(context, 'suggested_actions', None):
                    response += f"\n\n💡 Suggestions:\n"
                    for suggestion in context.suggested_actions:
                        response += f"• {suggestion}\n"
                
                return response
            
            return "No response generated."
            
        except Exception as e:
            return f"Error during generation: {str(e)}"

    # =====================
    # Three-layer Orchestrator
    # =====================
    def generate_multilayer(self, user_question: str) -> str:
        """Three-stage pipeline: gather → analyze (with docs) → compose."""
        if not isinstance(user_question, str) or not user_question.strip():
            return "Please provide a question."
        try:
            gathered = self._layer1_gather(user_question)
            analysis = self._layer2_analyze(user_question, gathered)
            final = self._layer3_compose(user_question, gathered, analysis)
            return final
        except Exception as e:
            return f"Error in multi-layer analysis: {str(e)}"

    def _layer1_gather(self, user_question: str) -> dict:
        """Gather telemetry summary, structured telemetry, anomaly scan, and RAG context (Qdrant)."""
        from telemetry_retriever import get_global_telemetry_retriever
        telemetry_retriever = get_global_telemetry_retriever()

        gathered: Dict[str, Any] = {
            "question": user_question,
            "telemetry_summary": {},
            "structured_telemetry": {},
            "anomaly_analysis": {},
            "available_parameters": [],
            "recent_events": [],
            "attitude_preview": [],
            "battery_preview": [],
            "rc_preview": [],
            "rag_context": []
        }

        # Telemetry components (best-effort, resilient)
        try:
            gathered["telemetry_summary"] = telemetry_retriever.get_telemetry_summary(self.session_id)
            if isinstance(gathered["telemetry_summary"], dict):
                ap = gathered["telemetry_summary"].get("available_parameters")
                if isinstance(ap, list):
                    gathered["available_parameters"] = ap
        except Exception:
            pass
        try:
            gathered["structured_telemetry"] = telemetry_retriever.get_structured_telemetry_data(self.session_id)
        except Exception:
            pass
        try:
            gathered["anomaly_analysis"] = telemetry_retriever.analyze_flight_anomalies(self.session_id, user_question)
        except Exception:
            pass

        # Direct flight_data peeks for previews (avoid large payloads)
        try:
            flight_data = telemetry_retriever.get_flight_data(self.session_id) or {}
            # Recent events (up to 5, newest last)
            ev = flight_data.get("events")
            if isinstance(ev, list) and ev:
                last5 = [e for e in ev[-5:] if isinstance(e, dict)]
                gathered["recent_events"] = last5
            # Attitude preview (first 5 points)
            att = flight_data.get("attitude_series")
            if isinstance(att, list) and att:
                gathered["attitude_preview"] = att[:5]
            # Battery preview from battery_series or events
            bser = flight_data.get("battery_series")
            if isinstance(bser, list) and bser:
                gathered["battery_preview"] = bser[:5]
            else:
                bp = []
                if isinstance(ev, list):
                    for e in ev:
                        if isinstance(e, dict) and ("battery_voltage" in e or "temperature" in e):
                            bp.append({
                                "timestamp": e.get("timestamp"),
                                "voltage": e.get("battery_voltage"),
                                "temperature": e.get("temperature")
                            })
                gathered["battery_preview"] = bp[:5]
            # RC preview
            rc = flight_data.get("rc_inputs")
            if isinstance(rc, list) and rc:
                gathered["rc_preview"] = rc[:5]
        except Exception:
            pass

        # RAG search (Qdrant), expanded with heuristic keywords
        try:
            base_docs = self.retrieve_documents(user_question, top_k=5) or []
        except Exception:
            base_docs = []
        extra_docs: List[str] = []
        try:
            # Derive a few keywords from question and available params
            terms = []
            uq = user_question.lower()
            for t in ["gps", "battery", "rc", "attitude", "altitude", "mode", "temperature", "voltage", "accuracy", "hdop", "vdop"]:
                if t in uq:
                    terms.append(t)
            for t in gathered.get("available_parameters", [])[:5]:
                if isinstance(t, str):
                    terms.append(t)
            terms = list(dict.fromkeys(terms))[:5]
            for term in terms:
                try:
                    docs = self.retrieve_documents(f"{user_question}\nFocus: {term}", top_k=2) or []
                    extra_docs.extend(docs)
                except Exception:
                    continue
        except Exception:
            pass
        # Deduplicate documents while preserving order
        try:
            seen = set()
            merged = []
            for d in base_docs + extra_docs:
                key = d if isinstance(d, str) else str(d)
                if key not in seen:
                    seen.add(key)
                    merged.append(d)
            gathered["rag_context"] = merged[:8]
        except Exception:
            gathered["rag_context"] = base_docs

        return gathered

    def _layer2_analyze(self, user_question: str, gathered: dict) -> dict:
        """Correlate signals; consult ArduPilot docs to inform decisions/interpretation."""
        analysis: Dict[str, Any] = {
            "key_findings": [],
            "correlations": [],
            "doc_notes": "",
            "takeaways": []
        }

        # Use anomaly indicators as primary signals if available
        aa = gathered.get("anomaly_analysis") or {}
        indicators = aa.get("anomaly_indicators") or []
        for ind in indicators[:10]:
            analysis["key_findings"].append({
                "type": ind.get("type"),
                "severity": ind.get("severity"),
                "timestamp": ind.get("timestamp"),
                "description": ind.get("description")
            })

        # Simple correlations from structured telemetry stats
        st = gathered.get("structured_telemetry") or {}
        kp = st.get("key_parameters") or {}
        candidate_pairs = [
            ("gps_alt", "battery_voltage"),
            ("rc_signal_strength", "gps_alt"),
            ("gps_accuracy", "rc_signal_strength")
        ]
        for a, b in candidate_pairs:
            if a in kp and b in kp:
                ta = kp[a].get("trend", "unknown")
                tb = kp[b].get("trend", "unknown")
                if ta in ("increasing", "decreasing") and ta == tb:
                    analysis["correlations"].append({
                        "pair": [a, b],
                        "note": f"{a} and {b} trend {ta} together"
                    })

        # Consult ArduPilot docs in this layer for terminology/units/threshold hints
        try:
            from ardupilot_docs import get_global_docs_retriever
            docs = get_global_docs_retriever()
            # Heuristic: extract potential terms from question
            terms = [t for t in ["GPS", "BAT", "ATT", "MODE", "ERR", "RCIN", "RSSI", "HDop", "VDop", "HAcc", "VAcc"] if t.lower() in user_question.lower()]
            if not terms and analysis["key_findings"]:
                # try infer from findings
                for f in analysis["key_findings"]:
                    t = f.get("type", "")
                    if isinstance(t, str) and t:
                        terms.append(t.upper())
            terms = list(dict.fromkeys(terms))[:3]
            doc_snips: List[str] = []
            for term in terms:
                doc = docs.get_parameter_documentation(term)
                if doc and isinstance(doc, dict):
                    desc = doc.get("description", "")
                    fields = ", ".join(list((doc.get("fields") or {}).keys())[:6])
                    doc_snips.append(f"{term}: {desc}. Fields: {fields}")
            if doc_snips:
                analysis["doc_notes"] = " | ".join(doc_snips)
        except Exception:
            pass

        # Takeaway
        if indicators:
            analysis["takeaways"].append("Detected anomaly indicators; review highlighted ones.")
        else:
            analysis["takeaways"].append("No clear anomalies in available data.")

        return analysis

    def _layer3_compose(self, user_question: str, gathered: dict, analysis: dict) -> str:
        """Compose final answer via LLM using compacted context and analysis."""
        ctx_lines: List[str] = []
        ts = gathered.get("telemetry_summary") or {}
        if isinstance(ts, dict):
            ds = ts.get("data_sources") or []
            if ds:
                ctx_lines.append("Data sources: " + ", ".join(d.get("type", "?") for d in ds))
        st = gathered.get("structured_telemetry") or {}
        if isinstance(st, dict) and "flight_overview" in st:
            ov = st["flight_overview"]
            ctx_lines.append(f"Flight overview: ~{ov.get('duration_seconds', 0):.0f}s, points={ov.get('total_data_points', 0)}")
        aa = gathered.get("anomaly_analysis") or {}
        tsum = aa.get("telemetry_summary") or {}
        if tsum:
            ctx_lines.append(f"Anomaly scan: indicators={tsum.get('anomaly_indicators_count',0)}, phases={tsum.get('flight_phases_count',0)}")
        if gathered.get("rag_context"):
            ctx_lines.append(f"RAG matches: {min(len(gathered['rag_context']), 5)}")
        if analysis.get("doc_notes"):
            ctx_lines.append("Docs consulted: " + analysis["doc_notes"])

        findings = analysis.get("key_findings") or []
        correlations = analysis.get("correlations") or []

        prompt = (
            "You are an expert UAV flight data analyst.\n\n"
            f"USER QUESTION:\n{user_question}\n\n"
            "GATHERED CONTEXT:\n" + ("\n".join(f"- {l}" for l in ctx_lines) or "- none") + "\n\n"
            "KEY FINDINGS:\n" + ("\n".join(f"- {f.get('type','?')}: {f.get('description','')}" for f in findings[:5]) or "- none") + "\n\n"
            "CORRELATIONS:\n" + ("\n".join(f"- {c['pair'][0]} vs {c['pair'][1]}: {c['note']}" for c in correlations[:3]) or "- none") + "\n\n"
            "TASK:\n"
            "Provide a concise answer:\n"
            "- Start with one-sentence takeaway.\n"
            "- Add up to 3 short bullets in plain language.\n"
            "- Include one clear next step.\n"
        )

        return self.generate(prompt)
    
    def generate_with_rag(self, prompt: str, top_k: int = 3, **kwargs) -> Dict[str, Any]:
        """Generate response with explicit RAG retrieval"""
        try:
            if not prompt or not isinstance(prompt, str):
                raise ValueError("Prompt must be a non-empty string.")
            
            # Retrieve relevant documents
            retrieved = self.rag.retrieve(prompt, top_k=top_k)
            
            # Create initial state with RAG context
            initial_state = {
                "messages": [HumanMessage(content=prompt)],
                "session_id": self.session_id,
                "rag_context": retrieved,
                "current_tool": None,
                "tool_result": None
            }
            
            # Run the agent
            config = {"configurable": {"thread_id": self.session_id}}
            result = self.agent.invoke(initial_state, config=config)
            
            # Extract the final response
            messages = result["messages"]
            response_text = "No response generated."
            if messages:
                last_message = messages[-1]
                if hasattr(last_message, 'content'):
                    response_text = last_message.content
            
            return {
                "response": response_text,
                "context_used": retrieved,
                "context_count": len(retrieved),
                "session_id": self.session_id
            }
            
        except Exception as e:
            return {
                "response": f"Error during generation: {str(e)}",
                "context_used": [],
                "context_count": 0,
                "session_id": self.session_id
            }
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session"""
        rag_status = self.rag.get_status()
        return {
            "session_id": self.session_id,
            "model_name": self.model_name,
            "system_prompt": self.system_prompt,
            "rag_status": rag_status,
            "tools_available": [tool.name for tool in self.tools]
        }
    
    def update_system_prompt(self, prompt_name: str = "ardupilot_analyst") -> str:
        """Update the system prompt using a predefined prompt from prompts.py"""
        try:
            new_prompt = get_prompt(prompt_name)
            self.system_prompt = new_prompt
            return f"System prompt updated to: {prompt_name}"
        except KeyError as e:
            return f"Error: {str(e)}"

# Backward compatibility wrapper
class GenAIWrapper(LangGraphReactAgent):
    """Backward compatibility wrapper for the original GenAIWrapper interface"""
    
    def __init__(self, system_prompt=None, enable_rag=True, session_id=None):
        super().__init__(system_prompt=system_prompt, session_id=session_id)
        self.enable_rag = enable_rag
        self.rag_status = "enabled" if enable_rag else "disabled"
        self.document_count = 0
        self.session_documents = []
    
    def add_rag_documents(self, texts):
        """Add documents to the RAG engine for retrieval (session-based)."""
        if self.enable_rag:
            if isinstance(texts, str):
                texts = [texts]
            
            result = self.rag.add_documents(texts)
            self.document_count = self.rag.document_count
            self.session_documents = self.rag.session_documents.copy()
            return result
        else:
            return "RAG is disabled. Cannot add documents."
    
    def clear_rag_documents(self):
        """Clear all documents from the RAG engine (session-based)."""
        if self.enable_rag:
            result = self.rag.clear_documents()
            self.document_count = 0
            self.session_documents = []
            return result
        else:
            return "RAG is disabled. No documents to clear."
    
    def get_rag_status(self):
        """Get the current status of the RAG engine (session-based)."""
        if self.enable_rag:
            status = self.rag.get_status()
            return {
                "status": "enabled",
                "session_id": self.session_id,
                "document_count": status["document_count"],
                "session_documents": status["session_documents"],
                "has_documents": status["has_documents"],
                "engine_ready": status["engine_ready"]
            }
        else:
            return {
                "status": "disabled",
                "session_id": self.session_id,
                "document_count": 0,
                "session_documents": 0,
                "has_documents": False,
                "engine_ready": False
            }
    
    def retrieve_documents(self, query, top_k=3):
        """Retrieve relevant documents from the RAG engine (session-based)."""
        if self.enable_rag:
            return self.rag.retrieve(query, top_k=top_k)
        else:
            return []
    
    def get_session_documents(self):
        """Get all documents in the current session."""
        return self.session_documents.copy()
    
    def get_session_info(self):
        """Get information about the current session."""
        return {
            "session_id": self.session_id,
            "document_count": self.document_count,
            "session_documents": len(self.session_documents),
            "rag_enabled": self.enable_rag,
            # Use consolidated status instead of internal engine references
            "engine_ready": bool(self.rag.get_status().get("engine_ready", False)) if self.rag else False
        }