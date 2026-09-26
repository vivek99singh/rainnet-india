import io
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from scripts.fetch_indianapi import fetch


class IndianApiTests(unittest.TestCase):
    def test_missing_key_does_not_send_request(self):
        with patch("scripts.fetch_indianapi.urlopen") as request:
            with self.assertRaisesRegex(ValueError, "INDIANAPI_KEY"):
                fetch("Mumbai", "india", "")
            request.assert_not_called()

    def test_secret_only_in_header_and_expected_forecast_path(self):
        with patch("scripts.fetch_indianapi.urlopen", return_value=io.BytesIO(b'{"city":"Mumbai", "weather":{"forecast":[]}}')) as call:
            result = fetch("Mumbai", "india", "test-placeholder")
            request = call.call_args.args[0]
            self.assertEqual(request.full_url, "https://weather.indianapi.in/india/weather?city=Mumbai")
            self.assertEqual(request.get_header("X-api-key"), "test-placeholder")
            self.assertNotIn("test-placeholder", str(result))

    def test_provider_error_does_not_echo_response_body(self):
        error = HTTPError("https://weather.indianapi.in", 401, "secret-echo", {}, io.BytesIO(b'secret-echo'))
        with patch("scripts.fetch_indianapi.urlopen", side_effect=error):
            with self.assertRaises(ValueError) as caught:
                fetch("Mumbai", "india", "test-placeholder")
        self.assertIn("401", str(caught.exception))
        self.assertNotIn("secret-echo", str(caught.exception))
