# dhruvd25.github.io

Personal academic website for Dhruv Desai.

## Automatic content updates

The Pages workflow refreshes content before every deployment and on Mondays at
09:17 UTC:

- Blog posts are loaded from Dhruv's NVIDIA Technical Blog author record.
- New arXiv papers are discovered by author name, relevant subject categories,
  and finance-related terms. The discovery date starts after the newest paper
  currently curated on the page, so older omitted papers are not added.

Existing paper venue labels remain manually curated. Newly discovered papers
are labeled `arXiv, YEAR` until their publication details are updated.

Run the same update locally with:

```sh
python3 scripts/update_content.py
python3 -m unittest discover -s tests
```

Content managed by the updater is enclosed by `AUTO-ARXIV` and `AUTO-BLOGS`
comments in `index.html`.

## GitHub Pages setup

In the repository settings, select **GitHub Actions** as the Pages build and
deployment source. The workflow can also be run manually from the Actions tab.
