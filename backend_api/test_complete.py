#!/usr/bin/env python3
"""
test_complete.py - Complete test suite for UAV Log Viewer Backend API

This script combines all testing functionality into a single comprehensive test suite:
- API endpoint testing
- Session management
- RAG functionality
- AI integration
- Anomaly detection
- Collection management
- Error handling
- Performance testing
- LangGraph agent testing
- System prompt testing

Usage:
    python test_complete.py [--verbose] [--url URL] [--skip-anomaly] [--skip-cleanup] [--skip-agent]
"""

import requests
import json
import uuid
import time
import logging
import argparse
import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CompleteBackendTester:
    """Complete test suite for the UAV Log Viewer Backend API"""
    
    def __init__(self, base_url: str = "http://localhost:8000", verbose: bool = False):
        self.base_url = base_url
        self.verbose = verbose
        self.session_id = str(uuid.uuid4())
        self.headers = {'X-Session-ID': self.session_id}
        self.test_results = []
        self.start_time = time.time()
        
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
    
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{status} {test_name}")
        if details and self.verbose:
            logger.info(f"   {details}")
        
        self.test_results.append({
            "test": test_name,
            "status": "PASSED" if passed else "FAILED",
            "details": details
        })
    
    def create_test_flight_data(self) -> Dict[str, Any]:
        """Create test flight data with various anomalies"""
        return {
            'vehicle': 'test_quadcopter',
            'trajectories': {
                'gps_trajectory': {
                    'trajectory': [
                        [37.7749, -122.4194, 100.0],  # Start
                        [37.7750, -122.4193, 105.0],  # Normal climb
                        [37.7751, -122.4192, 110.0],  # Normal climb
                        [37.7752, -122.4191, 50.0],   # Sudden drop (anomaly)
                        [37.7753, -122.4190, 55.0],   # Recovery
                        [37.7754, -122.4189, 60.0],   # Normal
                        [37.7755, -122.4188, 65.0],   # Normal
                        [37.7756, -122.4187, 70.0],   # Normal
                        [37.7757, -122.4186, 75.0],   # Normal
                        [37.7758, -122.4185, 80.0]    # Normal
                    ]
                }
            },
            'events': [
                {'timestamp': 0, 'battery_voltage': 12.6, 'temperature': 25.0},
                {'timestamp': 1, 'battery_voltage': 12.5, 'temperature': 26.0},
                {'timestamp': 2, 'battery_voltage': 12.4, 'temperature': 27.0},
                {'timestamp': 3, 'battery_voltage': 10.2, 'temperature': 28.0},  # Low voltage (anomaly)
                {'timestamp': 4, 'battery_voltage': 12.3, 'temperature': 29.0},
                {'timestamp': 5, 'battery_voltage': 12.2, 'temperature': 30.0},
                {'timestamp': 6, 'battery_voltage': 12.1, 'temperature': 31.0},
                {'timestamp': 7, 'battery_voltage': 12.0, 'temperature': 32.0},
                {'timestamp': 8, 'battery_voltage': 11.9, 'temperature': 33.0},
                {'timestamp': 9, 'battery_voltage': 11.8, 'temperature': 34.0}
            ],
            'flightModeChanges': [
                [0, 'MANUAL'],
                [1, 'AUTO'],
                [2, 'AUTO'],
                [3, 'RTL'],  # Return to launch (anomaly response)
                [4, 'AUTO'],
                [5, 'MANUAL'],
                [6, 'AUTO'],
                [7, 'AUTO'],
                [8, 'AUTO'],
                [9, 'MANUAL']
            ],
            'params': {
                'BATT_VOLT_MULT': 10.1,
                'BATT_CURR_MULT': 15.0,
                'GPS_TYPE': 1,
                'GPS_AUTO_SWITCH': 1,
                'GPS_DELAY_MS': 0
            }
        }
    
    # Core API Tests
    def test_health_endpoint(self) -> bool:
        """Test health endpoint"""
        try:
            response = requests.get(f'{self.base_url}/api/health', timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Health Endpoint", True, f"Status: {data.get('status', 'unknown')}")
                return True
            else:
                self.log_test("Health Endpoint", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Health Endpoint", False, f"Error: {str(e)}")
            return False
    
    def test_prompts_endpoint(self) -> bool:
        """Test prompts endpoint"""
        try:
            response = requests.get(f'{self.base_url}/api/prompts', timeout=10)
            if response.status_code == 200:
                data = response.json()
                prompts = data.get('available_prompts', [])
                self.log_test("Prompts Endpoint", True, f"Available prompts: {prompts}")
                return True
            else:
                self.log_test("Prompts Endpoint", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Prompts Endpoint", False, f"Error: {str(e)}")
            return False
    
    def test_session_creation(self) -> bool:
        """Test session creation"""
        try:
            response = requests.post(f'{self.base_url}/api/chat', 
                                    json={'message': 'Hello, I want to analyze flight data'},
                                    headers=self.headers,
                                    timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Session Creation", True, f"Session ID: {self.session_id}")
                return True
            else:
                self.log_test("Session Creation", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Session Creation", False, f"Error: {str(e)}")
            return False
    
    def test_session_info_retrieval(self) -> bool:
        """Test session info retrieval"""
        try:
            response = requests.get(f'{self.base_url}/api/session/{self.session_id}', timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Session Info Retrieval", True, f"Message count: {data.get('message_count', 0)}")
                return True
            else:
                self.log_test("Session Info Retrieval", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Session Info Retrieval", False, f"Error: {str(e)}")
            return False
    
    def test_flight_data_storage(self) -> bool:
        """Test flight data storage"""
        try:
            flight_data = self.create_test_flight_data()
            response = requests.post(f'{self.base_url}/api/flight-data', 
                                    json=flight_data,
                                    headers=self.headers,
                                    timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                rag_status = data.get('rag_status', 'N/A')
                self.log_test("Flight Data Storage", True, f"RAG Status: {rag_status}")
                return True
            else:
                self.log_test("Flight Data Storage", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Flight Data Storage", False, f"Error: {str(e)}")
            return False
    
    # RAG System Tests
    def test_rag_stats(self) -> bool:
        """Test RAG stats endpoint"""
        try:
            response = requests.get(f'{self.base_url}/api/rag/stats', timeout=10)
            if response.status_code == 200:
                data = response.json()
                collections = data.get('total_collections', 0)
                self.log_test("RAG Stats", True, f"Collections: {collections}")
                return True
            else:
                self.log_test("RAG Stats", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("RAG Stats", False, f"Error: {str(e)}")
            return False
    
    def test_rag_collection_status(self) -> bool:
        """Test RAG collection status"""
        try:
            response = requests.get(f'{self.base_url}/api/rag/collections/{self.session_id}', timeout=10)
            if response.status_code == 200:
                data = response.json()
                docs = data.get('document_count', 0)
                self.log_test("RAG Collection Status", True, f"Documents: {docs}")
                return True
            else:
                self.log_test("RAG Collection Status", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("RAG Collection Status", False, f"Error: {str(e)}")
            return False
    
    def test_rag_collections_list(self) -> bool:
        """Test RAG collections list"""
        try:
            response = requests.get(f'{self.base_url}/api/rag/collections', timeout=10)
            if response.status_code == 200:
                data = response.json()
                total = data.get('total_collections', 0)
                self.log_test("List RAG Collections", True, f"Total: {total}")
                return True
            else:
                self.log_test("List RAG Collections", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("List RAG Collections", False, f"Error: {str(e)}")
            return False
    
    def test_rag_collection_clear(self) -> bool:
        """Test RAG collection clear"""
        try:
            response = requests.post(f'{self.base_url}/api/rag/collections/{self.session_id}/clear', timeout=10)
            if response.status_code == 200:
                data = response.json()
                success = data.get('success', False)
                self.log_test("Clear RAG Collection", True, f"Success: {success}")
                return True
            else:
                self.log_test("Clear RAG Collection", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Clear RAG Collection", False, f"Error: {str(e)}")
            return False
    
    # AI Integration Tests
    def test_ai_chat_with_context(self) -> bool:
        """Test AI chat with context"""
        try:
            response = requests.post(f'{self.base_url}/api/chat', 
                                    json={'message': 'What can you tell me about this flight data?'},
                                    headers=self.headers,
                                    timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                message_length = len(data.get('message', ''))
                self.log_test("AI Chat with Context", True, f"Response length: {message_length}")
                return True
            else:
                self.log_test("AI Chat with Context", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("AI Chat with Context", False, f"Error: {str(e)}")
            return False
    
    def test_ai_follow_up_chat(self) -> bool:
        """Test AI follow-up chat"""
        try:
            response = requests.post(f'{self.base_url}/api/chat', 
                                    json={'message': 'Can you provide more details?'},
                                    headers=self.headers,
                                    timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("AI Follow-up Chat", True, "Response received")
                return True
            else:
                self.log_test("AI Follow-up Chat", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("AI Follow-up Chat", False, f"Error: {str(e)}")
            return False
    
    def test_internet_search_capability(self) -> bool:
        """Test internet search capability"""
        try:
            response = requests.post(f'{self.base_url}/api/chat', 
                                    json={'message': 'Search for information about ArduPilot flight modes'},
                                    headers=self.headers,
                                    timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                message_length = len(data.get('message', ''))
                self.log_test("Internet Search Capability", True, f"Response length: {message_length}")
                return True
            else:
                self.log_test("Internet Search Capability", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Internet Search Capability", False, f"Error: {str(e)}")
            return False
    
    # System Prompt Tests
    def test_system_prompt_switching(self) -> bool:
        """Test system prompt switching"""
        try:
            response = requests.post(f'{self.base_url}/api/prompt/{self.session_id}', 
                                    json={'prompt_name': 'flight_data_expert'},
                                    timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                prompt_name = data.get('prompt_name', 'unknown')
                self.log_test("System Prompt Switching", True, f"Prompt: {prompt_name}")
                return True
            else:
                self.log_test("System Prompt Switching", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("System Prompt Switching", False, f"Error: {str(e)}")
            return False
    
    def test_chat_with_new_prompt(self) -> bool:
        """Test chat with new prompt"""
        try:
            response = requests.post(f'{self.base_url}/api/chat', 
                                    json={'message': 'How would you analyze this flight?'},
                                    headers=self.headers,
                                    timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Chat with New Prompt", True, "Response received")
                return True
            else:
                self.log_test("Chat with New Prompt", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Chat with New Prompt", False, f"Error: {str(e)}")
            return False
    
    # Anomaly Detection Tests
    def test_anomaly_analysis_api(self) -> bool:
        """Test anomaly analysis API endpoint"""
        try:
            response = requests.post(f'{self.base_url}/api/anomaly/{self.session_id}/analyze', 
                                    json={'question': 'Are there any anomalies in this flight?'},
                                    timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'error' not in data:
                    summary = data.get('telemetry_summary', {})
                    duration = summary.get('flight_duration', 0)
                    indicators = summary.get('anomaly_indicators_count', 0)
                    self.log_test("Anomaly Analysis API", True, f"Duration: {duration:.1f}s, Indicators: {indicators}")
                    return True
                else:
                    self.log_test("Anomaly Analysis API", False, f"Error: {data['error']}")
                    return False
            else:
                self.log_test("Anomaly Analysis API", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Anomaly Analysis API", False, f"Error: {str(e)}")
            return False
    
    def test_structured_data_api(self) -> bool:
        """Test structured data API endpoint"""
        try:
            response = requests.get(f'{self.base_url}/api/anomaly/{self.session_id}/structured-data', timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'error' not in data:
                    overview = data.get('flight_overview', {})
                    params = len(overview.get('parameters_available', []))
                    self.log_test("Structured Data API", True, f"Parameters: {params}")
                    return True
                else:
                    self.log_test("Structured Data API", False, f"Error: {data['error']}")
                    return False
            else:
                self.log_test("Structured Data API", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Structured Data API", False, f"Error: {str(e)}")
            return False
    
    def test_agentic_anomaly_detection(self) -> bool:
        """Test agentic anomaly detection through chat"""
        try:
            response = requests.post(f'{self.base_url}/api/chat', 
                                    json={'message': 'Are there any anomalies in this flight?'},
                                    headers=self.headers,
                                    timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                message_length = len(data.get('message', ''))
                self.log_test("Agentic Anomaly Detection", True, f"Response length: {message_length}")
                return True
            else:
                self.log_test("Agentic Anomaly Detection", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Agentic Anomaly Detection", False, f"Error: {str(e)}")
            return False
    
    def test_specific_anomaly_questions(self) -> bool:
        """Test specific anomaly-related questions"""
        questions = [
            "Can you spot any issues in the GPS data?",
            "What about the battery voltage?",
            "Are there any sudden changes in altitude?"
        ]
        
        passed = 0
        total = len(questions)
        
        for question in questions:
            try:
                response = requests.post(f'{self.base_url}/api/chat', 
                                        json={'message': question},
                                        headers=self.headers,
                                        timeout=30)
                
                if response.status_code == 200:
                    passed += 1
                else:
                    logger.error(f"Question '{question[:30]}...' failed with status {response.status_code}")
            except Exception as e:
                logger.error(f"Question '{question[:30]}...' failed with error: {e}")
        
        success_rate = (passed / total) * 100
        self.log_test("Specific Anomaly Questions", passed == total, f"{passed}/{total} passed ({success_rate:.1f}%)")
        return passed == total
    
    def test_telemetry_summary(self) -> bool:
        """Test telemetry summary endpoint"""
        try:
            response = requests.get(f'{self.base_url}/api/telemetry/{self.session_id}/summary', timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'error' not in data:
                    sources = len(data.get('data_sources', []))
                    self.log_test("Telemetry Summary", True, f"Data sources: {sources}")
                    return True
                else:
                    self.log_test("Telemetry Summary", False, f"Error: {data['error']}")
                    return False
            else:
                self.log_test("Telemetry Summary", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Telemetry Summary", False, f"Error: {str(e)}")
            return False
    
    # LangGraph Agent Tests
    def test_langgraph_agent_direct(self) -> bool:
        """Test LangGraph agent directly"""
        try:
            from llm_config import LangGraphReactAgent
            
            # Check if API key is available
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                self.log_test("LangGraph Agent Direct", False, "GOOGLE_API_KEY not found")
                return False
            
            # Initialize the agent
            agent = LangGraphReactAgent(
                system_prompt="You are a helpful AI assistant for UAV log analysis.",
                session_id="test_direct_agent"
            )
            
            # Test generation
            response = agent.generate("Hello, can you help me analyze flight data?")
            
            if response and len(response) > 0:
                self.log_test("LangGraph Agent Direct", True, f"Response length: {len(response)}")
                return True
            else:
                self.log_test("LangGraph Agent Direct", False, "No response generated")
                return False
                
        except Exception as e:
            self.log_test("LangGraph Agent Direct", False, f"Error: {str(e)}")
            return False
    
    # Error Handling and Performance Tests
    def test_error_handling(self) -> bool:
        """Test error handling"""
        try:
            response = requests.get(f'{self.base_url}/api/session/invalid-session-id', timeout=10)
            if response.status_code == 404:
                self.log_test("Error Handling", True, "Invalid session handled correctly")
                return True
            else:
                self.log_test("Error Handling", False, f"Expected 404, got {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Error Handling", False, f"Error: {str(e)}")
            return False
    
    def test_performance(self) -> bool:
        """Test performance"""
        try:
            start_time = time.time()
            response = requests.get(f'{self.base_url}/api/health', timeout=10)
            end_time = time.time()
            
            if response.status_code == 200:
                response_time = end_time - start_time
                self.log_test("Performance", True, f"Response time: {response_time:.2f}s")
                return True
            else:
                self.log_test("Performance", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Performance", False, f"Error: {str(e)}")
            return False
    
    def run_all_tests(self, skip_anomaly: bool = False, skip_cleanup: bool = False, skip_agent: bool = False) -> Dict[str, Any]:
        """Run all tests"""
        logger.info("🚀 Starting Complete Backend Test Suite")
        logger.info("=" * 60)
        logger.info(f"Session ID: {self.session_id}")
        logger.info(f"Base URL: {self.base_url}")
        
        # Core API tests
        core_tests = [
            ("Health Endpoint", self.test_health_endpoint),
            ("Prompts Endpoint", self.test_prompts_endpoint),
            ("Session Creation", self.test_session_creation),
            ("Session Info Retrieval", self.test_session_info_retrieval),
            ("Flight Data Storage", self.test_flight_data_storage),
        ]
        
        # RAG system tests
        rag_tests = [
            ("RAG Stats", self.test_rag_stats),
            ("RAG Collection Status", self.test_rag_collection_status),
            ("List RAG Collections", self.test_rag_collections_list),
        ]
        
        # AI integration tests
        ai_tests = [
            ("AI Chat with Context", self.test_ai_chat_with_context),
            ("AI Follow-up Chat", self.test_ai_follow_up_chat),
            ("Internet Search Capability", self.test_internet_search_capability),
        ]
        
        # System prompt tests
        prompt_tests = [
            ("System Prompt Switching", self.test_system_prompt_switching),
            ("Chat with New Prompt", self.test_chat_with_new_prompt),
        ]
        
        # Anomaly detection tests
        anomaly_tests = [
            ("Anomaly Analysis API", self.test_anomaly_analysis_api),
            ("Structured Data API", self.test_structured_data_api),
            ("Agentic Anomaly Detection", self.test_agentic_anomaly_detection),
            ("Specific Anomaly Questions", self.test_specific_anomaly_questions),
            ("Telemetry Summary", self.test_telemetry_summary),
        ]
        
        # LangGraph agent tests
        agent_tests = [
            ("LangGraph Agent Direct", self.test_langgraph_agent_direct),
        ]
        
        # Cleanup tests
        cleanup_tests = [
            ("Clear RAG Collection", self.test_rag_collection_clear),
        ]
        
        # Error handling and performance tests
        system_tests = [
            ("Error Handling", self.test_error_handling),
            ("Performance", self.test_performance),
        ]
        
        # Combine all tests
        all_tests = core_tests + rag_tests + ai_tests + prompt_tests + system_tests
        
        if not skip_anomaly:
            all_tests.extend(anomaly_tests)
        
        if not skip_agent:
            all_tests.extend(agent_tests)
        
        if not skip_cleanup:
            all_tests.extend(cleanup_tests)
        
        passed = 0
        total = len(all_tests)
        
        for test_name, test_func in all_tests:
            logger.info(f"\nTesting {test_name}...")
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                logger.error(f"❌ {test_name}: FAILED - {e}")
                self.test_results.append({"test": test_name, "status": "FAILED", "details": str(e)})
        
        # Summary
        end_time = time.time()
        total_time = end_time - self.start_time
        
        logger.info("\n" + "=" * 60)
        logger.info("📊 COMPLETE TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {total}")
        logger.info(f"Passed: {passed} ✅")
        logger.info(f"Failed: {total - passed} ❌")
        logger.info(f"Success Rate: {(passed / total) * 100:.1f}%")
        logger.info(f"Total Time: {total_time:.2f}s")
        
        return {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": (passed / total) * 100,
            "total_time": total_time,
            "results": self.test_results
        }

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Complete test suite for UAV Log Viewer Backend")
    parser.add_argument('--url', default='http://localhost:8000', help='Backend URL')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--skip-anomaly', action='store_true', help='Skip anomaly detection tests')
    parser.add_argument('--skip-cleanup', action='store_true', help='Skip cleanup tests')
    parser.add_argument('--skip-agent', action='store_true', help='Skip LangGraph agent tests')
    
    args = parser.parse_args()
    
    tester = CompleteBackendTester(args.url, args.verbose)
    results = tester.run_all_tests(args.skip_anomaly, args.skip_cleanup, args.skip_agent)
    
    if results['success_rate'] == 100:
        logger.info("\n🎉 All tests passed!")
        exit(0)
    else:
        logger.error(f"\n⚠️ {results['failed']} tests failed!")
        exit(1)

if __name__ == "__main__":
    main()
