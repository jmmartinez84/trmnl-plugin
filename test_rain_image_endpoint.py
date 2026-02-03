"""
Tests for the rain image endpoint with SAS token generation.
"""
import unittest
from unittest.mock import Mock, patch
import json
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestRainImageEndpoint(unittest.TestCase):
    """Test suite for rain image endpoint functionality."""
    
    def test_get_image_number_less_than_24h(self):
        """Test image selection for less than 24 hours."""
        from function_app import get_image_number
        
        # 12 hours
        result = get_image_number(12)
        self.assertEqual(result, "00")
        
        # 23.5 hours
        result = get_image_number(23.5)
        self.assertEqual(result, "00")
    
    def test_get_image_number_1_to_2_days(self):
        """Test image selection for 1-2 days."""
        from function_app import get_image_number
        
        # 24 hours (1 day)
        result = get_image_number(24)
        self.assertEqual(result, "01")
        
        # 36 hours (1.5 days)
        result = get_image_number(36)
        self.assertEqual(result, "01")
        
        # 47 hours
        result = get_image_number(47)
        self.assertEqual(result, "01")
    
    def test_get_image_number_2_to_3_days(self):
        """Test image selection for 2-3 days."""
        from function_app import get_image_number
        
        # 48 hours (2 days)
        result = get_image_number(48)
        self.assertEqual(result, "02")
        
        # 60 hours
        result = get_image_number(60)
        self.assertEqual(result, "02")
    
    def test_get_image_number_all_ranges(self):
        """Test all image number ranges."""
        from function_app import get_image_number
        
        test_cases = [
            (12, "00"),      # < 1 day
            (24, "01"),      # 1 day
            (48, "02"),      # 2 days
            (72, "03"),      # 3 days
            (96, "04"),      # 4 days
            (120, "05"),     # 5 days
            (144, "06"),     # 6 days
            (168, "07"),     # 7 days
            (192, "08"),     # 8 days
            (216, "09"),     # 9 days
            (240, "10"),     # 10 days
            (300, "10"),     # 12.5 days (>= 10)
        ]
        
        for hours, expected in test_cases:
            with self.subTest(hours=hours):
                result = get_image_number(hours)
                self.assertEqual(result, expected, 
                    f"Expected {expected} for {hours} hours ({hours/24:.1f} days), got {result}")
    
    def test_get_image_number_none_input(self):
        """Test image selection with None input."""
        from function_app import get_image_number
        
        result = get_image_number(None)
        self.assertEqual(result, "00")
    
    def test_generate_sas_url_format(self):
        """Test SAS URL generation format (mocked)."""
        from function_app import generate_sas_url, BLOB_BASE_URL
        
        # Mock environment variable
        with patch.dict(os.environ, {'AZURE_STORAGE_ACCOUNT_KEY': 'test_key_12345=='}):
            # Mock generate_blob_sas to return a known token
            with patch('function_app.generate_blob_sas') as mock_sas:
                mock_sas.return_value = 'sv=2021-08-06&st=2026-02-03T19%3A00%3A00Z&se=2026-02-03T20%3A00%3A00Z&sr=b&sp=r&sig=test_signature'
                
                blob_name = "dias-sin-llover-05-full.png"
                result = generate_sas_url(blob_name, validity_hours=1)
                
                self.assertIsNotNone(result)
                self.assertIn(BLOB_BASE_URL, result)
                self.assertIn(blob_name, result)
                self.assertIn("?", result)  # SAS token separator
                self.assertIn("sv=", result)  # SAS version
                self.assertIn("sp=r", result)  # Read permission
    
    def test_generate_sas_url_no_key(self):
        """Test SAS URL generation without storage key."""
        from function_app import generate_sas_url
        
        # Ensure no key is set
        with patch.dict(os.environ, {}, clear=True):
            result = generate_sas_url("test.png")
            self.assertIsNone(result)
    
    @patch('function_app.get_last_rain_persisted')
    def test_calculate_rain_time(self, mock_get_rain):
        """Test rain time calculation."""
        from function_app import calculate_rain_time
        import pandas as pd
        from dateutil import tz
        
        # Mock last rain: 2 days ago
        spanish_tz = tz.gettz('Europe/Madrid')
        now = datetime.now(spanish_tz)
        last_rain = now - timedelta(days=2)
        
        # Return pandas Timestamp (as stored in Table Storage)
        mock_get_rain.return_value = pd.Timestamp(last_rain)
        
        hours, days = calculate_rain_time()
        
        # Should be approximately 2 days (48 hours)
        self.assertIsNotNone(hours)
        self.assertIsNotNone(days)
        self.assertAlmostEqual(days, 2.0, delta=0.1)
        self.assertAlmostEqual(hours, 48.0, delta=2.0)
    
    @patch('function_app.calculate_rain_time')
    @patch('function_app.generate_sas_url')
    def test_rain_image_endpoint_success(self, mock_sas, mock_rain_time):
        """Test successful endpoint response."""
        from function_app import rain_image_endpoint
        import azure.functions as func
        
        # Mock rain time: 3.5 days (84 hours)
        mock_rain_time.return_value = (84.0, 3.5)
        
        # Mock SAS URL
        mock_sas.return_value = "https://staticfilestrmnlsa.blob.core.windows.net/images/dias-sin-llover-03-full.png?sas_token"
        
        # Create mock request
        req = Mock(spec=func.HttpRequest)
        
        # Call endpoint
        response = rain_image_endpoint(req)
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")
        
        # Parse JSON response
        data = json.loads(response.get_body().decode('utf-8'))
        
        self.assertIn("imageUrl", data)
        self.assertIn("value_h", data)
        self.assertIn("value_d", data)
        
        self.assertIn("dias-sin-llover-03-full.png", data["imageUrl"])
        self.assertEqual(data["value_h"], "84.0")
        self.assertEqual(data["value_d"], "3.50")
    
    @patch('function_app.calculate_rain_time')
    def test_rain_image_endpoint_error_calculation(self, mock_rain_time):
        """Test endpoint when rain time calculation fails."""
        from function_app import rain_image_endpoint
        import azure.functions as func
        
        # Mock rain time error
        mock_rain_time.return_value = (None, None)
        
        # Create mock request
        req = Mock(spec=func.HttpRequest)
        
        # Call endpoint
        response = rain_image_endpoint(req)
        
        # Verify error response
        self.assertEqual(response.status_code, 500)
        
        # Parse JSON response
        data = json.loads(response.get_body().decode('utf-8'))
        
        self.assertIn("error", data)
        self.assertIsNone(data["imageUrl"])
    
    @patch('function_app.calculate_rain_time')
    @patch('function_app.generate_sas_url')
    def test_rain_image_endpoint_error_sas(self, mock_sas, mock_rain_time):
        """Test endpoint when SAS generation fails."""
        from function_app import rain_image_endpoint
        import azure.functions as func
        
        # Mock rain time: 1 day
        mock_rain_time.return_value = (24.0, 1.0)
        
        # Mock SAS URL failure
        mock_sas.return_value = None
        
        # Create mock request
        req = Mock(spec=func.HttpRequest)
        
        # Call endpoint
        response = rain_image_endpoint(req)
        
        # Verify error response
        self.assertEqual(response.status_code, 500)
        
        # Parse JSON response
        data = json.loads(response.get_body().decode('utf-8'))
        
        self.assertIn("error", data)
        self.assertIsNone(data["imageUrl"])
        # Should still have time values
        self.assertEqual(data["value_h"], "24.0")
        self.assertEqual(data["value_d"], "1.00")
    
    def test_image_number_boundaries(self):
        """Test edge cases for image number calculation."""
        from function_app import get_image_number
        
        # Test boundary values
        self.assertEqual(get_image_number(23.99), "00")  # Just under 1 day
        self.assertEqual(get_image_number(24.0), "01")   # Exactly 1 day
        self.assertEqual(get_image_number(24.01), "01")  # Just over 1 day
        
        self.assertEqual(get_image_number(47.99), "01")  # Just under 2 days
        self.assertEqual(get_image_number(48.0), "02")   # Exactly 2 days
        
        self.assertEqual(get_image_number(239.99), "09") # Just under 10 days
        self.assertEqual(get_image_number(240.0), "10")  # Exactly 10 days
        self.assertEqual(get_image_number(1000.0), "10") # Way over 10 days

def run_tests():
    """Run all tests."""
    unittest.main(argv=[''], verbosity=2, exit=False)

if __name__ == "__main__":
    run_tests()
