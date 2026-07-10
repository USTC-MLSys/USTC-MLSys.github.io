# Publication Agent

This directory contains the publication ingestion backend for the lab website.

## Active workflow

The current primary workflow is:

```bash
1. User selects a PDF in the portal
2. `/parse` extracts metadata locally and optionally via DeepSeek
3. User confirms or edits fields
4. Portal publishes directly to `content/publications.json`
5. Portal rebuilds the static site
```

## CLI commands

Create a pending entry from a submission folder:

```bash
python -m tools.publication_agent.submit_publication --submission /path/to/submission
```

Publish a reviewed entry:

```bash
python -m tools.publication_agent.publish_publication --slug your-paper-slug
```

Inspect legacy pending entries:

```bash
python -m tools.publication_agent.review_publications
python -m tools.publication_agent.review_publications --slug your-paper-slug
```

Serve a minimal local portal:

```bash
python -m tools.publication_agent.portal --port 8123
```

## Submission folder

```text
submission/
  paper.pdf
  meta.json
```

You can start from `templates/meta.template.json`.

## Notes

- `service.py` is the shared backend orchestration layer used by portal and CLI flows.
- `parser.py` performs heuristic extraction of title, authors, abstract, and year.
- When `DEEPSEEK_API_KEY` is configured, parsing automatically upgrades to:
  - local PDF text extraction
  - DeepSeek JSON-structured metadata cleanup
- Portal submissions publish directly to `content/publications.json`.
- `content/publications_pending.json` is still supported for legacy/manual review workflows.

## DeepSeek integration

Set these environment variables in the backend runtime:

```bash
export DEEPSEEK_API_KEY=your_key_here
export DEEPSEEK_BASE_URL=https://api.deepseek.com
export DEEPSEEK_MODEL=deepseek-chat
```

Behavior:

- If `DEEPSEEK_API_KEY` is missing, the parser uses local heuristic extraction only.
- If `DEEPSEEK_API_KEY` is present, the parser sends the PDF text excerpt plus heuristic result to DeepSeek and expects strict JSON back.

The API key must stay on the backend only. Do not expose it in browser JavaScript.
