#!/usr/bin/env python3
"""
test_enhanced_telemetry.py - Test script for enhanced telemetry capabilities

This script tests the new GPS, battery, and RC signal detection capabilities
that have been added to the system.
"""

import requests
import json
import uuid
import time

API_BASE_URL = "http://localhost:8000"

def create_enhanced_test_flight_data():
    """Create comprehensive test flight data with GPS metadata, battery, and RC data"""
    return {
        'vehicle': 'test_quadcopter',
        'trajectories': {
            'GPS': {
                'trajectory': [
                    [37.7749, -122.4194, 100.0, 0],      # Start
                    [37.7750, -122.4193, 105.0, 1000],   # Normal climb
                    [37.7751, -122.4192, 110.0, 2000],   # Normal climb
                    [37.7752, -122.4191, 50.0, 3000],    # Sudden drop (anomaly)
                    [37.7753, -122.4190, 55.0, 4000],    # Recovery
                    [37.7754, -122.4189, 60.0, 5000],    # Normal
                    [37.7755, -122.4188, 65.0, 6000],    # Normal
                    [37.7756, -122.4187, 70.0, 7000],    # Normal
                    [37.7757, -122.4186, 75.0, 8000],    # Normal
                    [37.7758, -122.4185, 80.0, 9000]     # Normal
                ]
            }
        },
        'gps_metadata': {
            'status_changes': [
                {'timestamp': 0, 'status': 'GPS_OK_FIX_3D', 'fix_type': '3D'},
                {'timestamp': 1000, 'status': 'GPS_OK_FIX_3D', 'fix_type': '3D'},
                {'timestamp': 2000, 'status': 'GPS_OK_FIX_3D', 'fix_type': '3D'},
                {'timestamp': 3000, 'status': 'NO_FIX', 'fix_type': 'No Fix'},  # GPS signal loss
                {'timestamp': 4000, 'status': 'GPS_OK_FIX_2D', 'fix_type': '2D'},  # Partial recovery
                {'timestamp': 5000, 'status': 'GPS_OK_FIX_3D', 'fix_type': '3D'},  # Full recovery
                {'timestamp': 6000, 'status': 'GPS_OK_FIX_3D', 'fix_type': '3D'},
                {'timestamp': 7000, 'status': 'GPS_OK_FIX_3D', 'fix_type': '3D'},
                {'timestamp': 8000, 'status': 'GPS_OK_FIX_3D', 'fix_type': '3D'},
                {'timestamp': 9000, 'status': 'GPS_OK_FIX_3D', 'fix_type': '3D'}
            ],
            'satellite_counts': [8, 9, 8, 2, 4, 7, 8, 9, 8, 7],  # Low satellites at timestamp 3000
            'signal_quality': [
                {'timestamp': 0, 'hdop': 1.2, 'vdop': 1.5},
                {'timestamp': 1000, 'hdop': 1.1, 'vdop': 1.4},
                {'timestamp': 2000, 'hdop': 1.3, 'vdop': 1.6},
                {'timestamp': 3000, 'hdop': 5.2, 'vdop': 6.1},  # Poor signal quality
                {'timestamp': 4000, 'hdop': 2.8, 'vdop': 3.2},  # Improving
                {'timestamp': 5000, 'hdop': 1.4, 'vdop': 1.7},
                {'timestamp': 6000, 'hdop': 1.2, 'vdop': 1.5},
                {'timestamp': 7000, 'hdop': 1.1, 'vdop': 1.4},
                {'timestamp': 8000, 'hdop': 1.3, 'vdop': 1.6},
                {'timestamp': 9000, 'hdop': 1.2, 'vdop': 1.5}
            ],
            'accuracy_metrics': [
                {'timestamp': 0, 'hacc': 2.1, 'vacc': 3.2, 'sacc': 0.8},
                {'timestamp': 1000, 'hacc': 1.9, 'vacc': 2.8, 'sacc': 0.7},
                {'timestamp': 2000, 'hacc': 2.2, 'vacc': 3.1, 'sacc': 0.9},
                {'timestamp': 3000, 'hacc': 8.5, 'vacc': 12.3, 'sacc': 2.1},  # Poor accuracy
                {'timestamp': 4000, 'hacc': 4.2, 'vacc': 6.1, 'sacc': 1.4},  # Improving
                {'timestamp': 5000, 'hacc': 2.3, 'vacc': 3.4, 'sacc': 0.9},
                {'timestamp': 6000, 'hacc': 2.0, 'vacc': 2.9, 'sacc': 0.8},
                {'timestamp': 7000, 'hacc': 1.8, 'vacc': 2.7, 'sacc': 0.7},
                {'timestamp': 8000, 'hacc': 2.1, 'vacc': 3.0, 'sacc': 0.8},
                {'timestamp': 9000, 'hacc': 2.0, 'vacc': 2.9, 'sacc': 0.8}
            ]
        },
        'events': [
            {'timestamp': 0, 'battery_voltage': 12.6, 'temperature': 25.0},
            {'timestamp': 1000, 'battery_voltage': 12.5, 'temperature': 26.0},
            {'timestamp': 2000, 'battery_voltage': 12.4, 'temperature': 27.0},
            {'timestamp': 3000, 'battery_voltage': 10.2, 'temperature': 28.0},  # Low voltage (anomaly)
            {'timestamp': 4000, 'battery_voltage': 12.3, 'temperature': 29.0},
            {'timestamp': 5000, 'battery_voltage': 12.2, 'temperature': 30.0},
            {'timestamp': 6000, 'battery_voltage': 12.1, 'temperature': 31.0},
            {'timestamp': 7000, 'battery_voltage': 12.0, 'temperature': 32.0},
            {'timestamp': 8000, 'battery_voltage': 11.9, 'temperature': 33.0},
            {'timestamp': 9000, 'battery_voltage': 11.8, 'temperature': 34.0}
        ],
        'rc_inputs': [
            {'timestamp': 0, 'signal_strength': 85, 'signal_lost': False},
            {'timestamp': 1000, 'signal_strength': 82, 'signal_lost': False},
            {'timestamp': 2000, 'signal_strength': 80, 'signal_lost': False},
            {'timestamp': 3000, 'signal_strength': 15, 'signal_lost': True},  # RC signal loss
            {'timestamp': 4000, 'signal_strength': 45, 'signal_lost': False},  # Recovery
            {'timestamp': 5000, 'signal_strength': 78, 'signal_lost': False},
            {'timestamp': 6000, 'signal_strength': 80, 'signal_lost': False},
            {'timestamp': 7000, 'signal_strength': 83, 'signal_lost': False},
            {'timestamp': 8000, 'signal_strength': 81, 'signal_lost': False},
            {'timestamp': 9000, 'signal_strength': 79, 'signal_lost': False}
        ],
        'flightModeChanges': [
            [0, 'MANUAL'],
            [1000, 'AUTO'],
            [2000, 'AUTO'],
            [3000, 'RTL'],  # Return to launch (anomaly response)
            [4000, 'AUTO'],
            [5000, 'MANUAL'],
            [6000, 'AUTO'],
            [7000, 'AUTO'],
            [8000, 'AUTO'],
            [9000, 'MANUAL']
        ],
        'params': {
            'BATT_VOLT_MULT': 10.1,
            'BATT_CURR_MULT': 15.0,
            'GPS_TYPE': 1,
            'GPS_AUTO_SWITCH': 1,
            'GPS_DELAY_MS': 0
        }
    }

