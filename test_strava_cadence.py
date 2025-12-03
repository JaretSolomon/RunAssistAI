"""
Simple unit test for Strava cadence extraction from payload JSON.

This tests the recent change where we extract average_cadence from the 
stored payload_json when fetching recent Strava runs.
"""

import json
import unittest
from unittest.mock import Mock, patch


def extract_cadence_from_payload(payload_raw: str) -> float | None:
    """
    Extract cadence from payload JSON - this mirrors the logic in 
    get_recent_strava_runs() in services.py
    """
    if not payload_raw:
        return None
    try:
        payload_data = json.loads(payload_raw)
        return payload_data.get("average_cadence")
    except Exception:
        return None


class TestStravaCadenceExtraction(unittest.TestCase):
    """Test cadence extraction from Strava payload JSON"""

    def test_extract_cadence_with_valid_payload(self):
        """Test extracting cadence from a valid payload"""
        payload = json.dumps({
            "id": 12345,
            "average_cadence": 180.5,
            "distance": 5000,
            "moving_time": 1200
        })
        result = extract_cadence_from_payload(payload)
        self.assertEqual(result, 180.5)

    def test_extract_cadence_missing_field(self):
        """Test when payload doesn't have average_cadence"""
        payload = json.dumps({
            "id": 12345,
            "distance": 5000,
            "moving_time": 1200
        })
        result = extract_cadence_from_payload(payload)
        self.assertIsNone(result)

    def test_extract_cadence_null_payload(self):
        """Test with null/empty payload"""
        result = extract_cadence_from_payload(None)
        self.assertIsNone(result)
        
        result = extract_cadence_from_payload("")
        self.assertIsNone(result)

    def test_extract_cadence_invalid_json(self):
        """Test with invalid JSON - should return None gracefully"""
        invalid_json = "{ invalid json }"
        result = extract_cadence_from_payload(invalid_json)
        self.assertIsNone(result)

    def test_extract_cadence_zero_value(self):
        """Test when cadence is 0 (valid but edge case)"""
        payload = json.dumps({
            "id": 12345,
            "average_cadence": 0,
            "distance": 5000
        })
        result = extract_cadence_from_payload(payload)
        self.assertEqual(result, 0)

    def test_extract_cadence_real_world_example(self):
        """Test with a realistic Strava activity payload"""
        payload = json.dumps({
            "id": 16623889026,
            "name": "Morning Run",
            "distance": 540.0,
            "moving_time": 215,
            "elapsed_time": 215,
            "average_cadence": 80.0,
            "average_heartrate": 140.0,
            "calories": 36
        })
        result = extract_cadence_from_payload(payload)
        self.assertEqual(result, 80.0)


if __name__ == "__main__":
    unittest.main()

