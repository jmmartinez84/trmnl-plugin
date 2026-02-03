#!/usr/bin/env python3
"""
Manual test script for the rain-image endpoint.

This script simulates calling the endpoint and displays the response.
It can be used for local testing before deploying to Azure.
"""

import json
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from dateutil import tz
import pandas as pd

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_endpoint_with_mock_data(hours_without_rain=84.0):
    """
    Test the endpoint with mocked rain time data.
    
    Args:
        hours_without_rain: Number of hours to simulate without rain (default: 84 = 3.5 days)
    """
    print("=" * 70)
    print("MANUAL TEST: Rain Image Endpoint")
    print("=" * 70)
    print()
    
    # Import after path is set
    import function_app
    import azure.functions as func
    
    # Mock storage account key
    test_key = "YW55IGNhcm5hbCBwbGVhc3VyZS4="  # Base64 encoded test key
    
    print(f"Test scenario: {hours_without_rain} hours without rain")
    print(f"Expected image: dias-sin-llover-{function_app.get_image_number(hours_without_rain)}-full.png")
    print()
    
    # Mock the rain time calculation
    with patch.object(function_app, 'calculate_rain_time') as mock_calc:
        days = hours_without_rain / 24
        mock_calc.return_value = (hours_without_rain, days)
        
        # Mock the environment variable
        with patch.dict(os.environ, {'AZURE_STORAGE_ACCOUNT_KEY': test_key}):
            # Create a mock HTTP request
            req = Mock(spec=func.HttpRequest)
            
            # Call the endpoint
            print("Calling endpoint...")
            response = function_app.rain_image_endpoint(req)
            
            # Parse response
            status_code = response.status_code
            mimetype = response.mimetype
            body = response.get_body().decode('utf-8')
            data = json.loads(body)
            
            # Display results
            print(f"\nStatus Code: {status_code}")
            print(f"Content-Type: {mimetype}")
            print()
            print("Response JSON:")
            print(json.dumps(data, indent=2))
            print()
            
            if status_code == 200:
                print("✓ SUCCESS")
                print()
                print(f"Image URL: {data['imageUrl'][:100]}...")
                print(f"Hours: {data['value_h']}")
                print(f"Days: {data['value_d']}")
                
                # Extract image name from URL
                if data['imageUrl']:
                    image_name = data['imageUrl'].split('/')[-1].split('?')[0]
                    print(f"Image: {image_name}")
            else:
                print("✗ ERROR")
                print(f"Error: {data.get('error', 'Unknown error')}")
    
    print()
    print("=" * 70)

def test_all_time_ranges():
    """Test endpoint with various time ranges to see all images."""
    print("\n" + "=" * 70)
    print("TESTING ALL IMAGE RANGES")
    print("=" * 70)
    print()
    
    import function_app
    
    # Test cases: (hours, expected_image_number)
    test_cases = [
        (12, "00", "12 hours - Less than 1 day"),
        (30, "01", "30 hours - 1.25 days"),
        (60, "02", "60 hours - 2.5 days"),
        (84, "03", "84 hours - 3.5 days"),
        (108, "04", "108 hours - 4.5 days"),
        (132, "05", "132 hours - 5.5 days"),
        (156, "06", "156 hours - 6.5 days"),
        (180, "07", "180 hours - 7.5 days"),
        (204, "08", "204 hours - 8.5 days"),
        (228, "09", "228 hours - 9.5 days"),
        (300, "10", "300 hours - 12.5 days"),
    ]
    
    print(f"{'Hours':<8} {'Days':<8} {'Image':<8} {'Description':<30}")
    print("-" * 70)
    
    for hours, expected, description in test_cases:
        days = hours / 24
        image_num = function_app.get_image_number(hours)
        status = "✓" if image_num == expected else "✗"
        
        print(f"{hours:<8} {days:<8.2f} {image_num:<8} {description:<30} {status}")
    
    print()

def test_error_scenarios():
    """Test error handling scenarios."""
    print("\n" + "=" * 70)
    print("TESTING ERROR SCENARIOS")
    print("=" * 70)
    print()
    
    import function_app
    import azure.functions as func
    
    # Test 1: No storage key
    print("Test 1: Missing AZURE_STORAGE_ACCOUNT_KEY")
    print("-" * 70)
    
    with patch.object(function_app, 'calculate_rain_time') as mock_calc:
        mock_calc.return_value = (24.0, 1.0)
        
        with patch.dict(os.environ, {}, clear=True):
            req = Mock(spec=func.HttpRequest)
            response = function_app.rain_image_endpoint(req)
            data = json.loads(response.get_body().decode('utf-8'))
            
            print(f"Status: {response.status_code}")
            print(f"Error: {data.get('error', 'No error')}")
            print(f"imageUrl: {data['imageUrl']}")
            print()
    
    # Test 2: Rain calculation fails
    print("Test 2: Rain time calculation fails")
    print("-" * 70)
    
    with patch.object(function_app, 'calculate_rain_time') as mock_calc:
        mock_calc.return_value = (None, None)
        
        req = Mock(spec=func.HttpRequest)
        response = function_app.rain_image_endpoint(req)
        data = json.loads(response.get_body().decode('utf-8'))
        
        print(f"Status: {response.status_code}")
        print(f"Error: {data.get('error', 'No error')}")
        print(f"value_h: {data['value_h']}")
        print(f"value_d: {data['value_d']}")
        print()

def main():
    """Run all manual tests."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "RAIN IMAGE ENDPOINT - MANUAL TESTS" + " " * 19 + "║")
    print("╚" + "=" * 68 + "╝")
    
    try:
        # Test 1: Default scenario (3.5 days without rain)
        test_endpoint_with_mock_data(hours_without_rain=84.0)
        
        # Test 2: All time ranges
        test_all_time_ranges()
        
        # Test 3: Error scenarios
        test_error_scenarios()
        
        print("\n" + "=" * 70)
        print("✓ All manual tests completed successfully!")
        print("=" * 70)
        print()
        
    except Exception as e:
        print(f"\n✗ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
