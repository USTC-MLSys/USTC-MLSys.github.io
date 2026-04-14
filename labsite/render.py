from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html import escape
from typing import Any


@dataclass
class RenderedPage:
    path: str
    title: str
    description: str
    current_section: str
    page_kind: str
    content: str


def normalize_base_path(value: str | None) -> str:
    if not value or value == "/":
        return "/"
    return f"/{value.strip('/')}/"


def slug_token(value: str) -> str:
    return "-".join(value.lower().replace("/", " ").replace("&", " ").split())


def is_external(url: str) -> bool:
    return url.startswith(("http://", "https://", "mailto:"))


def resolve_url(base_path: str, url: str) -> str:
    if not url:
        return base_path
    if is_external(url) or url.startswith("#"):
        return url
    clean = url.lstrip("/")
    if base_path == "/":
        return f"/{clean}" if clean else "/"
    return f"{base_path}{clean}" if clean else base_path


def external_attrs(url: str) -> str:
    return ' target="_blank" rel="noreferrer"' if url.startswith(("http://", "https://")) else ""


def h(value: Any) -> str:
    return escape(str(value), quote=True)


def format_date(value: str) -> str:
    parsed = datetime.strptime(value, "%Y-%m-%d")
    return parsed.strftime("%B %d, %Y")


def join_classes(*classes: str) -> str:
    return " ".join(part for part in classes if part)


def pick_by_slugs(items: list[dict[str, Any]], slugs: list[str]) -> list[dict[str, Any]]:
    index = {item["slug"]: item for item in items}
    return [index[slug] for slug in slugs if slug in index]


def render_tag_list(tags: list[str], extra_class: str = "") -> str:
    return "".join(
        f'<span class="{join_classes("chip", extra_class)}">{h(tag)}</span>'
        for tag in tags
    )


def render_action_links(base_path: str, links: dict[str, str], compact: bool = False) -> str:
    label_map = {
        "github": "GitHub",
        "demo": "Demo",
        "docs": "Docs",
        "publication": "Publication",
        "pdf": "PDF",
        "pdf_url": "PDF",
        "code": "Code",
        "code_url": "Code",
        "homepage": "Homepage",
        "email": "Email",
    }
    classes = join_classes("button", "button--ghost", "button--compact" if compact else "")
    rendered: list[str] = []
    for key, url in links.items():
        if not url:
            continue
        label = label_map.get(key, key.replace("_", " ").title())
        resolved = resolve_url(base_path, url)
        rendered.append(f'<a class="{classes}" href="{resolved}"{external_attrs(resolved)}>{h(label)}</a>')
    return "".join(rendered)


def render_metric_items(metrics: list[dict[str, str]], item_class: str = "metric-item") -> str:
    parts: list[str] = []
    for metric in metrics:
        parts.append(
            f"""
            <div class="{item_class}">
              <span class="{item_class}__value">{h(metric["value"])}</span>
              <span class="{item_class}__label">{h(metric["label"])}</span>
            </div>
            """
        )
    return "".join(parts)


def render_content_blocks(base_path: str, blocks: list[dict[str, Any]]) -> str:
    rendered: list[str] = []
    for block in blocks:
        block_title = block.get("title")
        block_id = block.get("id")
        id_attr = f' id="{h(block_id)}"' if block_id else ""
        heading = f'<h2 class="prose__heading"{id_attr}>{h(block_title)}</h2>' if block_title else ""
        block_type = block.get("type")
        if block_type == "html":
            rendered.append(block.get("html", ""))
            continue
        if block_type == "paragraph":
            rendered.append(
                f"""
                <section class="prose-block"{id_attr}>
                  {heading}
                  <p>{h(block.get("text", ""))}</p>
                </section>
                """
            )
        elif block_type == "list":
            items = "".join(f"<li>{h(item)}</li>" for item in block.get("items", []))
            rendered.append(
                f"""
                <section class="prose-block"{id_attr}>
                  {heading}
                  <ul>{items}</ul>
                </section>
                """
            )
        elif block_type == "quote":
            rendered.append(
                f"""
                <section class="prose-block">
                  {heading}
                  <blockquote>{h(block.get("text", ""))}</blockquote>
                </section>
                """
            )
        elif block_type == "image":
            src = resolve_url(base_path, block.get("src", ""))
            alt = block.get("alt", block.get("title", ""))
            caption = block.get("caption", "")
            rendered.append(
                f"""
                <figure class="prose-figure">
                  {heading}
                  <img src="{h(src)}" alt="{h(alt)}" loading="lazy" />
                  {f'<figcaption>{h(caption)}</figcaption>' if caption else ''}
                </figure>
                """
            )
        else:
            rendered.append(f"<p>{h(block)}</p>")
    return "".join(rendered)


def render_section_heading(eyebrow: str, title: str, description: str, action: str = "") -> str:
    return f"""
    <div class="section-heading" data-reveal>
      <div>
        <p class="section-heading__eyebrow">{h(eyebrow)}</p>
        <h2 class="section-heading__title">{h(title)}</h2>
      </div>
      <p class="section-heading__description">{h(description)}</p>
      {action}
    </div>
    """


