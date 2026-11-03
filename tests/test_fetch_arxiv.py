import unittest
from unittest.mock import Mock, patch

from src.fetch_arxiv import search_arxiv


class SearchArxivTests(unittest.TestCase):
    @patch("src.fetch_arxiv.requests.get")
    def test_builds_query_from_search_filters(self, get):
        response = Mock()
        response.text = "<feed xmlns='http://www.w3.org/2005/Atom' />"
        get.return_value = response

        search_arxiv(
            "neural networks",
            max_results=10,
            year_from=2020,
            year_to=2024,
            category="cs.AI",
            sort_by="submittedDate",
        )

        get.assert_called_once()
        params = get.call_args.kwargs["params"]
        self.assertEqual(
            params["search_query"],
            "all:neural networks AND submittedDate:[202001010000 TO 202412312359] AND cat:cs.AI",
        )
        self.assertEqual(params["sortBy"], "submittedDate")
        self.assertEqual(params["max_results"], 10)


if __name__ == "__main__":
    unittest.main()
