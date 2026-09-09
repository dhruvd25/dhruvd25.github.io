#!/usr/bin/env python3
"""Refresh NVIDIA blog posts and discover new arXiv papers."""

from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "index.html"

BLOG_START = "        <!-- AUTO-BLOGS:START -->"
BLOG_END = "        <!-- AUTO-BLOGS:END -->"
PAPER_START = "        <!-- AUTO-ARXIV:START -->"
PAPER_END = "        <!-- AUTO-ARXIV:END -->"

NVIDIA_AUTHOR_ID = 3071
ARXIV_AUTHOR = "Dhruv Desai"
ARXIV_DISCOVERY_START = datetime.fromisoformat("2026-07-27T14:56:00+00:00")
USER_AGENT = "dhruvd25.github.io content updater/1.0"

FINANCE_TERMS = re.compile(
    r"\b(finance|financial|portfolio|portfolios|trading|markets?|assets?|"
    r"bonds?|funds?|risk)\b",
    re.IGNORECASE,
)
RELEVANT_CATEGORY_PREFIXES = ("q-fin.", "cs.", "stat.")
RELEVANT_CATEGORIES = {"math.NA", "math.OC"}

ATOM = {"atom": "http://www.w3.org/2005/Atom"}


@dataclass(frozen=True)
class Paper:
    arxiv_id: str
    title: str
    published: datetime

    @property
    def url(self) -> str:
        return f"https://arxiv.org/abs/{self.arxiv_id}"


@dataclass(frozen=True)
class BlogPost:
    title: str
    url: str
    published: datetime