class SiteRenderer:
    def __init__(self, content: dict[str, Any], base_path: str) -> None:
        self.site = content["site"]
        self.projects = content["projects"]
        self.blog = content["blog"]
        self.publications = content["publications"]
        self.news = content["news"]
        self.team = content["team"]
        self.base_path = normalize_base_path(base_path)
        self.project_index = {item["slug"]: item for item in self.projects}
        self.blog_index = {item["slug"]: item for item in self.blog}
        self.publication_index = {item["slug"]: item for item in self.publications}
        self.news_index = {item["slug"]: item for item in self.news}

    def nav_items(self) -> list[tuple[str, str, str]]:
        items: list[tuple[str, str, str]] = []
        # Always expose the Projects nav item so the section can be populated later
        items.append(("projects/", "Projects", "projects"))
        if self.blog:
            items.append(("blog/", "Blog", "blog"))
        if self.publications:
            items.append(("publications/", "Publications", "publications"))
        if self.team:
            items.append(("team/", "Team", "team"))
        return items

    def meta_parts(self, *parts: Any) -> str:
        clean = [str(part) for part in parts if part not in (None, "", [])]
        return " / ".join(clean)

    def publication_date_label(self, publication: dict[str, Any]) -> str:
        return " ".join(part for part in [str(publication.get("month", "")).strip(), str(publication.get("year", "")).strip()] if part)

    def generate_pages(self) -> list[RenderedPage]:
        # Always generate a projects page (may be empty) so the nav link is valid.
        pages = [self.home_page(), self.not_found_page(), self.projects_page()]
        if self.blog:
            pages.append(self.blog_page())
        if self.publications:
          pages.append(self.publications_page())
        if self.team:
          pages.append(self.team_page())
        pages.extend(self.project_detail_pages())
        pages.extend(self.blog_detail_pages())
        pages.extend(self.publication_detail_pages())
        return pages

    def page_shell(
        self,
        *,
        title: str,
        description: str,
        current_section: str,
        page_kind: str,
        body: str,
    ) -> str:
        lab_name = self.site["lab_name"]
        brand_mark = "".join(part[0] for part in lab_name.split()[:2]).upper() or "LB"
        page_title = lab_name if title == lab_name else f"{title} | {lab_name}"
        description_text = description or self.site["description"]
        canonical = self.site.get("base_url", "").rstrip("/")
        nav_items = self.nav_items()
        nav_links = "".join(
            f'<a class="{join_classes("site-nav__link", "is-active" if section == current_section else "")}" '
            f'href="{resolve_url(self.base_path, href)}">{h(label)}</a>'
            for href, label, section in nav_items
        )
        collaboration_links = self.site.get("collaboration", {}).get("links", [])
        collaboration_cta = ""
        if collaboration_links:
            collaboration_url = collaboration_links[0]["url"]
            collaboration_cta = (
                f'<a class="button button--primary button--compact site-nav__cta" '
                f'href="{resolve_url(self.base_path, collaboration_url)}"'
                f'{external_attrs(resolve_url(self.base_path, collaboration_url))}>'
                f"{h(collaboration_links[0]['label'])}</a>"
            )
        footer_targets = [(href, label) for href, label, _ in nav_items]
        if self.site.get("github"):
            footer_targets.append((self.site["github"], "GitHub"))
        if self.site.get("email"):
            footer_targets.append((f"mailto:{self.site['email']}", self.site["email"]))
        footer_links = "".join(
            f'<a href="{resolve_url(self.base_path, href)}"{external_attrs(resolve_url(self.base_path, href))}>{h(label)}</a>'
            for href, label in footer_targets
        )
        footer_location = f'<p>{h(self.site.get("location", ""))}</p>' if self.site.get("location") else ""
        footer_links_html = f'<div class="site-footer__links">{footer_links}</div>' if footer_links else ""
        canonical_tag = ""
        if canonical:
            canonical_path = "" if page_kind == "home" else page_kind.strip("/")
            full = f"{canonical}{self.base_path.rstrip('/')}"
            if canonical_path:
                full = f"{full}/{canonical_path}/"
            else:
                full = f"{full}/"
            canonical_tag = f'<link rel="canonical" href="{h(full)}" />'
        return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{h(page_title)}</title>
    <meta name="description" content="{h(description_text)}" />
    <meta name="theme-color" content="#121417" />
    <meta property="og:title" content="{h(page_title)}" />
    <meta property="og:description" content="{h(description_text)}" />
    <meta property="og:type" content="website" />
    <link rel="icon" href="{resolve_url(self.base_path, 'assets/img/favicon.svg')}" type="image/svg+xml" />
    <link rel="manifest" href="{resolve_url(self.base_path, 'site.webmanifest')}" />
    <script>document.documentElement.classList.add('js');</script>
    <link rel="stylesheet" href="{resolve_url(self.base_path, 'assets/css/styles.css')}" />
    {canonical_tag}
  </head>
  <body class="page page--{h(page_kind)}">
    <div class="page-glow page-glow--teal" aria-hidden="true"></div>
    <div class="page-glow page-glow--copper" aria-hidden="true"></div>
    <header class="site-header" data-site-header>
      <div class="shell site-header__inner">
        <a class="brand" href="{resolve_url(self.base_path, '')}">
          <span class="brand__mark">{h(brand_mark[:2])}</span>
          <span class="brand__text">
            <strong>{h(self.site["lab_name"])}</strong>
            <small>{h(self.site["tagline"])}</small>
          </span>
        </a>
        <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav" data-menu-toggle>
          <span></span>
          <span></span>
        </button>
        <div class="site-search">
          <input type="search" class="site-search__input" placeholder="Search..." data-search-input aria-label="Search" />
          <div class="site-search__results" data-search-results></div>
        </div>
        <nav class="site-nav" id="site-nav" data-menu-panel>
          {nav_links}
          {collaboration_cta}
        </nav>
      </div>
    </header>
    <main class="site-main">
      {body}
    </main>
    <footer class="site-footer">
        <div class="shell site-footer__inner">
        <div class="site-footer__intro">
          <p class="site-footer__eyebrow">{h(self.site.get("tagline", ""))}</p>
          <h2>{h(self.site["lab_name"])}</h2>
          <p>{h(self.site["description"])}</p>
        </div>
        <div class="site-footer__meta">
          {footer_location}
          {footer_links_html}
        </div>
      </div>
    </footer>
    <script defer src="{resolve_url(self.base_path, 'assets/js/site.js')}"></script>
  </body>
