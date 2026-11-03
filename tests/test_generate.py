import os
import unittest
from unittest.mock import Mock, patch

from src.generate import _call_groq, _try_model


class GroqGenerationTests(unittest.TestCase):
    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
    @patch("src.generate.requests.post")
    def test_uses_bearer_authentication(self, post):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "choices": [{"message": {"content": "Generated text"}}]
        }
        post.return_value = response

        result, error = _try_model("test-model", "test-key", "prompt")

        self.assertEqual(result, "Generated text")
        self.assertIsNone(error)
        self.assertEqual(
            post.call_args.kwargs["headers"]["Authorization"], "Bearer test-key"
        )

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_api_key_is_an_explicit_error(self):
        with self.assertRaisesRegex(RuntimeError, "GROQ_API_KEY"):
            _call_groq("prompt")


if __name__ == "__main__":
    unittest.main()
