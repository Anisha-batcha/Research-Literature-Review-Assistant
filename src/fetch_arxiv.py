"""
arXiv Search Module
---------------------
arXiv provides a free, keyless API that returns paper metadata (title,
authors, abstract, publish date) as an Atom XML feed. This module
queries it and parses the results into plain Python dicts.

Docs: https://info.arxiv.org/help/api/user-manual.html
"""

import xml.etree.ElementTree as ET
import requests

ARXIV_API_URL = "http://export.arxiv.org/api/query"
ATOM_NS = "{http://www.w3.org/2005/Atom}"


def search_arxiv(
    query,
    max_results=15,
    year_from=None,
    year_to=None,
    category=None,
    sort_by="relevance",
):
    """
    Search arXiv for a topic and return a list of paper dicts:
    {title, summary, year, authors, url}
    """
    search_parts = [f"all:{query}"]
    if year_from or year_to:
        start = f"{year_from or 1900}01010000"
        end = f"{year_to or 2100}12312359"
        search_parts.append(f"submittedDate:[{start} TO {end}]")
    if category:
        search_parts.append(f"cat:{category}")

    params = {
        "search_query": " AND ".join(search_parts),
        "start": 0,
        "max_results": max_results,
        "sortBy": sort_by,
        "sortOrder": "descending",
    }
    response = requests.get(ARXIV_API_URL, params=params, timeout=30)
    response.raise_for_status()
    return parse_arxiv_feed(response.text)


def parse_arxiv_feed(xml_text):
    """
    Parse an arXiv Atom XML feed (as returned by search_arxiv or saved
    from a test fixture) into a list of paper dicts.
    """
    root = ET.fromstring(xml_text)
    papers = []

    for entry in root.findall(f"{ATOM_NS}entry"):
        title_el = entry.find(f"{ATOM_NS}title")
        summary_el = entry.find(f"{ATOM_NS}summary")
        published_el = entry.find(f"{ATOM_NS}published")
        id_el = entry.find(f"{ATOM_NS}id")

        if title_el is None or summary_el is None:
            continue

        title = " ".join(title_el.text.split())
        summary = " ".join(summary_el.text.split())
        published = published_el.text if published_el is not None else ""
        year = published[:4] if published else "n.d."
        url = id_el.text if id_el is not None else ""

        authors = [
            a.find(f"{ATOM_NS}name").text
            for a in entry.findall(f"{ATOM_NS}author")
            if a.find(f"{ATOM_NS}name") is not None
        ]

        papers.append({
            "title": title,
            "summary": summary,
            "year": year,
            "authors": authors,
            "url": url,
        })

    return papers
