from __future__ import annotations

import argparse
import cgi
import html
import json
import shutil
import tempfile
import urllib.parse
from pathlib import Path
from wsgiref.simple_server import make_server

from .common import CONTENT_DIR, load_json
from .review_publications import load_pending_publications
from .service import create_record_from_submission_dir, load_submission, parse_preview, publish_record, rebuild_site


def _html_page(title: str, body: str) -> bytes:
    site = load_json(CONTENT_DIR / "site.json", {})
    lab_name = html.escape(site.get("lab_name", "MLSys Lab"))
    tagline = html.escape(site.get("tagline", "MLSys @ USTC"))
    home_url = html.escape(site.get("base_url") or "http://127.0.0.1:8001")
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{html.escape(title)}</title>
    <style>
      :root {{
        --bg: #f5f0e6;
        --panel: rgba(252, 248, 240, 0.92);
        --panel-strong: rgba(255, 252, 246, 0.96);
        --border: rgba(118, 104, 87, 0.18);
        --ink: #191919;
        --muted: #635d56;
        --teal: #0f8a88;
        --copper: #c86d3a;
        --shadow: 0 18px 45px rgba(47, 39, 30, 0.08);
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        color: var(--ink);
        font-family: "Instrument Sans", "Segoe UI", sans-serif;
        background:
          radial-gradient(circle at top left, rgba(15, 138, 136, 0.12), transparent 32%),
          radial-gradient(circle at top right, rgba(200, 109, 58, 0.12), transparent 28%),
          linear-gradient(rgba(118, 104, 87, 0.08) 1px, transparent 1px),
          linear-gradient(90deg, rgba(118, 104, 87, 0.08) 1px, transparent 1px),
          var(--bg);
        background-size: auto, auto, 38px 38px, 38px 38px, auto;
      }}
      a {{ color: inherit; text-decoration: none; }}
      .shell {{ width: min(1120px, calc(100% - 40px)); margin: 0 auto; }}
      .site-header {{
        position: sticky;
        top: 0;
        z-index: 10;
        padding: 22px 0 14px;
        backdrop-filter: blur(10px);
      }}
      .site-header__inner {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 18px;
        padding: 14px 18px;
        border: 1px solid rgba(255, 255, 255, 0.4);
        border-radius: 999px;
        background: rgba(250, 246, 238, 0.84);
        box-shadow: var(--shadow);
      }}
      .brand {{
        display: flex;
        align-items: center;
        gap: 14px;
      }}
      .brand__mark {{
        width: 54px;
        height: 54px;
        display: grid;
        place-items: center;
        border-radius: 999px;
        background: #1c1c1c;
        color: #f7f1e8;
        font-family: "Iowan Old Style", "Times New Roman", serif;
        font-size: 1.4rem;
        font-weight: 700;
      }}
      .brand__text strong {{
        display: block;
        font-size: 1.45rem;
        line-height: 1.05;
      }}
      .brand__text small {{
        display: block;
        margin-top: 3px;
        color: var(--muted);
        font-size: 0.98rem;
      }}
      .site-nav {{
        display: flex;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
      }}
      .nav-link, button, .action-link {{
        border-radius: 999px;
        border: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.7);
        color: var(--ink);
        padding: 0.72rem 1.05rem;
        font: inherit;
        cursor: pointer;
        transition: transform 160ms ease, background 160ms ease, border-color 160ms ease;
      }}
      .nav-link:hover, button:hover, .action-link:hover {{
        transform: translateY(-1px);
        border-color: rgba(15, 138, 136, 0.35);
        background: rgba(255, 255, 255, 0.95);
      }}
      .action-link--primary, button {{
        background: #1c1c1c;
        color: #f7f1e8;
      }}
      main {{ padding: 24px 0 56px; }}
      .hero {{
        display: grid;
        grid-template-columns: 1.15fr 0.85fr;
        gap: 26px;
        align-items: stretch;
        margin-bottom: 24px;
      }}
      .hero__card, form, .card {{
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 28px;
        box-shadow: var(--shadow);
      }}
      .hero__card {{
        padding: 30px 30px 24px;
        min-height: 100%;
      }}
      .hero__eyebrow, .section-eyebrow {{
        margin: 0 0 10px;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.16em;
        font-size: 0.9rem;
      }}
      h1, h2 {{
        margin: 0;
        font-family: "Iowan Old Style", "Times New Roman", serif;
        font-weight: 700;
        line-height: 1.02;
      }}
      h1 {{ font-size: clamp(2.45rem, 5.2vw, 4.05rem); max-width: 10ch; }}
      h2 {{ font-size: clamp(2rem, 4vw, 2.8rem); }}
      .hero__summary, .muted {{
        color: var(--muted);
      }}
      .hero__summary {{
        margin: 16px 0 0;
        font-size: 1.02rem;
        line-height: 1.72;
        max-width: 34rem;
      }}
      .hero__aside {{
        padding: 24px;
        display: flex;
        flex-direction: column;
        justify-content: center;
      }}
      .hero__aside h3 {{
        margin: 0 0 14px;
        font-size: 1.1rem;
      }}
      .hero__aside ul {{
        margin: 0;
        padding-left: 1.1rem;
        color: var(--muted);
        line-height: 1.75;
      }}
      .hero__summary strong {{
        color: var(--ink);
      }}
      form, .card {{
        padding: 24px;
        margin-bottom: 18px;
      }}
      .section-eyebrow {{ margin-bottom: 14px; }}
      .section-head {{
        display: flex;
        align-items: end;
        justify-content: space-between;
        gap: 18px;
        margin-bottom: 18px;
      }}
      .form-note {{
        margin: 10px 0 0;
        color: var(--muted);
        line-height: 1.6;
      }}
      label {{
        display: block;
        margin-bottom: 14px;
        font-size: 0.96rem;
        font-weight: 600;
      }}
      .field-label {{
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 8px;
      }}
      .required-pill, .optional-pill {{
        border-radius: 999px;
        padding: 0.18rem 0.55rem;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.05em;
      }}
      .required-pill {{
        background: rgba(200, 109, 58, 0.12);
        color: #9f4f24;
      }}
      .optional-pill {{
        background: rgba(15, 138, 136, 0.1);
        color: #0e6e6c;
      }}
      input, textarea, select {{
        width: 100%;
        padding: 0.9rem 1rem;
        border-radius: 18px;
        border: 1px solid rgba(118, 104, 87, 0.24);
        background: var(--panel-strong);
        color: var(--ink);
        font: inherit;
        outline: none;
        transition: border-color 160ms ease, box-shadow 160ms ease, background 160ms ease;
      }}
      input:focus, textarea:focus, select:focus {{
        border-color: rgba(15, 138, 136, 0.6);
        box-shadow: 0 0 0 4px rgba(15, 138, 136, 0.11);
      }}
      input::placeholder, textarea::placeholder {{
        color: #8b847c;
      }}
      textarea {{ min-height: 132px; resize: vertical; }}
      .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
      .submit-row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        margin-top: 12px;
      }}
      .submit-row .muted {{ max-width: 38rem; line-height: 1.6; }}
      .flash {{
        padding: 20px 22px;
        border-radius: 24px;
        border: 1px solid var(--border);
        box-shadow: var(--shadow);
        background: rgba(252, 248, 240, 0.9);
        position: relative;
        overflow: hidden;
      }}
      .flash--error {{
        border-color: rgba(200, 109, 58, 0.22);
      }}
      .flash--ok {{
        border-color: rgba(15, 138, 136, 0.22);
      }}
      .flash::before {{
        content: "";
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 6px;
        background: rgba(23, 23, 23, 0.18);
      }}
      .flash--error::before {{
        background: var(--copper);
      }}
      .flash--ok::before {{
        background: var(--teal);
      }}
      .flash strong {{
        display: block;
        padding-left: 6px;
        line-height: 1.55;
      }}
      .flash__actions {{
        display: flex;
        gap: 0.8rem;
        flex-wrap: wrap;
        margin-top: 1rem;
        padding-left: 6px;
      }}
      .pending-list {{
        display: grid;
        gap: 12px;
      }}
      .pending-item {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        padding: 16px 18px;
        border-radius: 20px;
        background: rgba(255,255,255,0.55);
        border: 1px solid rgba(118, 104, 87, 0.14);
      }}
      .pending-item.is-highlighted {{
        border-color: rgba(15, 138, 136, 0.42);
        box-shadow: 0 0 0 4px rgba(15, 138, 136, 0.08);
        background: rgba(239, 251, 249, 0.82);
      }}
      .pending-item strong {{
        display: block;
        margin-bottom: 4px;
      }}
      .pending-item p {{
        margin: 0;
        color: var(--muted);
      }}
      .empty-state {{
        color: var(--muted);
        margin: 0;
      }}
      @media (max-width: 920px) {{
        .hero {{ grid-template-columns: 1fr; }}
        .hero__card {{
          min-height: auto;
        }}
      }}
      @media (max-width: 720px) {{
        .shell {{ width: min(100% - 24px, 1120px); }}
        .site-header__inner {{ border-radius: 28px; padding: 14px; }}
        .brand__mark {{ width: 48px; height: 48px; font-size: 1.2rem; }}
        .row {{ grid-template-columns: 1fr; gap: 0; }}
        .submit-row, .pending-item, .section-head {{ flex-direction: column; align-items: stretch; }}
      }}
    </style>
  </head>
  <body>
    <header class="site-header">
      <div class="shell site-header__inner">
        <a class="brand" href="{home_url}" target="_blank" rel="noreferrer">
          <span class="brand__mark">ML</span>
          <span class="brand__text">
            <strong>{lab_name}</strong>
            <small>{tagline}</small>
          </span>
        </a>
        <nav class="site-nav">
          <a class="nav-link" href="{home_url}" target="_blank" rel="noreferrer">Main Site</a>
          <a class="nav-link" href="#pending">Pending</a>
        </nav>
      </div>
    </header>
    <main>
      {body}
    </main>
    <script>
      const paperInput = document.querySelector('input[name="paper"]');
      const titleInput = document.querySelector('input[name="title"]');
      const authorsInput = document.querySelector('textarea[name="authors"]');
      const abstractInput = document.querySelector('textarea[name="abstract"]');
      const yearInput = document.querySelector('input[name="year"]');

      async function parseSelectedPaper(file) {{
        const formData = new FormData();
        formData.append('paper', file);
        const response = await fetch('/parse', {{
          method: 'POST',
          body: formData,
        }});
        const payload = await response.json();
        if (!payload.ok) {{
          throw new Error(payload.error || 'Failed to parse PDF.');
        }}
        return payload.data || {{}};
      }}

      if (paperInput) {{
        paperInput.addEventListener('change', async () => {{
          const file = paperInput.files && paperInput.files[0];
          if (!file) return;
          try {{
            const parsed = await parseSelectedPaper(file);
            if (titleInput) {{
              titleInput.value = parsed.title || '';
            }}
            if (authorsInput) {{
              authorsInput.value = Array.isArray(parsed.authors) ? parsed.authors.join('\\n') : '';
            }}
            if (abstractInput) {{
              abstractInput.value = parsed.abstract || '';
            }}
            if (yearInput && parsed.year) {{
              yearInput.value = parsed.year;
            }}
          }} catch (error) {{
            console.error(error);
            alert('PDF 解析失败：' + error.message);
          }}
        }});
      }}
    </script>
  </body>
