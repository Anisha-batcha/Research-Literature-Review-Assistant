import time
import unittest
import uuid
from unittest.mock import patch

from fastapi import HTTPException

from app import PaperSession, ReviewRequest, paper_sessions, write_review


class ReviewSelectionTests(unittest.TestCase):
    def setUp(self):
        self.session_id = uuid.uuid4()
        self.papers = [
            {"title": "Paper one", "url": "https://arxiv.org/abs/1"},
            {"title": "Paper two", "url": "https://arxiv.org/abs/2"},
        ]
        paper_sessions[str(self.session_id)] = PaperSession(
            topic="testing",
            papers=self.papers,
            index=None,
            last_accessed=time.monotonic(),
        )

    def tearDown(self):
        paper_sessions.pop(str(self.session_id), None)

    @patch("app.generate_literature_review", return_value="Review cites [1].")
    def test_review_uses_selected_papers_and_returns_citation_mapping(self, generate):
        result = write_review(
            ReviewRequest(session_id=self.session_id, paper_indices=[1])
        )

        generate.assert_called_once_with("testing", [self.papers[1]])
        self.assertEqual(result["review"], "Review cites [1].")
        self.assertEqual(
            result["citations"]["1"],
            {
                "index": 1,
                "title": "Paper two",
                "url": "https://arxiv.org/abs/2",
            },
        )

    def test_review_rejects_duplicate_paper_indices(self):
        with self.assertRaises(HTTPException) as error:
            write_review(ReviewRequest(session_id=self.session_id, paper_indices=[0, 0]))

        self.assertEqual(error.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
