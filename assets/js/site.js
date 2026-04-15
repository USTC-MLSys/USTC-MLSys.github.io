document.documentElement.classList.add("js");

const header = document.querySelector("[data-site-header]");
const menuToggle = document.querySelector("[data-menu-toggle]");
const menuPanel = document.querySelector("[data-menu-panel]");

if (header) {
  const syncHeader = () => {
    header.classList.toggle("is-scrolled", window.scrollY > 12);
  };

  syncHeader();
  window.addEventListener("scroll", syncHeader, { passive: true });
}

if (menuToggle && menuPanel) {
  menuToggle.addEventListener("click", () => {
    const expanded = menuToggle.getAttribute("aria-expanded") === "true";
    menuToggle.setAttribute("aria-expanded", String(!expanded));
    menuToggle.classList.toggle("is-open", !expanded);
    menuPanel.classList.toggle("is-open", !expanded);
  });

  menuPanel.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      menuToggle.setAttribute("aria-expanded", "false");
      menuToggle.classList.remove("is-open");
      menuPanel.classList.remove("is-open");
    });
  });
}

const revealItems = [...document.querySelectorAll("[data-reveal]")];
if (revealItems.length) {
  revealItems.forEach((item, index) => {
    item.style.setProperty("--reveal-delay", `${Math.min(index * 22, 180)}ms`);
  });

  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) {
          return;
        }
        entry.target.classList.add("is-visible");
        revealObserver.unobserve(entry.target);
      });
    },
    {
      threshold: 0.18,
      rootMargin: "0px 0px -6% 0px"
    }
  );

  revealItems.forEach((item) => revealObserver.observe(item));
}

// Table of Contents: scroll spy
(function initTOC() {
  const toc = document.querySelector('[data-toc]');
  if (!toc) return;

  const links = toc.querySelectorAll('[data-toc-link]');
  const targets = [];

  links.forEach((link) => {
    const href = link.getAttribute('href');
    if (href && href.startsWith('#')) {
      const target = document.querySelector(href);
      if (target) targets.push(target);
    }
  });

  if (targets.length === 0) return;

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const id = entry.target.getAttribute('id');
          links.forEach((link) => {
            link.classList.toggle('is-active', link.getAttribute('href') === `#${id}`);
          });
        }
      });
    },
    {
      rootMargin: '-20% 0px -60% 0px',
      threshold: 0,
    }
  );

  targets.forEach((target) => observer.observe(target));
})();

// Site Search
(function initSearch() {
  const searchInput = document.querySelector('[data-search-input]');
  const searchResults = document.querySelector('[data-search-results]');
  if (!searchInput || !searchResults) return;

  let searchIndex = [];
  
  // Load search index
  fetch('/search-index.json')
    .then(res => res.json())
    .then(data => {
      searchIndex = data;
    })
    .catch(err => console.error('Failed to load search index:', err));

  function performSearch(query) {
    if (!query || query.length === 0) return [];
    const lowerQuery = query.toLowerCase();
    return searchIndex
      .filter(item => 
        item.title.toLowerCase().includes(lowerQuery) ||
        item.summary.toLowerCase().includes(lowerQuery) ||
        item.tags.some(tag => tag.toLowerCase().includes(lowerQuery))
      )
      .slice(0, 8);
  }

  function renderResults(results) {
    if (results.length === 0) {
      searchResults.innerHTML = '<div class="site-search__empty">No results found</div>';
      return;
    }

    const typeLabels = {
      project: 'Project',
      publication: 'Publication',
      blog: 'Blog'
    };

    searchResults.innerHTML = results.map(item => `
      <a href="${item.url}" class="site-search__result">
        <span class="site-search__result-type">${typeLabels[item.type] || item.type}</span>
        <div class="site-search__result-title">${escapeHtml(item.title)}</div>
        <div class="site-search__result-summary">${escapeHtml(item.summary)}</div>
      </a>
    `).join('');
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  let debounceTimer;
  searchInput.addEventListener('input', (e) => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      const query = e.target.value.trim();
      if (query.length === 0) {
        searchResults.classList.remove('is-open');
        return;
      }
      const results = performSearch(query);
      renderResults(results);
      searchResults.classList.add('is-open');
    }, 100);
  });

  // Close search results when clicking outside
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.site-search')) {
      searchResults.classList.remove('is-open');
    }
  });

  // Close on escape key
  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      searchResults.classList.remove('is-open');
      searchInput.blur();
    }
  });
})();

// Detail page sidebar: sticky on scroll
// Strategy: use CSS position:sticky on a wrapper, and dynamically set the
// 'top' value so the sidebar stays below the header as the page scrolls.
(function initDetailSidebar() {
  const sidebar = document.querySelector(".detail-sidebar");
  if (!sidebar) return;

  // Don't sticky on narrow screens where sidebar stacks below prose
  const mq = window.matchMedia("(max-width: 1080px)");
  if (mq.matches) return;

  const headerEl = document.querySelector("[data-site-header]");
  // Header height + breathing room
  const OFFSET = headerEl ? headerEl.offsetHeight + 16 : 88;

  // Store initial 'top' value in a CSS variable; JS updates it on scroll
  sidebar.style.setProperty("--sticky-top", OFFSET + "px");
  sidebar.style.position = "sticky";
  sidebar.style.top = OFFSET + "px";
})();

document.querySelectorAll("[data-filter-root]").forEach((root) => {
  const buttons = [...root.querySelectorAll("[data-filter-button]")];
  const container = root.nextElementSibling && root.nextElementSibling.hasAttribute("data-filter-container")
    ? root.nextElementSibling
    : root.parentElement?.querySelector("[data-filter-container]");

  if (!buttons.length || !container) {
    return;
  }

  const items = [...container.querySelectorAll("[data-filter-item]")];

  const applyFilter = (value) => {
    buttons.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.filterValue === value);
    });

    items.forEach((item) => {
      const tags = item.dataset.filterTags || "";
      const visible = value === "all" || tags.split(/\s+/).includes(value);
      item.classList.toggle("is-hidden", !visible);
    });
  };

  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      applyFilter(button.dataset.filterValue || "all");
    });
  });
});