</html>""".encode("utf-8")


def _redirect(start_response, location: str) -> list[bytes]:
    start_response("303 See Other", [("Location", location)])
    return [b""]


def _build_datalist(datalist_id: str, options: list[str]) -> str:
    values = [value.strip() for value in options if value and value.strip()]
    deduped = list(dict.fromkeys(values))
    if not deduped:
        return ""
    option_html = "".join(f"<option value='{html.escape(value)}'></option>" for value in deduped)
    return f"<datalist id='{html.escape(datalist_id)}'>{option_html}</datalist>"


def _load_form_options() -> dict[str, list[str]]:
    publications = load_json(CONTENT_DIR / "publications.json", [])
    projects = load_json(CONTENT_DIR / "projects.json", [])

    current_year = 2026
    venue_options = [str(item.get("venue", "")).strip() for item in publications]
    research_area_options = [str(item.get("research_area", "")).strip() for item in publications]
    project_options = [str(item.get("slug", "")).strip() for item in projects]
    year_options = [str(year) for year in range(current_year + 1, current_year - 6, -1)]

    return {
        "status": ["accepted", "camera-ready", "published", "arXiv", "under review"],
        "venue": venue_options + [
            "SOSP 2025",
            "OSDI 2026",
            "NSDI 2026",
            "ATC 2026",
            "EuroSys 2026",
            "ASPLOS 2026",
            "MLSys 2026",
            "ICML 2026",
            "NeurIPS 2026",
            "ICLR 2026",
            "SC 2026",
            "VLDB 2026",
            "SIGMOD 2026",
            "FAST 2026",
            "MICRO 2026",
            "HPCA 2026",
            "ISCA 2026",
            "ICCD 2026",
            "TPDS",
        ],
        "month": [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
        "year": year_options,
        "research_area": research_area_options + [
            "distributed machine learning",
            "storage systems",
            "distributed databases",
            "large language models",
            "graph neural networks",
            "parallel and distributed intelligent computing",
        ],
        "project_slug": project_options,
    }


def _main_site_url() -> str:
    site = load_json(CONTENT_DIR / "site.json", {})
    return str(site.get("base_url") or "http://127.0.0.1:8001").rstrip("/") + "/"


def _publish_from_submission(temp_dir: Path) -> tuple[bool, str, str]:
    try:
        record, _ = create_record_from_submission_dir(temp_dir)
        slug = publish_record(record, remove_from_pending=True)
        rebuild_site()
        return True, f"Published: {slug}", slug
    except Exception as exc:
        return False, str(exc), ""


def _save_submission_from_form(form: cgi.FieldStorage) -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="publication_submission_"))
    pdf_item = form["paper"]
    meta = {
        "status": form.getfirst("status", ""),
        "venue": form.getfirst("venue", ""),
        "month": form.getfirst("month", ""),
        "year": int(form.getfirst("year")) if form.getfirst("year") else None,
        "research_area": form.getfirst("research_area", ""),
        "project_slug": form.getfirst("project_slug", ""),
        "code_url": form.getfirst("code_url", ""),
        "award": form.getfirst("award", ""),
        "title": form.getfirst("title", ""),
        "abstract": form.getfirst("abstract", ""),
        "authors": [item.strip() for item in form.getfirst("authors", "").split("\n") if item.strip()],
        "tags": [item.strip() for item in form.getfirst("tags", "").split(",") if item.strip()],
    }
    (temp_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    with (temp_dir / "paper.pdf").open("wb") as handle:
        shutil.copyfileobj(pdf_item.file, handle)
    return temp_dir


def _save_parse_request_from_form(form: cgi.FieldStorage) -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="publication_parse_"))
    pdf_item = form["paper"]
    with (temp_dir / "paper.pdf").open("wb") as handle:
        shutil.copyfileobj(pdf_item.file, handle)
    return temp_dir


def app(environ, start_response):
    path = environ.get("PATH_INFO", "/")
    query = urllib.parse.parse_qs(environ.get("QUERY_STRING", ""))

    if path == "/" and environ["REQUEST_METHOD"] == "GET":
        pending = load_pending_publications()
        form_options = _load_form_options()
        message = query.get("message", [""])[0]
        highlight_slug = query.get("slug", [""])[0]
        message_class = "flash--ok" if message.startswith("OK:") else "flash--error"
        detail_url = ""
        if highlight_slug:
            detail_url = _main_site_url() + f"publications/{highlight_slug}/"
        flash_actions = ""
        if message and message.startswith("OK:") and highlight_slug:
            flash_actions = (
                f"<div class='flash__actions'>"
                f"<a class='action-link action-link--primary' href='{html.escape(detail_url)}' target='_blank' rel='noreferrer'>Open publication</a>"
                f"<a class='action-link' href='{html.escape(_main_site_url())}' target='_blank' rel='noreferrer'>Open homepage</a>"
                f"</div>"
            )
        body = f"""
        <div class="shell">
          <section class="hero">
            <div class="hero__card">
              <p class="hero__eyebrow">Publication Portal</p>
              <h1>Submit new papers for the lab site.</h1>
              <p class="hero__summary">Choose a PDF, let the portal prefill the metadata, review the extracted fields, and then publish the paper to the main site.</p>
            </div>
            <aside class="hero__card hero__aside">
              <p class="section-eyebrow">Workflow</p>
              <h3>Review before publish</h3>
              <ul>
                <li>Select a PDF and let the portal extract the title, authors, abstract, and year.</li>
                <li>Confirm the required fields, then publish directly to the site.</li>
                <li>If parsing looks wrong, edit the override fields before submitting.</li>
              </ul>
            </aside>
          </section>
          {f"<div class='flash {message_class}'><strong>{html.escape(message)}</strong>{flash_actions}</div>" if message else ""}
        </div>
        <div class="shell">
        <form method="post" action="/submit" enctype="multipart/form-data">
          <div class="section-head">
            <div>
              <p class="section-eyebrow">Submission</p>
              <h2>Submit a paper</h2>
            </div>
          </div>
          <p class="form-note">Fields marked with <span class="required-pill">Required</span> must be confirmed by the submitter. Fields marked with <span class="optional-pill">Optional</span> are metadata overrides or site-specific additions.</p>
          <label><span class="field-label">PDF <span class="required-pill">Required</span></span><input type="file" name="paper" accept="application/pdf" required /></label>
          <div class="row">
            <label><span class="field-label">Status <span class="required-pill">Required</span></span><input type="text" name="status" placeholder="accepted" list="status-options" required /></label>
            <label><span class="field-label">Venue <span class="required-pill">Required</span></span><input type="text" name="venue" placeholder="SOSP 2025" list="venue-options" required /></label>
          </div>
          <div class="row">
            <label><span class="field-label">Month <span class="optional-pill">Optional</span></span><input type="text" name="month" placeholder="October" list="month-options" /></label>
            <label><span class="field-label">Year <span class="required-pill">Required</span></span><input type="text" name="year" placeholder="2025" list="year-options" required /></label>
          </div>
          <label><span class="field-label">Research area <span class="required-pill">Required</span></span><input type="text" name="research_area" placeholder="storage systems" list="research-area-options" required /></label>
          <div class="row">
            <label><span class="field-label">Project slug <span class="optional-pill">Optional</span></span><input type="text" name="project_slug" list="project-slug-options" /></label>
            <label><span class="field-label">Code URL <span class="optional-pill">Optional</span></span><input type="text" name="code_url" /></label>
          </div>
          <label><span class="field-label">Award <span class="optional-pill">Optional</span></span><input type="text" name="award" /></label>
          <label><span class="field-label">Title override <span class="optional-pill">Optional</span></span><input type="text" name="title" /></label>
          <label><span class="field-label">Authors override, one per line <span class="optional-pill">Optional</span></span><textarea name="authors" rows="5"></textarea></label>
          <label><span class="field-label">Abstract override <span class="optional-pill">Optional</span></span><textarea name="abstract" rows="8"></textarea></label>
          <label><span class="field-label">Tags override, comma separated <span class="optional-pill">Optional</span></span><input type="text" name="tags" /></label>
          <div class="submit-row">
            <p class="muted">Selecting a PDF will auto-parse its metadata into the override fields below. After you review and confirm them, submit will publish the paper directly to the main site and rebuild the homepage.</p>
            <button type="submit">Publish to site</button>
          </div>
        </form>
        {_build_datalist("status-options", form_options["status"])}
        {_build_datalist("venue-options", form_options["venue"])}
        {_build_datalist("month-options", form_options["month"])}
        {_build_datalist("year-options", form_options["year"])}
        {_build_datalist("research-area-options", form_options["research_area"])}
        {_build_datalist("project-slug-options", form_options["project_slug"])}
        <div class="card" id="pending">
          <div class="section-head">
            <div>
              <p class="section-eyebrow">Queue</p>
              <h2>Pending entries</h2>
            </div>
          </div>
          <div class="pending-list">
            {"".join(f"<div class='pending-item {'is-highlighted' if item.get('slug','') == highlight_slug else ''}'><div><strong>{html.escape(item.get('slug',''))}</strong><p>{html.escape(item.get('title',''))}</p></div><span class='muted'>Legacy pending</span></div>" for item in pending) or "<p class='empty-state'>No pending publications yet.</p>"}
          </div>
        </div>
        </div>
        """
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [_html_page("Publication Portal", body)]

    if path == "/parse" and environ["REQUEST_METHOD"] == "POST":
        form = cgi.FieldStorage(fp=environ["wsgi.input"], environ=environ, keep_blank_values=True)
        if "paper" not in form:
            start_response("400 Bad Request", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"ok": False, "error": "Missing paper field"}).encode("utf-8")]
        temp_dir = _save_parse_request_from_form(form)
        try:
            payload = parse_preview(temp_dir / "paper.pdf")
            start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"ok": True, "data": payload}, ensure_ascii=False).encode("utf-8")]
        except Exception as exc:
            start_response("500 Internal Server Error", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False).encode("utf-8")]

    if path == "/submit" and environ["REQUEST_METHOD"] == "POST":
        form = cgi.FieldStorage(fp=environ["wsgi.input"], environ=environ, keep_blank_values=True)
        temp_dir = _save_submission_from_form(form)
        ok, message, slug = _publish_from_submission(temp_dir)
        location = "/?message=" + urllib.parse.quote(("OK: " if ok else "ERROR: ") + message)
        if slug:
            location += "&slug=" + urllib.parse.quote(slug)
        location += "#pending"
        return _redirect(start_response, location)

    start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
    return [b"Not found"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve a local publication submission portal.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8123)
    args = parser.parse_args()
    with make_server(args.host, args.port, app) as server:
        print(f"Publication portal running on http://{args.host}:{args.port}")
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
