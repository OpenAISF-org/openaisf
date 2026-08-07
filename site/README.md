# openaisf.org

One self-contained page. No build step, no external requests, no fonts to fetch,
no analytics.

## Why the CSP is strict

The policy in `netlify.toml` is part of the argument rather than boilerplate. A
standard about verifiable claims should not ask you to trust that its own page
behaves. `default-src 'none'` denies everything by default, and the two inline
scripts are pinned by SHA-256 hash instead of being waved through with
`unsafe-inline`.

**If you edit the inline script or the JSON-LD block, the hashes change and the
page will silently stop working.** Regenerate them:

```bash
python3 - <<'PY'
import hashlib, base64, re, pathlib
html = pathlib.Path("index.html").read_text()
for b in re.findall(r"<script(?:[^>]*)>(.*?)</script>", html, re.S):
    print("'sha256-" + base64.b64encode(hashlib.sha256(b.encode()).digest()).decode() + "'")
PY
```

Paste the results into the `script-src` directive.

## The numbers are generated output

The coverage table, control counts and applicability figures on the page come
from the tooling, not from copy. Regenerate before publishing a change:

```bash
openaisf coverage
```

## Files

| | |
|---|---|
| `index.html` | The page. Self-contained. |
| `netlify.toml` | Static deploy plus security headers. |
| `llms.txt` | Structured context for AI systems ([llmstxt.org](https://llmstxt.org)). Keep in sync with the page. |
| `robots.txt` | Allows every crawler, including AI crawlers, explicitly. OpenAISF exists to be cited. |
| `sitemap.xml` | Two URLs. Update `lastmod` on change. |

## Deploy

Point Netlify at this directory. There is nothing to build.
