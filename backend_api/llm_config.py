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
from in_memory_rag import BM25RAG
from prompts import get_prompt, ARDUPILOT_DATA_ANALYST_PROMPT

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
    """Session-based RAG implementation"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.rag_engine = BM25RAG()
        self.session_documents = []
        self.document_count = 0
    
    def add_documents(self, texts: List[str]) -> str:
        """Add documents to the session-based RAG engine"""
        if isinstance(texts, str):
            texts = [texts]
        
        self.session_documents.extend(texts)
        self.rag_engine.add_documents(texts)
        self.document_count += len(texts)
        
        return f"Added {len(texts)} document(s) to session {self.session_id}. Total documents: {self.document_count}"
    
    def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        """Retrieve relevant documents from the session-based RAG engine"""
        return self.rag_engine.retrieve(query, top_k=top_k)
    
    def clear_documents(self) -> str:
        """Clear all documents from the session-based RAG engine"""
        self.rag_engine.documents = []
        self.rag_engine.tokenized_docs = []
        self.rag_engine.bm25 = None
        self.session_documents = []
        self.document_count = 0
        return f"RAG documents cleared for session {self.session_id}."
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the session-based RAG engine"""
        return {
            "session_id": self.session_id,
            "document_count": self.document_count,
            "session_documents": len(self.session_documents),
            "has_documents": self.document_count > 0,
            "engine_ready": self.rag_engine.bm25 is not None
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
            self._create_rag_status_tool()
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
            
            # Get response from model
            response = self.llm.bind_tools(self.tools).invoke(messages)
            
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
        """Generate response using the LangGraph React agent"""
        try:
            if not prompt or not isinstance(prompt, str):
                raise ValueError("Prompt must be a non-empty string.")
            
            # Create initial state
            initial_state = {
                "messages": [HumanMessage(content=prompt)],
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
                    return last_message.content
                else:
                    return str(last_message)
            
            return "No response generated."
            
        except Exception as e:
            return f"Error during generation: {str(e)}"
    
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
            "engine_ready": self.rag.rag_engine.bm25 is not None if self.rag else False
        }