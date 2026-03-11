# 10 — GitHub Explorer

Combine OpenAPI skill + custom analysis skill + Code Mode into a multi-step explore-analyze-report workflow. This is helm's "wow" example — real API data, custom scoring, and formatted reports in one script.

## What You'll Learn

- Registering both `openapi()` and `define_skill()` skills on one agent
- Multi-step workflows: search → fetch → analyze → report
- Combining real API data with custom computation
- Generating formatted reports from aggregated results

## Run It

```bash
pip install -e ../..
python main.py
```

Set `GITHUB_TOKEN` for 5,000 req/hr (this example makes ~15 calls):

```bash
export GITHUB_TOKEN=ghp_your_token_here
python main.py
```

## How It Works

1. **Register skills** — 18 GitHub API operations + 2 custom analysis operations
2. **Search** — Find "python async" repos via GitHub search
3. **Fetch** — Get full details + languages for each result
4. **Analyze** — Compute health scores (0–100) using the custom `analysis.health_score` operation
5. **Report** — Generate a formatted report via `analysis.format_report`

The health score weighs popularity (stars), community (fork ratio), maintenance (freshness), and issue health.
