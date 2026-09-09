import json
import unittest
from datetime import datetime

from scripts.update_content import (
    BLOG_END,
    BLOG_START,
    PAPER_END,
    PAPER_START,
    BlogPost,
    Paper,
    parse_arxiv_papers,
    parse_blog_posts,
    update_index,
)


class ContentUpdaterTests(unittest.TestCase):
    def test_parses_and_sorts_nvidia_posts(self):
        payload = json.dumps(
            [
                {
                    "date": "2026-07-09T12:40:37",
                    "status": "publish",
                    "link": "https://developer.nvidia.com/blog/older/",
                    "title": {"rendered": "Older &amp; useful"},
                },
                {
                    "date": "2026-08-21T09:21:04",
                    "status": "publish",
                    "link": "https://developer.nvidia.com/blog/newer/",
                    "title": {"rendered": "Newer"},
                },
            ]
        ).encode()

        posts = parse_blog_posts(payload)

        self.assertEqual(["Newer", "Older & useful"], [post.title for post in posts])

    def test_filters_same_name_arxiv_authors_by_topic(self):
        payload = b"""<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>http://arxiv.org/abs/2607.24518v1</id>
            <title>Portfolio factorization on GPUs</title>
            <summary>Risk modeling for large portfolios.</summary>
            <published>2026-07-27T14:56:00Z</published>
            <category term="cs.LG"/>
            <author><name>Dhruv Desai</name></author>
          </entry>
          <entry>
            <id>http://arxiv.org/abs/2609.00001v1</id>
            <title>Unrelated physics paper</title>
            <summary>Stellar winds and magnetized stars.</summary>
            <published>2026-09-01T00:00:00Z</published>
            <category term="astro-ph.HE"/>
            <author><name>Dhruv Desai</name></author>
          </entry>
        </feed>"""

        papers = parse_arxiv_papers(payload)

        self.assertEqual(["2607.24518"], [paper.arxiv_id for paper in papers])

    def test_replaces_blogs_and_prepends_new_papers(self):
        index = f"""<ol>
{PAPER_START}
        <li><a href="https://arxiv.org/abs/2607.24518">Existing</a></li>
{PAPER_END}
</ol>
<div>
{BLOG_START}
        <p>Old blog</p>
{BLOG_END}
</div>
"""
        paper = Paper(
            arxiv_id="2609.00001",
            title="A new finance paper",
            published=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        )
        post = BlogPost(
            title="A new blog",
            url="https://developer.nvidia.com/blog/a-new-blog/",
            published=datetime.fromisoformat("2026-09-01T00:00:00"),
        )

        updated = update_index(index, [post], [paper])

        self.assertIn("A new finance paper", updated)
        self.assertIn("Existing", updated)
        self.assertIn("A new blog", updated)
        self.assertNotIn("Old blog", updated)


if __name__ == "__main__":
    unittest.main()