def fetch(url: str, accept: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"Accept": accept, "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def nvidia_api_url() -> str:
    query = urllib.parse.urlencode(
        {
            "author": NVIDIA_AUTHOR_ID,
            "per_page": 100,
            "_fields": "link,title,date,status",
        }
    )
    return f"https://developer-blogs.nvidia.com/wp-json/wp/v2/posts?{query}"


def arxiv_api_url() -> str:
    query = urllib.parse.urlencode(
        {
            "search_query": f'au:"{ARXIV_AUTHOR}"',
            "start": 0,
            "max_results": 50,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    return f"https://export.arxiv.org/api/query?{query}"


def parse_blog_posts(payload: bytes) -> list[BlogPost]:
    records = json.loads(payload)
    posts: list[BlogPost] = []

    for record in records:
        if record.get("status") != "publish":
            continue

        url = record.get("link", "")
        parsed_url = urllib.parse.urlparse(url)
        if parsed_url.scheme != "https" or parsed_url.netloc != "developer.nvidia.com":
            raise ValueError(f"Unexpected NVIDIA blog URL: {url!r}")

        rendered_title = record.get("title", {}).get("rendered", "")
        title = " ".join(html.unescape(rendered_title).split())
        if not title:
            raise ValueError("NVIDIA returned a post without a title")

        published = datetime.fromisoformat(record["date"])
        posts.append(BlogPost(title=title, url=url, published=published))

    if not posts:
        raise ValueError("NVIDIA returned no published posts; refusing to clear the page")

    return sorted(posts, key=lambda post: post.published, reverse=True)


def parse_arxiv_papers(payload: bytes) -> list[Paper]:
    root = ET.fromstring(payload)
    papers: list[Paper] = []

    for entry in root.findall("atom:entry", ATOM):
        authors = {
            " ".join((author.findtext("atom:name", default="", namespaces=ATOM)).split())
            for author in entry.findall("atom:author", ATOM)
        }
        if ARXIV_AUTHOR not in authors:
            continue

        categories = {
            category.attrib.get("term", "")
            for category in entry.findall("atom:category", ATOM)
        }
        has_relevant_category = any(
            category.startswith(RELEVANT_CATEGORY_PREFIXES)
            or category in RELEVANT_CATEGORIES
            for category in categories
        )
        if not has_relevant_category:
            continue

        title = " ".join(entry.findtext("atom:title", default="", namespaces=ATOM).split())
        summary = " ".join(
            entry.findtext("atom:summary", default="", namespaces=ATOM).split()
        )
        if not FINANCE_TERMS.search(f"{title} {summary}"):
            continue

        identifier = entry.findtext("atom:id", default="", namespaces=ATOM)
        match = re.search(r"/abs/(\d{4}\.\d{4,5})(?:v\d+)?$", identifier)
        if not match:
            raise ValueError(f"Unexpected arXiv identifier: {identifier!r}")

        published_text = entry.findtext(
            "atom:published", default="", namespaces=ATOM
        )
        published = datetime.fromisoformat(published_text.replace("Z", "+00:00"))
        papers.append(
            Paper(arxiv_id=match.group(1), title=title, published=published)
        )

    paper_ids = {paper.arxiv_id for paper in papers}
    if "2607.24518" not in paper_ids:
        raise ValueError("Expected known arXiv paper was not returned")

    return sorted(papers, key=lambda paper: paper.published, reverse=True)


def region(text: str, start_marker: str, end_marker: str) -> str:
    start = text.find(start_marker)
    end = text.find(end_marker)
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"Missing or invalid markers: {start_marker}, {end_marker}")
    return text[start + len(start_marker) : end].strip("\n")


def replace_region(
    text: str,
    start_marker: str,
    end_marker: str,
    replacement: str,
) -> str:
    start = text.find(start_marker)
    end = text.find(end_marker)
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"Missing or invalid markers: {start_marker}, {end_marker}")

    content_start = start + len(start_marker)
    return (
        text[:content_start]
        + "\n"
        + replacement.strip("\n")
        + "\n"
        + text[end:]
    )


def render_blog(post: BlogPost) -> str:
    title = html.escape(post.title)
    url = html.escape(post.url, quote=True)
    return "\n".join(
        [
            "        <p>",
            f'          <a href="{url}" target="_blank" rel="noopener">{title}</a>',
            '          <span class="meta"> — NVIDIA Technical Blog</span>',
            "        </p>",
        ]
    )


def render_paper(paper: Paper) -> str:
    title = html.escape(paper.title)
    url = html.escape(paper.url, quote=True)
    return "\n".join(
        [
            "        <li>",
            '          <div class="pub-title">',
            f'            <a href="{url}" target="_blank" rel="noopener">{title}</a>',
            "          </div>",
            f'          <div class="pub-meta">arXiv, {paper.published.year}.</div>',
            "        </li>",
        ]
    )


def update_papers(index: str, arxiv_papers: list[Paper]) -> str:
    existing_papers = region(index, PAPER_START, PAPER_END)
    existing_ids = set(
        re.findall(r"arxiv\.org/abs/(\d{4}\.\d{4,5})", existing_papers)
    )

    new_papers = [
        paper
        for paper in arxiv_papers
        if paper.published > ARXIV_DISCOVERY_START
        and paper.arxiv_id not in existing_ids
    ]
    rendered_new_papers = "\n".join(render_paper(paper) for paper in new_papers)
    paper_content = existing_papers
    if rendered_new_papers:
        paper_content = f"{rendered_new_papers}\n{existing_papers}"

    return replace_region(index, PAPER_START, PAPER_END, paper_content)


def update_blogs(index: str, blog_posts: list[BlogPost]) -> str:
    blog_content = "\n".join(render_blog(post) for post in blog_posts)
    return replace_region(index, BLOG_START, BLOG_END, blog_content)


def update_index(
    index: str,
    blog_posts: list[BlogPost],
    arxiv_papers: list[Paper],
) -> str:
    return update_blogs(update_papers(index, arxiv_papers), blog_posts)


def main() -> None:
    current = INDEX_PATH.read_text(encoding="utf-8")
    updated = current
    refreshed_sources: list[str] = []

    try:
        blog_posts = parse_blog_posts(fetch(nvidia_api_url(), "application/json"))
    except Exception as error:
        print(f"::warning title=NVIDIA blog update failed::{error}")
    else:
        updated = update_blogs(updated, blog_posts)
        refreshed_sources.append(f"{len(blog_posts)} NVIDIA blog posts")

    try:
        arxiv_papers = parse_arxiv_papers(
            fetch(arxiv_api_url(), "application/atom+xml")
        )
    except Exception as error:
        print(f"::warning title=arXiv update failed::{error}")
    else:
        updated = update_papers(updated, arxiv_papers)
        refreshed_sources.append(
            f"{len(arxiv_papers)} relevant arXiv records checked"
        )

    if updated == current:
        print("Content is already up to date.")
        return

    INDEX_PATH.write_text(updated, encoding="utf-8")
    print(f"Updated content ({'; '.join(refreshed_sources)}).")


if __name__ == "__main__":
    main()