</html>
"""

    def home_page(self) -> RenderedPage:
        hero = self.site["hero"]
        announcement = self.site.get("announcement")
        announcement_html = ""
        if announcement:
            announcement_html = (
                f'<a class="announcement shell" href="{resolve_url(self.base_path, announcement["url"])}">'
                f'<span class="announcement__label">{h(announcement["label"])}</span>'
                f'<span class="announcement__text">{h(announcement["text"])}</span>'
                "</a>"
            )
        hero_stats = "".join(
            f"""
            <article class="metric-card" data-reveal>
              <span class="metric-card__value">{h(item["value"])}</span>
              <span class="metric-card__label">{h(item["label"])}</span>
            </article>
            """
            for item in self.site.get("stats", [])
        )
        buttons: list[str] = []
        primary_cta = hero.get("primary_cta")
        secondary_cta = hero.get("secondary_cta")
        tertiary_cta = hero.get("tertiary_cta")
        if primary_cta:
            buttons.append(
                f'<a class="button button--primary" href="{resolve_url(self.base_path, primary_cta["url"])}">{h(primary_cta["label"])}</a>'
            )
        if secondary_cta:
            buttons.append(
                f'<a class="button button--ghost" href="{resolve_url(self.base_path, secondary_cta["url"])}">{h(secondary_cta["label"])}</a>'
            )
        if tertiary_cta:
            buttons.append(
                f'<a class="button button--ghost" href="{resolve_url(self.base_path, tertiary_cta["url"])}">{h(tertiary_cta["label"])}</a>'
            )
        hero_buttons = f'<div class="hero__actions" data-reveal>{"".join(buttons)}</div>' if buttons else ""
        featured_projects = pick_by_slugs(self.projects, self.site.get("featured_project_slugs", [])) or self.projects[:3]
        featured_blog = pick_by_slugs(self.blog, self.site.get("featured_project_slugs", [])) or self.blog[:3]
        featured_publications = pick_by_slugs(self.publications, self.site.get("featured_publication_slugs", [])) or self.publications[:3]
        spotlight_cards: list[str] = []
        if featured_projects:
            spotlight_cards.append(self.render_project_card(featured_projects[0], compact=True))
        if featured_blog:
            spotlight_cards.append(self.render_blog_card(featured_blog[0], compact=True))
        if featured_publications:
            spotlight_cards.append(self.render_publication_card(featured_publications[0], compact=True))
        research_cards = "".join(
            f"""
            <article class="theme-card" data-reveal>
              <div class="theme-card__eyebrow">{h(' / '.join(area['keywords']))}</div>
              <h3>{h(area["name"])}</h3>
              <p>{h(area["summary"])}</p>
            </article>
            """
            for area in self.site.get("research_areas", [])
        )
        principles = "".join(
            f"""
            <article class="principle-card" data-reveal>
              <h3>{h(item["title"])}</h3>
              <p>{h(item["summary"])}</p>
            </article>
            """
            for item in self.site.get("principles", [])
        )
        collaboration_links = "".join(
            f'<a class="button button--ghost" href="{resolve_url(self.base_path, link["url"])}"{external_attrs(resolve_url(self.base_path, link["url"]))}>{h(link["label"])}</a>'
            for link in self.site.get("collaboration", {}).get("links", [])
        )
        hero_metrics = f'<div class="hero__metrics">{hero_stats}</div>' if hero_stats else ""
        
        # Build dynamic timeline with latest items (auto-updates from all content)
        timeline_html = self.render_hero_timeline(3)
        
        body_parts = [
            announcement_html,
            f"""
        <section class="hero">
          <div class="shell hero__grid">
            <div class="hero__copy">
              <p class="hero__eyebrow" data-reveal>{h(hero["eyebrow"])}</p>
              <h1 class="hero__title" data-reveal>{h(hero["headline"])}</h1>
              <p class="hero__summary" data-reveal>{h(hero["subheadline"])}</p>
              {hero_buttons}
              {hero_metrics}
            </div>
            <div class="hero__visual" data-reveal>
              {timeline_html}
            </div>
          </div>
        </section>
        """,
        ]
        if spotlight_cards:
            body_parts.append(
                f"""
        <section class="section section--spotlight">
          <div class="shell">
            {render_section_heading('Featured', 'Latest from the lab.', '')}
            <div class="spotlight-grid">
              {''.join(spotlight_cards)}
            </div>
          </div>
        </section>
        """
            )
        if self.site.get("research_areas"):
            body_parts.append(
                f"""
        <section class="section">
          <div class="shell">
            {render_section_heading('Research Areas', 'What we work on.', '')}
            <div class="theme-grid">
              {research_cards}
            </div>
          </div>
        </section>
        """
            )
        if featured_blog:
            body_parts.append(
                f"""
        <section class="section">
          <div class="shell">
            {render_section_heading('Blog', 'Technical writeups.', '', f'<a class="section-heading__action" href="{resolve_url(self.base_path, "blog/")}">All posts</a>')}
            <div class="card-grid card-grid--projects">
              {''.join(self.render_blog_card(post) for post in featured_blog)}
            </div>
          </div>
        </section>
        """
            )
        if featured_projects:
            body_parts.append(
                f"""
        <section class="section">
          <div class="shell">
            {render_section_heading('Projects', 'Research projects.', '', f'<a class="section-heading__action" href="{resolve_url(self.base_path, "projects/")}">View all projects</a>')}
            <div class="card-grid card-grid--projects">
              {''.join(self.render_project_card(project) for project in featured_projects)}
            </div>
          </div>
        </section>
        """
            )
        if featured_publications:
            body_parts.append(
                f"""
        <section class="section">
          <div class="shell">
            {render_section_heading('Publications', 'Research publications and award-winning publications from the lab.', 'Peer-reviewed work on distributed training, tensor core optimization, and efficient AI systems published at top-tier venues.', f'<a class="section-heading__action" href="{resolve_url(self.base_path, "publications/")}">View all publications</a>')}
            <div class="timeline-stack">
              {''.join(self.render_publication_card(pub) for pub in featured_publications)}
            </div>
          </div>
        </section>
        """
            )
        if principles or collaboration_links:
            body_parts.append(
                f"""
        <section class="section section--contrast">
          <div class="shell section-split">
            <div>
              {render_section_heading('', '', '')}
              <div class="principle-grid">
                {principles}
              </div>
            </div>
            <aside class="collaboration-panel" data-reveal>
              <p class="collaboration-panel__eyebrow">Links</p>
              <h3>{h(self.site.get('collaboration', {}).get('title', 'Public links'))}</h3>
              <p>{h(self.site.get('collaboration', {}).get('summary', ''))}</p>
              <div class="collaboration-panel__actions">{collaboration_links}</div>
            </aside>
          </div>
        </section>
        """
            )
        body = "".join(body_parts)
        return RenderedPage(
            path="index.html",
            title=self.site["lab_name"],
            description=self.site["description"],
            current_section="home",
            page_kind="home",
            content=body,
        )

    def projects_page(self) -> RenderedPage:
        cards = "".join(self.render_project_card(project) for project in self.projects)
        body = f"""
        {self.render_page_intro('Projects', 'Systems for distributed LLM training and efficient AI infrastructure.', '')}
        <section class="section">
          <div class="shell">
            <div class="card-grid card-grid--projects" data-filter-container>
              {cards}
            </div>
          </div>
        </section>
        """
        return RenderedPage(
            path="projects/index.html",
            title="Projects",
            description="Research projects from MLSys Lab.",
            current_section="projects",
            page_kind="projects",
            content=body,
        )

    def blog_page(self) -> RenderedPage:
        cards = "".join(self.render_blog_card(post) for post in self.blog)
        body = f"""
        {self.render_page_intro('Blogs', 'Technical notes on systems, publications, and implementation details.', '')}
        <section class="section">
          <div class="shell">
            <div class="card-grid card-grid--projects">
              {cards}
            </div>
          </div>
        </section>
        """
        return RenderedPage(
            path="blog/index.html",
            title="Blog",
            description="Technical notes and research commentary from MLSys Lab.",
            current_section="blog",
            page_kind="blog",
            content=body,
        )

    def publications_page(self) -> RenderedPage:
        grouped: dict[int, list[dict[str, Any]]] = {}
        for pub in self.publications:
            grouped.setdefault(pub["year"], []).append(pub)
        year_sections = []
        for year in sorted(grouped, reverse=True):
            items = "".join(self.render_publication_card(pub) for pub in grouped[year])
            year_sections.append(
                f"""
                <section class="timeline-group">
                  <div class="timeline-group__year" data-reveal>{h(year)}</div>
                  <div class="timeline-group__items">
                    {items}
                  </div>
                </section>
                """
            )
        body = f"""
        {self.render_page_intro('Publications', 'Research on distributed training, tensor core optimization, and efficient AI systems.', '')}
        <section class="section">
          <div class="shell">
            <div class="timeline-stack">
              {''.join(year_sections)}
            </div>
          </div>
        </section>
        """
        return RenderedPage(
            path="publications/index.html",
            title="Publications",
            description="Selected recent publications from the lab.",
            current_section="publications",
            page_kind="publications",
            content=body,
        )

    def team_page(self) -> RenderedPage:
        groups = [("faculty", "Faculty"), ("postdoc", "Postdocs"), ("phd", "PhD students"), ("master", "Master's students"), ("engineer", "Research engineers"), ("alumni", "Alumni")]
        group_sections: list[str] = []
        for key, label in groups:
            members = [member for member in self.team if member["group"] == key]
            if not members:
                continue
            cards = "".join(self.render_team_card(member) for member in members)
            group_sections.append(
                f"""
                <section class="team-section">
                  <div class="team-section__heading" data-reveal>
                    <p>{h(label)}</p>
                  </div>
                  <div class="team-grid">
                    {cards}
                  </div>
                </section>
                """
            )
        body = f"""
        {self.render_page_intro('Team', 'Our people.', '')}
        <section class="section">
          <div class="shell">
            {''.join(group_sections)}
          </div>
        </section>
        """
        return RenderedPage(
            path="team/index.html",
            title="Team",
            description="Current team information included on the site.",
            current_section="team",
            page_kind="team",
            content=body,
        )

    def project_detail_pages(self) -> list[RenderedPage]:
        pages = []
        for project in self.projects:
            related_publications = [pub for pub in self.publications if pub.get("project_slug") == project["slug"]]
            side_metrics = render_metric_items(project.get("metrics", []), item_class="fact-item")
            side_links = render_action_links(self.base_path, project.get("links", {}), compact=False)
            related_cards = "".join(self.render_publication_card(item, compact=True) for item in related_publications[:2])
            sidebar_panels: list[str] = []
            if side_metrics:
                sidebar_panels.append(
                    f"""
                  <div class="detail-sidebar__panel">
                    <p class="detail-sidebar__eyebrow">Project facts</p>
                    <div class="fact-list">{side_metrics}</div>
                  </div>
                    """
                )
            sidebar_panels.append(
                f"""
                  <div class="detail-sidebar__panel">
                    <p class="detail-sidebar__eyebrow">Related output</p>
                    <div class="detail-sidebar__stack">{related_cards or '<p class="muted">No related entries yet.</p>'}</div>
                  </div>
                """
            )
            body = f"""
            {self.render_detail_intro(
                title=project['title'],
                eyebrow=project.get('page_label', 'Project'),
                summary=project['description'],
                meta=self.meta_parts(project.get('category'), project.get('status'), project.get('year')),
                tags=project.get('tags', []),
                actions=side_links,
            )}
            <section class="section detail-section">
              <div class="shell detail-layout">
                <article class="detail-prose" data-reveal>
                  {render_content_blocks(self.base_path, project.get('content', []))}
                </article>
                <aside class="detail-sidebar" data-reveal>
                  {''.join(sidebar_panels)}
                </aside>
              </div>
            </section>
            """
            pages.append(
                RenderedPage(
                    path=f"projects/{project['slug']}/index.html",
                    title=project["title"],
                    description=project["summary"],
                    current_section="projects",
                    page_kind="project-detail",
                    content=body,
                )
            )
        return pages

    def extract_toc(self, content: list[dict[str, Any]]) -> list[tuple[str, str]]:
        """Extract table of contents from content blocks."""
        toc = []
        for block in content:
            if block.get("type") in ("paragraph", "list") and block.get("title"):
                anchor = block["title"].lower().replace(" ", "-").replace("/", "")
                toc.append((anchor, block["title"]))
            elif block.get("type") == "image" and block.get("title"):
                anchor = block["title"].lower().replace(" ", "-").replace("/", "")
                toc.append((anchor, block["title"]))
        return toc

    def render_toc(self, toc: list[tuple[str, str]]) -> str:
        """Render table of contents HTML."""
        if not toc:
            return ""
        items = "".join(
            f'<li><a href="#{anchor}" data-toc-link>{h(title)}</a></li>'
            for anchor, title in toc
        )
        return f"""
            <nav class="toc-nav" data-toc>
                <p class="toc-nav__eyebrow">Contents</p>
                <ul class="toc-nav__list">{items}</ul>
            </nav>
        """

    def blog_detail_pages(self) -> list[RenderedPage]:
        pages = []
        for post in self.blog:
            side_links = render_action_links(self.base_path, post.get("links", {}), compact=False)
            toc = self.extract_toc(post.get("content", []))
            toc_html = self.render_toc(toc)
            
            # Build meta with Author first
            meta_parts = []
            if post.get("author"):
                meta_parts.append(post['author'])
            if post.get("date"):
                meta_parts.append(format_date(post["date"]))
            meta = "        ".join(meta_parts) if meta_parts else ""
            
            # Add IDs to content blocks for TOC linking
            content_with_ids = []
            for block in post.get("content", []):
                block_copy = dict(block)
                if block.get("type") in ("paragraph", "list", "image") and block.get("title"):
                    anchor = block["title"].lower().replace(" ", "-").replace("/", "")
                    block_copy["id"] = anchor
                content_with_ids.append(block_copy)
            
            sidebar_panels: list[str] = []
            if toc_html:
                sidebar_panels.append(toc_html)
            
            body = f"""
            {self.render_detail_intro(
                title=post['title'],
                eyebrow=post.get('page_label', 'Blog'),
                summary=post['description'],
                meta=meta,
                tags=post.get('tags', []),
                actions=side_links,
            )}
            <section class="section detail-section">
              <div class="shell detail-layout">
                <article class="detail-prose" data-reveal>
                  {render_content_blocks(self.base_path, content_with_ids)}
                </article>
                <aside class="detail-sidebar" data-reveal>
                  {''.join(sidebar_panels)}
                </aside>
              </div>
            </section>
            """
            pages.append(
                RenderedPage(
                    path=f"blog/{post['slug']}/index.html",
                    title=post["title"],
                    description=post["summary"],
                    current_section="blog",
                    page_kind="blog-detail",
                    content=body,
                )
            )
        return pages

    def publication_detail_pages(self) -> list[RenderedPage]:
        pages = []
        for pub in self.publications:
            project = self.project_index.get(pub.get("project_slug", ""))
            related_news = [item for item in self.news if pub["slug"] in item.get("related_paper_slugs", [])]
            actions = render_action_links(
                self.base_path,
                {
                    "pdf": pub.get("pdf_url", ""),
                    "code": pub.get("code_url", ""),
                },
                compact=False,
            )
            meta = self.meta_parts(pub["venue"], self.publication_date_label(pub))
            if pub.get("award"):
                meta = f"{meta} / {pub['award']}"
            related = ""
            if project:
                related += self.render_project_card(project, compact=True)
            related += "".join(self.render_news_card(item, compact=True) for item in related_news[:2])
            body = f"""
            {self.render_detail_intro(
                title=pub['title'],
                eyebrow='Publication',
                summary=pub['abstract'],
                meta=meta,
                tags=pub['tags'],
                actions=actions,
            )}
            <section class="section detail-section">
              <div class="shell detail-layout">
                <article class="detail-prose" data-reveal>
                  <section class="prose-block">
                    <h2 class="prose__heading">Authors</h2>
                    <p>{h(', '.join(pub['authors']))}</p>
                  </section>
                  {render_content_blocks(self.base_path, pub.get('content', []))}
                </article>
                <aside class="detail-sidebar" data-reveal>
                  <div class="detail-sidebar__panel">
                    <p class="detail-sidebar__eyebrow">Research area</p>
                    <p>{h(pub['research_area'])}</p>
                  </div>
                  <div class="detail-sidebar__panel">
                    <p class="detail-sidebar__eyebrow">Related output</p>
                    <div class="detail-sidebar__stack">{related or '<p class="muted">No related entries on the site.</p>'}</div>
                  </div>
                </aside>
              </div>
            </section>
            """
            pages.append(
                RenderedPage(
                    path=f"publications/{pub['slug']}/index.html",
                    title=pub["title"],
                    description=pub["summary"],
                    current_section="publications",
                    page_kind="publication-detail",
                    content=body,
                )
            )
        return pages

    def not_found_page(self) -> RenderedPage:
        body = f"""
        <section class="page-intro page-intro--tight">
          <div class="shell">
            <p class="page-intro__eyebrow" data-reveal>Error 404</p>
            <h1 class="page-intro__title" data-reveal>Page not found.</h1>
            <p class="page-intro__summary" data-reveal>This page does not exist or may have moved.</p>
            <div class="page-intro__actions" data-reveal>
              <a class="button button--primary" href="{resolve_url(self.base_path, '')}">Go home</a>
              <a class="button button--ghost" href="{resolve_url(self.base_path, 'blog/')}">Browse blog</a>
            </div>
          </div>
        </section>
        """
        return RenderedPage(
            path="404.html",
            title="Page not found",
            description="The page you requested does not exist.",
            current_section="home",
            page_kind="404",
            content=body,
        )

    def render_page_intro(self, title: str, summary: str, description: str) -> str:
        return f"""
        <section class="page-intro">
          <div class="shell">
            <p class="page-intro__eyebrow" data-reveal>{h(self.site['tagline'])}</p>
            <h1 class="page-intro__title" data-reveal>{h(title)}</h1>
            <p class="page-intro__summary" data-reveal>{h(summary)}</p>
            <p class="page-intro__description" data-reveal>{h(description)}</p>
          </div>
        </section>
        """

    def render_detail_intro(self, *, title: str, eyebrow: str, summary: str, meta: str, tags: list[str], actions: str) -> str:
        meta_html = f'<div class="detail-hero__meta" data-reveal><span>{h(meta)}</span></div>' if meta else ""
        tags_html = f'<div class="detail-hero__tags" data-reveal>{render_tag_list(tags)}</div>' if tags else ""
        actions_html = f'<div class="detail-hero__actions" data-reveal>{actions}</div>' if actions else ""
        return f"""
        <section class="detail-hero">
          <div class="shell detail-hero__grid">
            <div>
              <p class="detail-hero__eyebrow" data-reveal>{h(eyebrow)}</p>
              <h1 class="detail-hero__title" data-reveal>{h(title)}</h1>
              <p class="detail-hero__summary" data-reveal>{h(summary)}</p>
              {meta_html}
              {tags_html}
              {actions_html}
            </div>
          </div>
        </section>
        """

    def render_project_card(self, project: dict[str, Any], compact: bool = False) -> str:
        tokens = [slug_token(project["category"]), slug_token(project["status"])]
        tokens.extend(slug_token(tag) for tag in project.get("tags", []))
        classes = join_classes("project-card", f"project-card--{project.get('tone', 'teal')}", "project-card--compact" if compact else "")
        metrics = render_metric_items(project.get("metrics", [])[:2] if compact else project.get("metrics", []))
        metrics_html = f'<div class="metric-strip">{metrics}</div>' if metrics else ""
        actions = render_action_links(self.base_path, project.get('links', {}), compact=True)
        actions_html = f'<div class="card-actions">{actions}</div>' if actions else ""
        return f"""
        <article class="{classes}" data-reveal data-filter-item data-filter-tags="{' '.join(tokens)}">
          <div class="card-kicker">
            <span>{h(project['category'])}</span>
            <span>{h(project['status'])}</span>
          </div>
          <h3 class="project-card__title"><a href="{resolve_url(self.base_path, f"projects/{project['slug']}/")}">{h(project['title'])}</a></h3>
          <p class="project-card__subtitle">{h(project['subtitle'])}</p>
          <p class="project-card__summary">{h(project['summary'])}</p>
          <div class="chip-row">{render_tag_list(project['tags'][:4])}</div>
          {metrics_html}
          {actions_html}
        </article>
        """

    def render_blog_card(self, post: dict[str, Any], compact: bool = False) -> str:
        tokens = [slug_token(tag) for tag in post.get("tags", [])]
        # 尝试从文章内容中找到第一张图片作为卡片右侧封面
        image_src = None
        image_alt = post.get('title', '')
        for block in post.get('content', []):
            if block.get('type') == 'image' and block.get('src'):
                image_src = resolve_url(self.base_path, block.get('src'))
                image_alt = block.get('alt') or block.get('title') or image_alt
                break

        classes = join_classes(
            "project-card",
            f"project-card--{post.get('tone', 'copper')}",
            "project-card--compact" if compact else "",
            "project-card--has-media" if image_src else "",
        )

        media_html = (
          f'<div class="project-card__media"><img src="{h(image_src)}" alt="{h(image_alt)}" loading="lazy"/>'
          f'</div>'
          if image_src
          else ""
        )

        return f"""
        <article class="{classes}" data-reveal data-filter-item data-filter-tags="{' '.join(tokens)}">
          <div>
            <div class="card-kicker">
              <span>{h(post.get('page_label', 'Blog'))}</span>
            </div>
            <h3 class="project-card__title"><a href="{resolve_url(self.base_path, f"blog/{post['slug']}/")}">{h(post['title'])}</a></h3>
            <p class="project-card__subtitle">{h(post.get('subtitle') or '')}</p>
            <p class="project-card__summary">{h(post.get('summary') or '')}</p>
            <div class="chip-row">{render_tag_list(post.get('tags', [])[:4])}</div>
          </div>
          {media_html}
        </article>
        """

    def render_publication_card(self, publication: dict[str, Any], compact: bool = False) -> str:
        award = f'<span class="publication-card__award">{h(publication["award"])}</span>' if publication.get("award") else ""
        # Determine accent color: gold for Best Publication, green for others
        accent_class = "publication-card--award" if publication.get("award") else "publication-card--venue"
        classes = join_classes("publication-card", accent_class, "publication-card--compact" if compact else "")
        actions = render_action_links(
            self.base_path,
            {
                "pdf": publication.get("pdf_url", ""),
                "code": publication.get("code_url", ""),
            },
            compact=True,
        )
        return f"""
        <article class="{classes}" data-reveal data-filter-item data-filter-tags="{slug_token(publication['type'])} {slug_token(publication['research_area'])}">
          <div class="publication-card__meta">
            <span>{h(publication['venue'])}</span>
            <span>{h(self.publication_date_label(publication)) if publication.get('month', '').strip() else ''}</span>
            {award}
          </div>
          <h3 class="publication-card__title"><a href="{resolve_url(self.base_path, f"publications/{publication['slug']}/")}">{h(publication['title'])}</a></h3>
          <p class="publication-card__authors">{h(', '.join(publication['authors']))}</p>
          <p class="publication-card__summary">{h(publication['summary'])}</p>
          <div class="chip-row">{render_tag_list(publication['tags'])}</div>
          <div class="card-actions">{actions}</div>
        </article>
        """

    def render_news_card(self, item: dict[str, Any], compact: bool = False) -> str:
        classes = join_classes("news-card", "news-card--compact" if compact else "")
        return f"""
        <article class="{classes}" data-reveal data-filter-item data-filter-tags="{slug_token(item['type'])}">
          <div class="news-card__meta">
            <span>{h(item['type'])}</span>
            <time datetime="{h(item['date'])}">{h(format_date(item['date']))}</time>
          </div>
          <h3 class="news-card__title"><a href="{resolve_url(self.base_path, f"news/{item['slug']}/")}">{h(item['title'])}</a></h3>
          <p class="news-card__summary">{h(item['summary'])}</p>
        </article>
        """

    def render_team_card(self, member: dict[str, Any]) -> str:
        interests = render_tag_list(member.get("research_interests", []))
        links = render_action_links(
            self.base_path,
            {
                "homepage": member.get("homepage", ""),
                "github": member.get("github", ""),
                "email": f"mailto:{member['email']}" if member.get("email") else "",
            },
            compact=True,
        )
        initials = "".join(part[0] for part in member["name"].split()[:2]).upper()
        photo = member.get("photo", "")
        if photo:
            photo_src = resolve_url(self.base_path, photo)
            avatar_html = (
                f'<div class="team-card__avatar team-card__avatar--photo" aria-hidden="true">'
                f'<img src="{h(photo_src)}" alt="{h(member["name"])}" loading="lazy" />'
                f'</div>'
            )
        else:
            avatar_html = f'<div class="team-card__avatar" aria-hidden="true">{h(initials)}</div>'
        return f"""
        <article class="team-card" data-reveal>
          {avatar_html}
          <div class="team-card__body">
            <p class="team-card__role">{h(member['role'])}</p>
            <h3>{h(member['name'])}</h3>
            <p>{h(member['bio'])}</p>
            <div class="chip-row">{interests}</div>
            <div class="card-actions">{links}</div>
          </div>
        </article>
        """


    def render_hero_timeline(self, max_items: int = 3) -> str:
        """Render a compact timeline for the hero section showing latest items across all types."""
        # Collect all items with their dates
        all_items: list[tuple[str, str, dict[str, Any]]] = []
        
        # Blog items: use date field
        for blog in self.blog:
          if blog.get("status") == "published":
            date_str = blog.get("date", "")
            all_items.append(("blog", date_str, blog))
        
        # Publication items: use year field
        for pub in self.publications:
            year = str(pub.get("year", ""))
            all_items.append(("publication", year, pub))
        
        # Project items: use year field
        for project in self.projects:
            year = str(project.get("year", ""))
            all_items.append(("project", year, project))
        
        # Sort by date descending (newest first)
        def sort_key(x: tuple[str, str, dict[str, Any]]) -> str:
            date_str = x[1]
            # Normalize dates: full dates (2025-04-10) come after years (2025)
            if len(date_str) == 4:  # Just year
                return date_str + "-00-00"
            return date_str
        
        all_items.sort(key=sort_key, reverse=True)
        
        # Take top N
        selected = all_items[:max_items]
        
        if not selected:
            return ""
        
        entries = []
        for item_type, date_str, item in selected:
            if item_type == "blog":
                date = date_str[:4] if date_str else ""
                title = item.get("title", "")
                url = resolve_url(self.base_path, f"blog/{item['slug']}/")
                label = "Blog"
                accent = "blog"
            elif item_type == "publication":
                date = date_str
                title = item.get("title", "")
                url = resolve_url(self.base_path, f"publications/{item['slug']}/")
                label = "Publication"
                accent = "award" if item.get("award") else "publication"
            else:  # project
                date = date_str
                title = item.get("title", "")
                url = resolve_url(self.base_path, f"projects/{item['slug']}/")
                label = "Project"
                accent = "project"
            
            entries.append(f"""
                <a href="{url}" class="hero-timeline__item hero-timeline__item--{accent}">
                    <div class="hero-timeline__content">
                        <span class="hero-timeline__label">{label}</span>
                        <span class="hero-timeline__date">{h(date)}</span>
                        <strong class="hero-timeline__title">{h(title)}</strong>
                    </div>
                </a>
            """)
        
        return f"""
            <div class="hero-timeline">
                {''.join(entries)}
            </div>
        """


def render_site(content: dict[str, Any], base_path: str) -> list[RenderedPage]:
    return SiteRenderer(content, base_path).generate_pages()
