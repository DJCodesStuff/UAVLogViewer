#!/usr/bin/env python3
"""
Test script for the UAV Log Viewer Backend API
Demonstrates the API functionality with sample data
"""

import requests
import json
import time
import uuid

API_BASE_URL = "http://localhost:8000"

def test_api():
    """Test the API endpoints with sample data"""
    
    # Generate a test session ID
    session_id = f"test_session_{int(time.time())}"
    
    print(f"Testing API with session ID: {session_id}")
    print("=" * 60)
    
    # Test 1: Health Check
    print("1. Testing Health Check...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/health")
        if response.status_code == 200:
            print("✓ Health check passed")
            print(f"  Response: {response.json()}")
        else:
            print(f"✗ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Health check error: {e}")
        return
    
    print()
    
    # Test 2: Chat without flight data
    print("2. Testing Chat (no flight data)...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/chat",
            headers={
                "X-Session-ID": session_id,
                "Content-Type": "application/json"
            },
            json={
                "message": "Hello, what can you tell me about my flight?",
                "sessionId": session_id,
                "timestamp": int(time.time())
            }
        )
        if response.status_code == 200:
            print("✓ Chat without flight data works")
            print(f"  Response: {response.json()['message']}")
        else:
            print(f"✗ Chat failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Chat error: {e}")
    
    print()
    
    # Test 3: Store sample flight data
    print("3. Testing Flight Data Storage...")
    sample_flight_data = {
        "vehicle": "Copter",
        "trajectories": {
            "GPS": {
                "trajectory": [
                    [-122.4194, 37.7749, 0, 1000],
                    [-122.4195, 37.7750, 10, 2000],
                    [-122.4196, 37.7751, 20, 3000],
                    [-122.4197, 37.7752, 15, 4000],
                    [-122.4198, 37.7753, 5, 5000]
                ],
                "timeTrajectory": {
                    1000: [-122.4194, 37.7749, 0, 1000],
                    2000: [-122.4195, 37.7750, 10, 2000],
                    3000: [-122.4196, 37.7751, 20, 3000],
                    4000: [-122.4197, 37.7752, 15, 4000],
                    5000: [-122.4198, 37.7753, 5, 5000]
                }
            }
        },
        "flightModeChanges": [
            [1000, "STABILIZE"],
            [2000, "AUTO"],
            [3000, "RTL"]
        ],
        "events": [
            [1000, "ARMED"],
            [2000, "MODE_CHANGED"],
            [5000, "DISARMED"]
        ],
        "mission": [
            {"lat": 37.7749, "lon": -122.4194, "alt": 10},
            {"lat": 37.7750, "lon": -122.4195, "alt": 20}
        ],
        "params": {
            "FRAME_TYPE": 1,
            "MOT_SPIN_ARMED": 70
        },
        "metadata": {
            "startTime": "2024-01-01T12:00:00Z"
        },
        "timeAttitude": {
            1000: [0.1, 0.2, 0.3],
            2000: [0.2, 0.3, 0.4]
        },
        "fences": []
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/flight-data",
            headers={
                "X-Session-ID": session_id,
                "Content-Type": "application/json"
            },
            json=sample_flight_data
        )
        if response.status_code == 200:
            print("✓ Flight data stored successfully")
            data = response.json()
            print(f"  Available data types: {data['available_data_types']}")
            print(f"  GPS points: {data['data_summary']['gps_points']}")
            print(f"  Vehicle type: {data['data_summary']['vehicle_type']}")
        else:
            print(f"✗ Flight data storage failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Flight data storage error: {e}")
    
    print()
    
    # Test 4: Chat with flight data
    print("4. Testing Chat (with flight data)...")
    test_messages = [
        "What flight modes were used?",
        "Can you give me a summary of the flight?",
        "What GPS data is available?",
        "Tell me about the events that occurred"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"  4.{i} Testing: '{message}'")
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/chat",
                headers={
                    "X-Session-ID": session_id,
                    "Content-Type": "application/json"
                },
                json={
                    "message": message,
                    "sessionId": session_id,
                    "timestamp": int(time.time())
                }
            )
            if response.status_code == 200:
                print(f"    ✓ Response: {response.json()['message'][:100]}...")
            else:
                print(f"    ✗ Failed: {response.status_code}")
        except Exception as e:
            print(f"    ✗ Error: {e}")
        print()
    
    # Test 5: Session Information
    print("5. Testing Session Information...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/session/{session_id}")
        if response.status_code == 200:
            print("✓ Session info retrieved")
            data = response.json()
            print(f"  Message count: {data['message_count']}")
            print(f"  Has flight data: {data['has_flight_data']}")
            print(f"  Available data types: {len(data['available_data_types'])}")
        else:
            print(f"✗ Session info failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Session info error: {e}")
    
    print()
    
    # Test 6: List Sessions
    print("6. Testing Session List...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/sessions")
        if response.status_code == 200:
            print("✓ Session list retrieved")
            data = response.json()
            print(f"  Total sessions: {data['total_sessions']}")
            if data['sessions']:
                session = data['sessions'][0]
                print(f"  First session: {session['session_id'][:20]}...")
                print(f"  Has flight data: {session['has_flight_data']}")
        else:
            print(f"✗ Session list failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Session list error: {e}")
    
    print()
    print("=" * 60)
    print("API testing completed!")

if __name__ == '__main__':
    print("UAV Log Viewer Backend API Test")
    print("Make sure the API is running on http://localhost:8000")
    print()
    
    try:
        test_api()
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test failed with error: {e}")
