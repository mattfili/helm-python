# 09 — GitHub Code Mode

Chain real GitHub API calls with Python control flow — search, filter, aggregate, and compare. This is what Code Mode looks like with a production API.

## What You'll Learn

- Chaining multiple API calls with `.call()` in loops
- Aggregating and ranking results from multiple endpoints
- Conditional logic based on API response data
- Building side-by-side comparisons from parallel data fetches

## Run It

```bash
pip install -e ../..
python main.py
```

Set `GITHUB_TOKEN` for 5,000 req/hr (this example makes ~15-20 calls):

```bash
export GITHUB_TOKEN=ghp_your_token_here
python main.py
```

## Scenarios

1. **Search + Rank** — Search "machine learning python" repos, fetch full details for each, rank by stars
2. **Org Repos + Issue Scan** — List pallets org repos, filter to those with open issues, show issue details
3. **Compare Two Repos** — Fetch Flask vs Django stats (stars, forks, languages, top contributors) side by side
