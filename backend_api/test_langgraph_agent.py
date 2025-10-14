#!/usr/bin/env python3
"""
Test script for the LangGraph React Agent with Gemini API and Session-based RAG
"""

import os
from dotenv import load_dotenv
from llm_config import LangGraphReactAgent, GenAIWrapper

def test_langgraph_agent():
    """Test the LangGraph React Agent implementation"""
    
    # Load environment variables
    load_dotenv()
    
    # Check if API key is available
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY not found in environment variables.")
        print("Please set your Google API key in the .env file.")
        return
    
    print("🚀 Testing LangGraph React Agent with Gemini API")
    print("=" * 50)
    
    try:
        # Initialize the agent
        agent = LangGraphReactAgent(
            system_prompt="You are a helpful AI assistant for UAV log analysis.",
            session_id="test_session_001"
        )
        
        print("✅ Agent initialized successfully")
        print(f"📋 Session ID: {agent.session_id}")
        print(f"🤖 Model: {agent.model_name}")
        
        # Test RAG functionality
        print("\n📚 Testing RAG functionality...")
        
        # Add some sample documents
        sample_docs = [
            "UAV flight logs contain telemetry data including GPS coordinates, altitude, and battery levels.",
            "MAVLink is a communication protocol used for UAV systems to exchange data between components.",
            "Flight modes in ArduPilot include STABILIZE, LOITER, AUTO, and RTL (Return to Launch)."
        ]
        
        result = agent.add_rag_documents(sample_docs)
        print(f"✅ {result}")
        
        # Check RAG status
        status = agent.get_rag_status()
        print(f"📊 RAG Status: {status}")
        
        # Test document retrieval
        print("\n🔍 Testing document retrieval...")
        retrieved = agent.retrieve_documents("flight modes", top_k=2)
        print(f"📄 Retrieved documents: {len(retrieved)}")
        for i, doc in enumerate(retrieved, 1):
            print(f"  {i}. {doc[:100]}...")
        
        # Test agent generation
        print("\n💬 Testing agent generation...")
        response = agent.generate("What are the different flight modes in UAV systems?")
        print(f"🤖 Agent Response: {response}")
        
        # Test generation with RAG
        print("\n🔗 Testing generation with RAG...")
        rag_response = agent.generate_with_rag("Explain MAVLink protocol", top_k=2)
        print(f"🤖 RAG-Enhanced Response: {rag_response['response']}")
        print(f"📚 Context used: {rag_response['context_count']} documents")
        
        # Test session info
        print("\n📋 Session Information:")
        session_info = agent.get_session_info()
        for key, value in session_info.items():
            print(f"  {key}: {value}")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

def test_backward_compatibility():
    """Test backward compatibility with the original GenAIWrapper interface"""
    
    print("\n🔄 Testing Backward Compatibility")
    print("=" * 50)
    
    try:
        # Initialize using the old interface
        wrapper = GenAIWrapper(
            system_prompt="You are a helpful assistant.",
            enable_rag=True,
            session_id="compat_test_001"
        )
        
        print("✅ GenAIWrapper initialized successfully")
        
        # Test old interface methods
        result = wrapper.add_rag_documents(["Test document for compatibility"])
        print(f"✅ {result}")
        
        status = wrapper.get_rag_status()
        print(f"📊 Status: {status}")
        
        response = wrapper.generate("Hello, how are you?")
        print(f"🤖 Response: {response}")
        
        print("✅ Backward compatibility test passed!")
        
    except Exception as e:
        print(f"❌ Backward compatibility test failed: {str(e)}")

if __name__ == "__main__":
    print("🧪 LangGraph React Agent Test Suite")
    print("=" * 60)
    
    # Test the new implementation
    test_langgraph_agent()
    
    # Test backward compatibility
    test_backward_compatibility()
    
    print("\n🎉 Test suite completed!")