def test_enhanced_telemetry():
    """Test the enhanced telemetry capabilities"""
    session_id = str(uuid.uuid4())
    headers = {'X-Session-ID': session_id}
    
    print(f"🚀 Testing Enhanced Telemetry Capabilities")
    print(f"Session ID: {session_id}")
    print("=" * 60)
    
    # Upload enhanced flight data
    print("\n1. Uploading Enhanced Flight Data...")
    flight_data = create_enhanced_test_flight_data()
    response = requests.post(f'{API_BASE_URL}/api/flight-data', 
                            headers=headers, json=flight_data)
    
    if response.status_code == 200:
        print("✅ Flight data uploaded successfully")
        data = response.json()
        print(f"   RAG Status: {data.get('rag_status', 'N/A')}")
    else:
        print(f"❌ Failed to upload flight data: {response.status_code}")
        return
    
    # Test specific telemetry queries
    test_queries = [
        ("What is the highest altitude reached?", "altitude"),
        ("Can you detect GPS signal loss?", "gps_signal"),
        ("How many satellites were visible?", "satellites"),
        ("What was the GPS accuracy?", "gps_accuracy"),
        ("How long was the total flight time?", "flight_duration"),
        ("What was the maximum battery temperature?", "battery_temp"),
        ("When was the first RC signal loss?", "rc_signal"),
        ("What was the minimum battery voltage?", "battery_voltage")
    ]
    
    print("\n2. Testing Enhanced Telemetry Queries...")
    for query, expected_type in test_queries:
        print(f"\n   Testing: {query}")
        response = requests.post(f'{API_BASE_URL}/api/chat', 
                                headers=headers, 
                                json={'message': query})
        
        if response.status_code == 200:
            data = response.json()
            message = data.get('message', 'No response')
            print(f"   ✅ Response: {message[:100]}...")
        else:
            print(f"   ❌ Error: {response.status_code}")
    
    # Test anomaly detection
    print("\n3. Testing Enhanced Anomaly Detection...")
    response = requests.post(f'{API_BASE_URL}/api/anomaly/{session_id}/analyze',
                            json={'question': 'Are there any anomalies in this flight?'})
    
    if response.status_code == 200:
        data = response.json()
        if 'error' not in data:
            indicators = data.get('anomaly_indicators', [])
            print(f"✅ Anomaly analysis completed")
            print(f"   Total indicators: {len(indicators)}")
            
            # Show specific anomaly types
            anomaly_types = {}
            for indicator in indicators:
                anomaly_type = indicator.get('type', 'unknown')
                anomaly_types[anomaly_type] = anomaly_types.get(anomaly_type, 0) + 1
            
            print("   Anomaly types detected:")
            for anomaly_type, count in anomaly_types.items():
                print(f"     - {anomaly_type}: {count}")
        else:
            print(f"❌ Anomaly analysis error: {data['error']}")
    else:
        print(f"❌ Anomaly analysis failed: {response.status_code}")
    
    # Test structured data
    print("\n4. Testing Structured Data API...")
    response = requests.get(f'{API_BASE_URL}/api/anomaly/{session_id}/structured-data')
    
    if response.status_code == 200:
        data = response.json()
        if 'error' not in data:
            print("✅ Structured data retrieved")
            overview = data.get('flight_overview', {})
            print(f"   Flight duration: {overview.get('duration_seconds', 'N/A')}s")
            print(f"   Data points: {overview.get('total_data_points', 'N/A')}")
            print(f"   Parameters: {len(overview.get('parameters_available', []))}")
        else:
            print(f"❌ Structured data error: {data['error']}")
    else:
        print(f"❌ Structured data failed: {response.status_code}")
    
    # Test telemetry summary
    print("\n5. Testing Telemetry Summary...")
    response = requests.get(f'{API_BASE_URL}/api/telemetry/{session_id}/summary')
    
    if response.status_code == 200:
        data = response.json()
        if 'error' not in data:
            print("✅ Telemetry summary retrieved")
            sources = data.get('data_sources', [])
            print(f"   Data sources: {len(sources)}")
            for source in sources:
                print(f"     - {source.get('type', 'unknown')}: {source.get('count', 0)} points")
        else:
            print(f"❌ Telemetry summary error: {data['error']}")
    else:
        print(f"❌ Telemetry summary failed: {response.status_code}")
    
    print("\n" + "=" * 60)
    print("🎉 Enhanced Telemetry Testing Complete!")

if __name__ == "__main__":
    test_enhanced_telemetry()
