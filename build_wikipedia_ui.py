import os
import sys
import re
import json
import html
from pathlib import Path
from collections import Counter, defaultdict

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def build_wikipedia_style_html(db_path: Path, output_html: Path):
    print(f"[*] Reading database from {db_path}...")
    with open(db_path, "r", encoding="utf-8") as f:
        stories = json.load(f)

    total_words = sum(s['word_count'] for s in stories)
    total_fiction_count = len(stories)
    universes = Counter(s['universe'] for s in stories)
    categories = Counter(s['category'] for s in stories)

    # Build character database
    char_map = defaultdict(list)
    for s in stories:
        for c in s['characters']:
            char_map[c].append({
                'id': s['id'],
                'title': s['title'],
                'universe': s['universe'],
                'word_count': s['word_count'],
                'category': s['category']
            })

    json_data = json.dumps(stories, ensure_ascii=False)
    char_data = json.dumps(dict(char_map), ensure_ascii=False)

    print(f"[*] Generating Wikipedia-style Fictionpedia HTML for {len(stories)} articles...")

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Fictionpedia — The Free Writing Encyclopedia</title>
  <style>
    /* Wikipedia Vector-like stylesheet with Modern Dark/Light Theme */
    :root {{
      --wiki-bg: #f8f9fa;
      --wiki-content-bg: #ffffff;
      --wiki-border: #a2a9b1;
      --wiki-border-light: #c8ccd1;
      --wiki-text: #202122;
      --wiki-text-muted: #54595d;
      --wiki-link: #0645ad;
      --wiki-link-visited: #0b0080;
      --wiki-link-hover: #0b0080;
      --wiki-link-red: #ba0000;
      --wiki-infobox-bg: #f8f9fa;
      --wiki-infobox-header: #eaecf0;
      --wiki-toc-bg: #f8f9fa;
      --wiki-header-border: #a2a9b1;
      --wiki-tab-active: #ffffff;
      --wiki-tab-inactive: #f8f9fa;
      --wiki-card-border: #eaecf0;
      --wiki-highlight: #fff9db;
      --font-body: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Lato", Helvetica, Arial, sans-serif;
      --font-serif: "Linux Libertine", "Georgia", "Times New Roman", serif;
    }}

    [data-theme="dark"] {{
      --wiki-bg: #10141e;
      --wiki-content-bg: #181f2e;
      --wiki-border: #364259;
      --wiki-border-light: #283347;
      --wiki-text: #eaecf0;
      --wiki-text-muted: #9aa7b8;
      --wiki-link: #6ba3ff;
      --wiki-link-visited: #9abaff;
      --wiki-link-hover: #9abaff;
      --wiki-link-red: #ff7575;
      --wiki-infobox-bg: #1f283b;
      --wiki-infobox-header: #28344c;
      --wiki-toc-bg: #1f283b;
      --wiki-header-border: #364259;
      --wiki-tab-active: #181f2e;
      --wiki-tab-inactive: #121722;
      --wiki-card-border: #2e3b52;
      --wiki-highlight: #2c3a52;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: var(--font-body);
      font-size: 14.5px;
      line-height: 1.6;
      background-color: var(--wiki-bg);
      color: var(--wiki-text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}

    a {{
      color: var(--wiki-link);
      text-decoration: none;
      cursor: pointer;
    }}
    a:hover {{ text-decoration: underline; }}

    /* Wikipedia Header Bar */
    header.wiki-header {{
      background: var(--wiki-content-bg);
      border-bottom: 1px solid var(--wiki-border-light);
      padding: 0.5rem 1.5rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 100;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}

    .wiki-brand {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      cursor: pointer;
    }}

    .wiki-logo-icon {{
      width: 42px;
      height: 42px;
      background: linear-gradient(135deg, #3366cc, #8b5cf6);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-family: var(--font-serif);
      font-size: 1.5rem;
      font-weight: bold;
      border: 2px solid var(--wiki-border-light);
    }}

    .wiki-brand-text h1 {{
      font-family: var(--font-serif);
      font-size: 1.35rem;
      font-weight: normal;
      letter-spacing: 0.02em;
      line-height: 1.1;
    }}

    .wiki-brand-text p {{
      font-size: 0.75rem;
      color: var(--wiki-text-muted);
    }}

    .wiki-search-box {{
      flex: 1;
      max-width: 480px;
      margin: 0 1.5rem;
      position: relative;
    }}

    .wiki-search-input {{
      width: 100%;
      padding: 0.45rem 0.75rem 0.45rem 2.2rem;
      border: 1px solid var(--wiki-border);
      border-radius: 2px;
      font-size: 0.88rem;
      background: var(--wiki-bg);
      color: var(--wiki-text);
      outline: none;
    }}
    .wiki-search-input:focus {{
      border-color: var(--wiki-link);
      background: var(--wiki-content-bg);
      box-shadow: 0 0 0 2px rgba(6,69,173,0.15);
    }}

    .wiki-search-icon {{
      position: absolute;
      left: 0.75rem;
      top: 50%;
      transform: translateY(-50%);
      color: var(--wiki-text-muted);
      font-size: 0.9rem;
    }}

    .search-suggestions {{
      position: absolute;
      top: 100%;
      left: 0;
      right: 0;
      background: var(--wiki-content-bg);
      border: 1px solid var(--wiki-border);
      border-top: none;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      max-height: 360px;
      overflow-y: auto;
      display: none;
      z-index: 1000;
    }}

    .search-item {{
      padding: 0.5rem 0.75rem;
      border-bottom: 1px solid var(--wiki-card-border);
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .search-item:hover, .search-item.active {{
      background: var(--wiki-infobox-header);
    }}

    .search-item-title {{
      font-weight: 600;
      font-size: 0.9rem;
    }}

    .search-item-meta {{
      font-size: 0.75rem;
      color: var(--wiki-text-muted);
    }}

    .wiki-top-tools {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}

    .wiki-btn {{
      background: var(--wiki-bg);
      border: 1px solid var(--wiki-border);
      color: var(--wiki-text);
      padding: 0.35rem 0.75rem;
      border-radius: 3px;
      font-size: 0.82rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.35rem;
    }}
    .wiki-btn:hover {{
      background: var(--wiki-infobox-header);
    }}

    /* Main Grid Layout */
    .wiki-layout {{
      display: flex;
      flex: 1;
      max-width: 1560px;
      margin: 0 auto;
      width: 100%;
      padding: 1.25rem 1rem;
      gap: 1.5rem;
    }}

    /* Left Sidebar (Wikipedia Navigation) */
    aside.wiki-sidebar {{
      width: 230px;
      flex-shrink: 0;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }}

    .wiki-nav-group {{
      border-bottom: 1px solid var(--wiki-border-light);
      padding-bottom: 0.75rem;
    }}

    .wiki-nav-title {{
      font-size: 0.75rem;
      text-transform: uppercase;
      font-weight: 700;
      color: var(--wiki-text-muted);
      margin-bottom: 0.4rem;
      letter-spacing: 0.05em;
    }}

    .wiki-nav-list {{
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 0.3rem;
    }}

    .wiki-nav-list li a {{
      font-size: 0.88rem;
      display: flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.2rem 0.3rem;
      border-radius: 2px;
    }}
    .wiki-nav-list li a:hover {{
      background: var(--wiki-infobox-header);
      text-decoration: none;
    }}

    /* Article Content Main Area */
    main.wiki-article-container {{
      flex: 1;
      min-width: 0;
      background: var(--wiki-content-bg);
      border: 1px solid var(--wiki-border-light);
      padding: 2rem 2.5rem;
      border-radius: 3px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }}

    /* Article Top Tabs */
    .article-tabs-bar {{
      display: flex;
      justify-content: space-between;
      border-bottom: 1px solid var(--wiki-header-border);
      margin-bottom: 1rem;
    }}

    .article-tabs {{
      display: flex;
      gap: 0.25rem;
    }}

    .article-tab {{
      padding: 0.4rem 0.9rem;
      font-size: 0.85rem;
      border: 1px solid transparent;
      border-bottom: none;
      background: var(--wiki-tab-inactive);
      color: var(--wiki-link);
      cursor: pointer;
      border-radius: 3px 3px 0 0;
      margin-bottom: -1px;
    }}
    .article-tab.active {{
      background: var(--wiki-tab-active);
      border-color: var(--wiki-header-border);
      color: var(--wiki-text);
      font-weight: 600;
      border-bottom: 1px solid var(--wiki-content-bg);
    }}

    /* Title Heading */
    h1.firstHeading {{
      font-family: var(--font-serif);
      font-size: 2rem;
      font-weight: normal;
      line-height: 1.25;
      margin-bottom: 0.2rem;
      border-bottom: 1px solid var(--wiki-header-border);
      padding-bottom: 0.4rem;
    }}

    .siteSub {{
      font-size: 0.78rem;
      color: var(--wiki-text-muted);
      margin-bottom: 1.25rem;
    }}

    /* Wikipedia Infobox */
    .infobox {{
      float: right;
      width: 320px;
      margin: 0 0 1.25rem 1.5rem;
      background: var(--wiki-infobox-bg);
      border: 1px solid var(--wiki-border);
      border-spacing: 0;
      font-size: 0.85rem;
      line-height: 1.45;
      border-collapse: collapse;
      border-radius: 3px;
    }}

    .infobox-title {{
      background: var(--wiki-infobox-header);
      font-family: var(--font-serif);
      font-size: 1.15rem;
      font-weight: bold;
      text-align: center;
      padding: 0.6rem 0.75rem;
      border-bottom: 1px solid var(--wiki-border);
    }}

    .infobox-subheader {{
      text-align: center;
      font-size: 0.78rem;
      color: var(--wiki-text-muted);
      padding: 0.25rem;
      border-bottom: 1px solid var(--wiki-border-light);
    }}

    .infobox th, .infobox td {{
      padding: 0.45rem 0.65rem;
      border-bottom: 1px solid var(--wiki-card-border);
      vertical-align: top;
      text-align: left;
    }}

    .infobox th {{
      width: 38%;
      font-weight: 600;
      color: var(--wiki-text-muted);
    }}

    /* Table of Contents (TOC) */
    .toc {{
      background: var(--wiki-toc-bg);
      border: 1px solid var(--wiki-border);
      padding: 0.75rem 1.25rem;
      display: inline-block;
      margin: 1.25rem 0;
      border-radius: 3px;
      min-width: 250px;
    }}

    .toctitle {{
      font-weight: bold;
      text-align: center;
      margin-bottom: 0.5rem;
      font-size: 0.9rem;
    }}

    .toc ul {{
      list-style: none;
      padding-left: 0;
      font-size: 0.88rem;
    }}

    .toc ul li {{
      margin-bottom: 0.25rem;
    }}

    .tocnumber {{
      color: var(--wiki-text-muted);
      margin-right: 0.4rem;
    }}

    /* Article Content Headings */
    .wiki-body h2 {{
      font-family: var(--font-serif);
      font-size: 1.5rem;
      font-weight: normal;
      border-bottom: 1px solid var(--wiki-header-border);
      margin: 2rem 0 0.85rem;
      padding-bottom: 0.3rem;
    }}

    .wiki-body h3 {{
      font-size: 1.15rem;
      font-weight: 600;
      margin: 1.5rem 0 0.6rem;
    }}

    .wiki-body p {{
      margin-bottom: 1rem;
      line-height: 1.7;
    }}

    .wiki-body blockquote {{
      background: var(--wiki-infobox-bg);
      border-left: 4px solid var(--wiki-link);
      padding: 0.75rem 1.25rem;
      margin: 1.25rem 0;
      font-style: italic;
      color: var(--wiki-text);
    }}

    /* Main Page Portal Styles */
    .portal-banner {{
      background: var(--wiki-infobox-bg);
      border: 1px solid var(--wiki-border);
      padding: 1.25rem 1.5rem;
      margin-bottom: 1.5rem;
      border-radius: 3px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .portal-banner h2 {{
      font-family: var(--font-serif);
      font-size: 1.6rem;
      margin: 0 0 0.25rem;
      border-bottom: none;
    }}

    .portal-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 1.25rem;
      margin-bottom: 1.5rem;
    }}

    .portal-card {{
      background: var(--wiki-content-bg);
      border: 1px solid var(--wiki-border-light);
      border-radius: 3px;
      overflow: hidden;
    }}

    .portal-card-header {{
      background: var(--wiki-infobox-header);
      padding: 0.6rem 0.85rem;
      font-weight: bold;
      font-family: var(--font-serif);
      font-size: 1rem;
      border-bottom: 1px solid var(--wiki-border-light);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .portal-card-body {{
      padding: 1rem;
      font-size: 0.88rem;
    }}

    .portal-list {{
      list-style: disc;
      padding-left: 1.25rem;
      margin-top: 0.5rem;
    }}

    .portal-list li {{
      margin-bottom: 0.35rem;
    }}

    /* A-Z Index Table */
    .index-letters {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.35rem;
      margin: 1rem 0 1.5rem;
      padding: 0.5rem;
      background: var(--wiki-infobox-bg);
      border: 1px solid var(--wiki-border-light);
    }}

    .letter-btn {{
      padding: 0.25rem 0.6rem;
      border: 1px solid var(--wiki-border);
      background: var(--wiki-content-bg);
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
    }}
    .letter-btn:hover, .letter-btn.active {{
      background: var(--wiki-link);
      color: white;
      border-color: var(--wiki-link);
    }}

    .index-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.88rem;
    }}
    .index-table th, .index-table td {{
      padding: 0.5rem 0.75rem;
      border-bottom: 1px solid var(--wiki-card-border);
      text-align: left;
    }}
    .index-table th {{
      background: var(--wiki-infobox-header);
      font-weight: 600;
    }}
    .index-table tr:hover td {{
      background: var(--wiki-infobox-bg);
    }}

    /* Categories Box at Bottom */
    .catlinks {{
      margin-top: 2.5rem;
      padding: 0.6rem 0.85rem;
      background: var(--wiki-infobox-bg);
      border: 1px solid var(--wiki-border);
      font-size: 0.82rem;
      border-radius: 3px;
    }}
    .catlinks ul {{
      display: inline;
      list-style: none;
      padding-left: 0;
    }}
    .catlinks li {{
      display: inline-block;
      margin-right: 0.5rem;
      padding-right: 0.5rem;
      border-right: 1px solid var(--wiki-border-light);
    }}
    .catlinks li:last-child {{
      border-right: none;
    }}

    /* Reader Mode Tab */
    .reader-mode-body {{
      font-family: var(--font-serif);
      font-size: 1.15rem;
      line-height: 1.8;
      max-width: 820px;
      margin: 1.5rem auto;
      padding: 1rem 0;
    }}
    .reader-mode-body p {{
      margin-bottom: 1.4rem;
      text-indent: 1.5em;
    }}
    .reader-mode-body p:first-of-type, .reader-mode-body h2 + p, .reader-mode-body h3 + p {{
      text-indent: 0;
    }}

    @media (max-width: 900px) {{
      .wiki-layout {{ flex-direction: column; }}
      aside.wiki-sidebar {{ width: 100%; }}
      .infobox {{ float: none; width: 100%; margin: 1rem 0; }}
      main.wiki-article-container {{ padding: 1.25rem; }}
    }}
  </style>
</head>
<body data-theme="light">

  <!-- Header -->
  <header class="wiki-header">
    <div class="wiki-brand" onclick="navigateTo('main')">
      <div class="wiki-logo-icon">W</div>
      <div class="wiki-brand-text">
        <h1>Fictionpedia</h1>
        <p>The Free Personal Writing Encyclopedia</p>
      </div>
    </div>

    <!-- Search with Suggestions -->
    <div class="wiki-search-box">
      <span class="wiki-search-icon">🔍</span>
      <input type="text" id="wikiSearchInput" class="wiki-search-input" placeholder="Search Fictionpedia (articles, characters, text)..." oninput="onSearchInput(this.value)" onkeydown="onSearchKey(event)">
      <div class="search-suggestions" id="searchSuggestions"></div>
    </div>

    <div class="wiki-top-tools">
      <button class="wiki-btn" onclick="goToRandomArticle()" title="Jump to a random story or manuscript">🎲 Random</button>
      <button class="wiki-btn" onclick="toggleTheme()" id="themeToggleBtn">🌙 Dark</button>
      <button class="wiki-btn" onclick="exportArchive()" title="Download raw JSON database">📥 Export</button>
    </div>
  </header>

  <!-- Layout Container -->
  <div class="wiki-layout">

    <!-- Left Wikipedia Sidebar -->
    <aside class="wiki-sidebar">
      <div class="wiki-nav-group">
        <div class="wiki-nav-title">Navigation</div>
        <ul class="wiki-nav-list">
          <li><a onclick="navigateTo('main')">🏠 Main Page</a></li>
          <li><a onclick="navigateTo('universes')">🌌 Sagas & Universes</a></li>
          <li><a onclick="navigateTo('characters')">👥 Character Codex</a></li>
          <li><a onclick="navigateTo('index')">🔤 All Articles (A–Z)</a></li>
          <li><a onclick="goToRandomArticle()">🎲 Random Article</a></li>
        </ul>
      </div>

      <div class="wiki-nav-group">
        <div class="wiki-nav-title">Major Universes</div>
        <ul class="wiki-nav-list">
          <li><a onclick="filterByUniverse('The Dead Down Under')">🇦🇺 The Dead Down Under</a></li>
          <li><a onclick="filterByUniverse('The Dead and the Signal')">📻 The Dead and the Signal</a></li>
          <li><a onclick="filterByUniverse('The Dead and the Rust')">⚙️ The Dead and the Rust</a></li>
          <li><a onclick="filterByUniverse('The Dead and the Sand')">🏜️ The Dead and the Sand</a></li>
          <li><a onclick="filterByUniverse('The Raven\'s Wake')">🚀 The Raven's Wake</a></li>
          <li><a onclick="filterByUniverse('Gravebound Universe')">💀 Gravebound</a></li>
          <li><a onclick="filterByUniverse('The Head Wife / Proud Hopper')">👑 The Head Wife Chronicles</a></li>
          <li><a onclick="filterByUniverse('Indigenous & Mythic Lore')">🦅 Mr. Stone & Indigenous Lore</a></li>
        </ul>
      </div>

      <div class="wiki-nav-group">
        <div class="wiki-nav-title">Archive Statistics</div>
        <div style="font-size:0.8rem; color:var(--wiki-text-muted); line-height:1.5; padding: 0.2rem 0.3rem;">
          • <strong>{total_fiction_count}</strong> Articles<br>
          • <strong>{total_words:,}</strong> Words<br>
          • <strong>{len(universes)}</strong> Fictional Universes<br>
          • <strong>{len(char_map)}</strong> Tracked Characters
        </div>
      </div>
    </aside>

    <!-- Main Content Area -->
    <main class="wiki-article-container" id="articleContainer">
      <!-- Dynamically populated article or portal -->
    </main>

  </div>

  <script>
    const database = {json_data};
    const characterMap = {char_data};
    let currentArticle = null;
    let currentTab = 'article';
    let activeSuggestionIdx = -1;

    // Navigation router
    function navigateTo(target, param) {{
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
      if (target === 'main') {{
        renderMainPage();
      }} else if (target === 'article') {{
        renderArticle(param);
      }} else if (target === 'universes') {{
        renderUniversesPortal(param);
      }} else if (target === 'characters') {{
        renderCharacterCodex(param);
      }} else if (target === 'character-bio') {{
        renderCharacterBio(param);
      }} else if (target === 'index') {{
        renderIndexPage(param);
      }}
      closeSuggestions();
    }}

    // Render Wikipedia Main Page
    function renderMainPage() {{
      const featured = database.find(s => s.word_count > 40000) || database[0];
      
      let html = `
        <div class="portal-banner">
          <div>
            <h2>Welcome to Fictionpedia,</h2>
            <p style="color:var(--wiki-text-muted);">the comprehensive open encyclopedia of the writing archives of ketrovin.</p>
          </div>
          <div style="text-align:right; font-size:0.85rem; color:var(--wiki-text-muted);">
            <strong>{total_fiction_count}</strong> creative articles in archive<br>
            <strong>{total_words:,}</strong> total written words
          </div>
        </div>

        <div class="portal-grid">
          <!-- Featured Article -->
          <div class="portal-card">
            <div class="portal-card-header">
              <span>⭐ Featured Manuscript</span>
              <a onclick="navigateTo('article', '${{featured.id}}')" style="font-size:0.8rem;">Full Article →</a>
            </div>
            <div class="portal-card-body">
              <h3 style="margin-bottom:0.4rem;"><a onclick="navigateTo('article', '${{featured.id}}')">${{escapeHtml(featured.title)}}</a></h3>
              <p style="font-size:0.82rem; color:var(--wiki-text-muted); margin-bottom:0.6rem;">
                <strong>Universe:</strong> <a onclick="filterByUniverse('${{escapeHtml(featured.universe)}}')">${{escapeHtml(featured.universe)}}</a> • 
                <strong>Length:</strong> ${{featured.word_count.toLocaleString()}} words (${{featured.tier}})
              </p>
              <p>${{escapeHtml(featured.excerpt)}}</p>
              <div style="margin-top:0.75rem;">
                <a onclick="navigateTo('article', '${{featured.id}}')" style="font-weight:600;">(Read more...)</a>
              </div>
            </div>
          </div>

          <!-- Major Sagas Portal -->
          <div class="portal-card">
            <div class="portal-card-header">
              <span>🌌 Major Sagas & Story Worlds</span>
              <a onclick="navigateTo('universes')" style="font-size:0.8rem;">All Sagas →</a>
            </div>
            <div class="portal-card-body">
              <ul class="portal-list">
                <li><strong><a onclick="filterByUniverse('The Dead Down Under')">The Dead Down Under</a></strong> — Full-length outbreak novel set across the Australian wasteland (108k+ words).</li>
                <li><strong><a onclick="filterByUniverse('The Dead and the Signal')">The Dead and the Signal</a></strong> — 30-part perspective anthology of the collapse through radio & comms (72k+ words).</li>
                <li><strong><a onclick="filterByUniverse('The Raven\'s Wake')">The Raven\'s Wake</a></strong> — Deep space exploration and existential sci-fi manuscript (92k+ words).</li>
                <li><strong><a onclick="filterByUniverse('The Dead and the Rust')">The Dead and the Rust</a></strong> — Industrial defense, scrap mechanics, and salvage survival (51k+ words).</li>
                <li><strong><a onclick="filterByUniverse('The Dead and the Sand')">The Dead and the Sand</a></strong> — Arid wasteland outbreak, desert oases, and geothermal defense (50k+ words).</li>
                <li><strong><a onclick="filterByUniverse('The Head Wife / Proud Hopper')">The Head Wife Chronicles</a></strong> — Martial politics, power filters, and SCP-NB dossiers.</li>
              </ul>
            </div>
          </div>
        </div>

        <!-- Portals & Categories -->
        <div class="portal-card" style="margin-bottom:1.5rem;">
          <div class="portal-card-header">
            <span>📚 Browse by Category</span>
          </div>
          <div class="portal-card-body">
            <div style="display:flex; flex-wrap:wrap; gap:0.6rem;">
              <button class="wiki-btn" onclick="renderIndexPage('Novel')">📖 Novels & Manuscripts (${{database.filter(s=>s.category.includes('Novel')).length}})</button>
              <button class="wiki-btn" onclick="renderIndexPage('Novella')">📕 Novellas (${{database.filter(s=>s.category.includes('Novella')).length}})</button>
              <button class="wiki-btn" onclick="renderIndexPage('Serialized')">📑 Serialized Chapters (${{database.filter(s=>s.category.includes('Chapter')).length}})</button>
              <button class="wiki-btn" onclick="renderIndexPage('Short')">📝 Short Stories (${{database.filter(s=>s.category.includes('Short')).length}})</button>
              <button class="wiki-btn" onclick="renderIndexPage('Worldbuilding')">🗺️ Worldbuilding & Lore (${{database.filter(s=>s.category.includes('Lore')).length}})</button>
              <button class="wiki-btn" onclick="renderIndexPage('Screenplay')">🎬 Screenplays & Scripts (${{database.filter(s=>s.category.includes('Script')).length}})</button>
            </div>
          </div>
        </div>

        <div class="catlinks">
          <strong>Portals:</strong>
          <ul>
            <li><a onclick="navigateTo('universes')">Fictional Universes</a></li>
            <li><a onclick="navigateTo('characters')">Character Codex</a></li>
            <li><a onclick="navigateTo('index')">Full Manuscript Archive</a></li>
            <li><a onclick="exportArchive()">Database Backup</a></li>
          </ul>
        </div>
      `;

      document.getElementById('articleContainer').innerHTML = html;
    }}

    // Render Wikipedia Article Page
    function renderArticle(storyId, tab = 'article') {{
      const story = database.find(s => s.id === storyId);
      if (!story) return;
      currentArticle = story;
      currentTab = tab;

      let relatedStories = database.filter(s => s.universe === story.universe && s.id !== story.id).slice(0, 6);

      let charactersList = story.characters.map(c => `
        <a onclick="navigateTo('character-bio', '${{escapeHtml(c)}}')">${{escapeHtml(c)}}</a>
      `).join(', ') || '<em>None explicitly designated</em>';

      let html = `
        <div class="article-tabs-bar">
          <div class="article-tabs">
            <button class="article-tab ${{tab === 'article' ? 'active' : ''}}" onclick="renderArticle('${{story.id}}', 'article')">Article</button>
            <button class="article-tab ${{tab === 'reader' ? 'active' : ''}}" onclick="renderArticle('${{story.id}}', 'reader')">📖 Full Manuscript (${{story.word_count.toLocaleString()}} words)</button>
            <button class="article-tab ${{tab === 'meta' ? 'active' : ''}}" onclick="renderArticle('${{story.id}}', 'meta')">File Metadata</button>
          </div>
          <div style="font-size:0.75rem; color:var(--wiki-text-muted); display:flex; align-items:center; gap:0.5rem;">
            <span>Last modified: ${{story.last_modified}}</span>
          </div>
        </div>

        <h1 class="firstHeading">${{escapeHtml(story.title)}}</h1>
        <div class="siteSub">From Fictionpedia, the free writing encyclopedia</div>
      `;

      if (tab === 'article') {{
        html += `
          <!-- Wikipedia Infobox -->
          <table class="infobox">
            <tr>
              <th colspan="2" class="infobox-title">${{escapeHtml(story.title)}}</th>
            </tr>
            <tr>
              <td colspan="2" class="infobox-subheader">Fictional manuscript from the <em>${{escapeHtml(story.universe)}}</em></td>
            </tr>
            <tr>
              <th>Universe</th>
              <td><a onclick="filterByUniverse('${{escapeHtml(story.universe)}}')">${{escapeHtml(story.universe)}}</a></td>
            </tr>
            <tr>
              <th>Author</th>
              <td>ketrovin</td>
            </tr>
            <tr>
              <th>Category</th>
              <td>${{escapeHtml(story.category)}}</td>
            </tr>
            <tr>
              <th>Length</th>
              <td>${{story.word_count.toLocaleString()}} words (${{story.tier}})</td>
            </tr>
            <tr>
              <th>Reading Time</th>
              <td>${{story.read_time}}</td>
            </tr>
            <tr>
              <th>Format</th>
              <td>${{story.format}} (.${{story.format.toLowerCase()}})</td>
            </tr>
            <tr>
              <th>Key Characters</th>
              <td>${{charactersList}}</td>
            </tr>
            <tr>
              <th>Tags / Themes</th>
              <td>${{story.tags.map(t => `<span style="display:inline-block; background:var(--wiki-infobox-header); padding:1px 5px; margin:2px; border-radius:2px; font-size:0.75rem;">${{escapeHtml(t)}}</span>`).join('')}}</td>
            </tr>
          </table>

          <div class="wiki-body">
            <p><strong><em>${{escapeHtml(story.title)}}</em></strong> is a ${{story.tier.toLowerCase()}} (${{story.word_count.toLocaleString()}} words) belonging to the <strong><a onclick="filterByUniverse('${{escapeHtml(story.universe)}}')">${{escapeHtml(story.universe)}}</a></strong> series. It is classified under <em>${{escapeHtml(story.category)}}</em> and was authored by ketrovin.</p>

            <!-- Table of Contents -->
            <div class="toc">
              <div class="toctitle">Contents</div>
              <ul>
                <li><span class="tocnumber">1</span> <a href="#sec-overview">Overview & Opening</a></li>
                <li><span class="tocnumber">2</span> <a href="#sec-characters">Characters & Personas</a></li>
                ${{story.chapters && story.chapters.length ? `<li><span class="tocnumber">3</span> <a href="#sec-chapters">Chapter Index (${{story.chapters.length}} chapters)</a></li>` : ''}}
                <li><span class="tocnumber">${{story.chapters && story.chapters.length ? '4' : '3'}}</span> <a href="#sec-related">Related Works & Universe</a></li>
              </ul>
            </div>

            <h2 id="sec-overview">1 Overview & Opening</h2>
            <blockquote>
              "${{escapeHtml(story.excerpt)}}"
            </blockquote>
            <p>The manuscript spans approximately ${{story.word_count.toLocaleString()}} words with an estimated reading time of ${{story.read_time}}. Readers can access the complete unabridged text in the <a onclick="renderArticle('${{story.id}}', 'reader')">Full Manuscript tab</a>.</p>

            <h2 id="sec-characters">2 Characters & Personas</h2>
            <p>The following named personas and entities are tracked in this text:</p>
            <ul>
              ${{story.characters && story.characters.length ? story.characters.map(c => `
                <li><strong><a onclick="navigateTo('character-bio', '${{escapeHtml(c)}}')">${{escapeHtml(c)}}</a></strong> — featured persona in this work.</li>
              `).join('') : '<li><em>No primary recurring character names isolated.</em></li>'}}
            </ul>

            ${{story.chapters && story.chapters.length ? `
              <h2 id="sec-chapters">3 Chapter Index</h2>
              <ol style="padding-left:1.5rem; margin-bottom:1rem;">
                ${{story.chapters.map((ch, idx) => `
                  <li style="margin-bottom:0.35rem;"><a onclick="renderArticle('${{story.id}}', 'reader')"><strong>${{escapeHtml(ch.title)}}</strong></a></li>
                `).join('')}}
              </ol>
            ` : ''}}

            <h2 id="sec-related">Related Works in ${{escapeHtml(story.universe)}}</h2>
            ${{relatedStories.length ? `
              <ul>
                ${{relatedStories.map(r => `
                  <li><a onclick="navigateTo('article', '${{r.id}}')"><strong>${{escapeHtml(r.title)}}</strong></a> — ${{r.category}} (${{r.word_count.toLocaleString()}} words)</li>
                `).join('')}}
              </ul>
            ` : `<p><em>This is the primary standalone manuscript in this universe entry.</em></p>`}}
          </div>
        `;
      }} else if (tab === 'reader') {{
        html += `
          <div class="reader-mode-body">
            <div style="border-bottom:1px solid var(--wiki-border-light); padding-bottom:0.75rem; margin-bottom:1.5rem; display:flex; justify-content:space-between; align-items:center;">
              <span style="font-size:0.9rem; color:var(--wiki-text-muted);"><strong>Reading Mode</strong> • ${{story.word_count.toLocaleString()}} words • ${{story.read_time}}</span>
              <button class="wiki-btn" onclick="window.print()">🖨️ Print Manuscript</button>
            </div>
            ${{formatStoryForReader(story.content)}}
          </div>
        `;
      }} else if (tab === 'meta') {{
        html += `
          <div class="wiki-body" style="margin-top:1.5rem;">
            <h2>File System & Archival Metadata</h2>
            <table class="index-table" style="max-width:700px; margin-top:1rem;">
              <tr><th>Property</th><th>Value</th></tr>
              <tr><td><strong>Document ID</strong></td><td><code>${{story.id}}</code></td></tr>
              <tr><td><strong>Original File Path</strong></td><td><code>${{story.file_path}}</code></td></tr>
              <tr><td><strong>Original Filename</strong></td><td>${{story.filename}}</td></tr>
              <tr><td><strong>Format</strong></td><td>${{story.format}}</td></tr>
              <tr><td><strong>File Size</strong></td><td>${{story.size_kb}} KB</td></tr>
              <tr><td><strong>Character Count</strong></td><td>${{story.char_count.toLocaleString()}} characters</td></tr>
              <tr><td><strong>Word Count</strong></td><td>${{story.word_count.toLocaleString()}} words</td></tr>
              <tr><td><strong>Last Modified</strong></td><td>${{story.last_modified}}</td></tr>
            </table>
          </div>
        `;
      }}

      html += `
        <div class="catlinks">
          <strong>Categories:</strong>
          <ul>
            <li><a onclick="filterByUniverse('${{escapeHtml(story.universe)}}')">${{escapeHtml(story.universe)}}</a></li>
            <li><a onclick="renderIndexPage('${{escapeHtml(story.category)}}')">${{escapeHtml(story.category)}}</a></li>
            <li><a onclick="renderIndexPage('${{escapeHtml(story.tier)}}')">${{escapeHtml(story.tier)}}</a></li>
            <li><a>ketrovin Archive</a></li>
          </ul>
        </div>
      `;

      document.getElementById('articleContainer').innerHTML = html;
    }}

    // Render Universes Portal
    function renderUniversesPortal(selectedUniverse = null) {{
      const groups = {{}};
      database.forEach(s => {{
        if (!groups[s.universe]) groups[s.universe] = [];
        groups[s.universe].push(s);
      }});

      let univKeys = Object.keys(groups).sort((a,b) => groups[b].reduce((acc,s)=>acc+s.word_count,0) - groups[a].reduce((acc,s)=>acc+s.word_count,0));
      if (selectedUniverse) {{
        univKeys = [selectedUniverse, ...univKeys.filter(k => k !== selectedUniverse)];
      }}

      let html = `
        <h1 class="firstHeading">Portal: Fictional Universes & Sagas</h1>
        <div class="siteSub">From Fictionpedia, the free writing encyclopedia</div>
        <p>This portal indexes all <strong>${{univKeys.length}}</strong> distinct narrative universes, series, and story worlds authored across the archive.</p>
        <hr style="border:0; height:1px; background:var(--wiki-header-border); margin:1rem 0 1.5rem;">
      `;

      univKeys.forEach(univ => {{
        const items = groups[univ].sort((a,b) => b.word_count - a.word_count);
        const univWords = items.reduce((sum, s) => sum + s.word_count, 0);

        html += `
          <div style="margin-bottom:2.5rem; background:var(--wiki-infobox-bg); border:1px solid var(--wiki-border-light); border-radius:3px; padding:1.25rem;">
            <div style="display:flex; justify-content:space-between; align-items:baseline; border-bottom:1px solid var(--wiki-border-light); padding-bottom:0.5rem; margin-bottom:1rem;">
              <h2 style="font-family:var(--font-serif); font-size:1.4rem; margin:0; border:none;">🌌 ${{escapeHtml(univ)}}</h2>
              <span style="font-size:0.82rem; color:var(--wiki-text-muted); font-weight:600;">${{items.length}} manuscripts • ${{univWords.toLocaleString()}} words</span>
            </div>
            
            <table class="index-table">
              <thead>
                <tr>
                  <th>Title / Article</th>
                  <th>Category</th>
                  <th>Length</th>
                  <th>Key Entities</th>
                </tr>
              </thead>
              <tbody>
                ${{items.map(item => `
                  <tr>
                    <td><a onclick="navigateTo('article', '${{item.id}}')"><strong>${{escapeHtml(item.title)}}</strong></a></td>
                    <td>${{escapeHtml(item.category)}}</td>
                    <td>${{item.word_count.toLocaleString()}} w</td>
                    <td style="font-size:0.8rem; color:var(--wiki-text-muted);">
                      ${{item.characters && item.characters.length ? item.characters.slice(0,3).map(c => `<a onclick="navigateTo('character-bio', '${{escapeHtml(c)}}')">${{escapeHtml(c)}}</a>`).join(', ') : '—'}}
                    </td>
                  </tr>
                `).join('')}}
              </tbody>
            </table>
          </div>
        `;
      }});

      document.getElementById('articleContainer').innerHTML = html;
    }}

    // Render Character Codex
    function renderCharacterCodex() {{
      const charKeys = Object.keys(characterMap).sort((a,b) => characterMap[b].length - characterMap[a].length);

      let html = `
        <h1 class="firstHeading">Portal: Character & Entity Codex</h1>
        <div class="siteSub">From Fictionpedia, the free writing encyclopedia</div>
        <p>This codex catalogues all <strong>${{charKeys.length}}</strong> named personas, protagonists, and recurring entities across your manuscripts.</p>
        <hr style="border:0; height:1px; background:var(--wiki-header-border); margin:1rem 0 1.5rem;">

        <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(280px, 1fr)); gap:1rem;">
          ${{charKeys.map(name => `
            <div style="background:var(--wiki-infobox-bg); border:1px solid var(--wiki-border-light); padding:1rem; border-radius:3px;">
              <h3 style="margin-top:0; font-family:var(--font-serif); font-size:1.15rem;">
                <a onclick="navigateTo('character-bio', '${{escapeHtml(name)}}')">👤 ${{escapeHtml(name)}}</a>
              </h3>
              <p style="font-size:0.8rem; color:var(--wiki-text-muted); margin-bottom:0.5rem;">Appears in ${{characterMap[name].length}} manuscript(s):</p>
              <ul style="padding-left:1.2rem; font-size:0.82rem;">
                ${{characterMap[name].slice(0, 4).map(st => `
                  <li><a onclick="navigateTo('article', '${{st.id}}')">${{escapeHtml(st.title)}}</a></li>
                `).join('')}}
              </ul>
            </div>
          `).join('')}}
        </div>
      `;

      document.getElementById('articleContainer').innerHTML = html;
    }}

    // Render Individual Character Bio Page
    function renderCharacterBio(charName) {{
      const appearances = characterMap[charName] || [];
      const primaryUniverse = appearances.length ? appearances[0].universe : 'Fiction Vault';

      let html = `
        <h1 class="firstHeading">${{escapeHtml(charName)}} (character)</h1>
        <div class="siteSub">From Fictionpedia, the free writing encyclopedia</div>

        <!-- Character Infobox -->
        <table class="infobox">
          <tr>
            <th colspan="2" class="infobox-title">👤 ${{escapeHtml(charName)}}</th>
          </tr>
          <tr>
            <td colspan="2" class="infobox-subheader">Fictional Character from <em>${{escapeHtml(primaryUniverse)}}</em></td>
          </tr>
          <tr>
            <th>Primary Universe</th>
            <td><a onclick="filterByUniverse('${{escapeHtml(primaryUniverse)}}')">${{escapeHtml(primaryUniverse)}}</a></td>
          </tr>
          <tr>
            <th>Total Appearances</th>
            <td>${{appearances.length}} works</td>
          </tr>
          <tr>
            <th>Creator</th>
            <td>ketrovin</td>
          </tr>
        </table>

        <div class="wiki-body">
          <p><strong>${{escapeHtml(charName)}}</strong> is a recurring fictional persona within the <strong><a onclick="filterByUniverse('${{escapeHtml(primaryUniverse)}}')">${{escapeHtml(primaryUniverse)}}</a></strong> fictional series created by author ketrovin.</p>

          <h2>Manuscript Appearances</h2>
          <p>${{escapeHtml(charName)}} appears in the following ${{appearances.length}} document(s) in the archive:</p>
          <table class="index-table" style="margin-top:1rem;">
            <thead>
              <tr>
                <th>Title</th>
                <th>Universe</th>
                <th>Category</th>
                <th>Word Count</th>
              </tr>
            </thead>
            <tbody>
              ${{appearances.map(st => `
                <tr>
                  <td><a onclick="navigateTo('article', '${{st.id}}')"><strong>${{escapeHtml(st.title)}}</strong></a></td>
                  <td>${{escapeHtml(st.universe)}}</td>
                  <td>${{escapeHtml(st.category)}}</td>
                  <td>${{st.word_count.toLocaleString()}} words</td>
                </tr>
              `).join('')}}
            </tbody>
          </table>
        </div>

        <div class="catlinks">
          <strong>Categories:</strong>
          <ul>
            <li><a onclick="navigateTo('characters')">Fictional Characters</a></li>
            <li><a onclick="filterByUniverse('${{escapeHtml(primaryUniverse)}}')">${{escapeHtml(primaryUniverse)}} Characters</a></li>
          </ul>
        </div>
      `;

      document.getElementById('articleContainer').innerHTML = html;
    }}

    // Render A-Z Index
    function renderIndexPage(filterQuery = '') {{
      let filtered = database;
      if (filterQuery) {{
        const q = filterQuery.toLowerCase();
        filtered = database.filter(s => 
          s.title.toLowerCase().includes(q) || 
          s.universe.toLowerCase().includes(q) || 
          s.category.toLowerCase().includes(q) || 
          s.tier.toLowerCase().includes(q)
        );
      }}

      filtered.sort((a,b) => a.title.localeCompare(b.title));

      let letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');

      let html = `
        <h1 class="firstHeading">All Articles Index</h1>
        <div class="siteSub">From Fictionpedia, the free writing encyclopedia</div>
        <p>Showing <strong>${{filtered.length}}</strong> indexed articles.</p>

        <div class="index-letters">
          <button class="letter-btn" onclick="renderIndexPage('')">ALL</button>
          ${{letters.map(l => `<button class="letter-btn" onclick="filterByLetter('${{l}}')">${{l}}</button>`).join('')}}
        </div>

        <table class="index-table">
          <thead>
            <tr>
              <th>Article Title</th>
              <th>Universe</th>
              <th>Category</th>
              <th>Word Count</th>
              <th>Read Time</th>
            </tr>
          </thead>
          <tbody>
            ${{filtered.map(s => `
              <tr>
                <td><a onclick="navigateTo('article', '${{s.id}}')"><strong>${{escapeHtml(s.title)}}</strong></a></td>
                <td><a onclick="filterByUniverse('${{escapeHtml(s.universe)}}')">${{escapeHtml(s.universe)}}</a></td>
                <td>${{escapeHtml(s.category)}}</td>
                <td>${{s.word_count.toLocaleString()}} words</td>
                <td style="color:var(--wiki-text-muted);">${{s.read_time}}</td>
              </tr>
            `).join('')}}
          </tbody>
        </table>
      `;

      document.getElementById('articleContainer').innerHTML = html;
    }}

    function filterByLetter(letter) {{
      let filtered = database.filter(s => s.title.trim().toUpperCase().startsWith(letter));
      renderIndexPage(letter);
    }}

    function filterByUniverse(univ) {{
      renderUniversesPortal(univ);
    }}

    function goToRandomArticle() {{
      const randomStory = database[Math.floor(Math.random() * database.length)];
      navigateTo('article', randomStory.id);
    }}

    // Search Autocomplete
    function onSearchInput(query) {{
      const box = document.getElementById('searchSuggestions');
      if (!query || query.trim().length < 2) {{
        closeSuggestions();
        return;
      }}

      const q = query.toLowerCase();
      const matches = [];

      // Find story title matches
      database.forEach(s => {{
        if (s.title.toLowerCase().includes(q)) {{
          matches.push({{ type: 'story', title: s.title, id: s.id, meta: `${{s.universe}} • ${{s.word_count}}w` }});
        }}
      }});

      // Find character matches
      Object.keys(characterMap).forEach(c => {{
        if (c.toLowerCase().includes(q)) {{
          matches.push({{ type: 'char', title: c, id: c, meta: `Character in ${{characterMap[c].length}} works` }});
        }}
      }});

      if (!matches.length) {{
        box.innerHTML = `<div class="search-item" style="color:var(--wiki-text-muted);">No matching articles found.</div>`;
        box.style.display = 'block';
        return;
      }}

      box.innerHTML = matches.slice(0, 8).map((m, idx) => `
        <div class="search-item" onclick="selectSuggestion('${{m.type}}', '${{escapeHtml(m.id)}}')">
          <div>
            <div class="search-item-title">${{m.type === 'char' ? '👤 ' : '📄 '}}${{escapeHtml(m.title)}}</div>
            <div class="search-item-meta">${{escapeHtml(m.meta)}}</div>
          </div>
        </div>
      `).join('');

      box.style.display = 'block';
    }}

    function selectSuggestion(type, id) {{
      if (type === 'story') {{
        navigateTo('article', id);
      }} else if (type === 'char') {{
        navigateTo('character-bio', id);
      }}
      closeSuggestions();
    }}

    function closeSuggestions() {{
      const box = document.getElementById('searchSuggestions');
      box.style.display = 'none';
      box.innerHTML = '';
      document.getElementById('wikiSearchInput').value = '';
    }}

    function onSearchKey(e) {{
      if (e.key === 'Enter') {{
        const val = document.getElementById('wikiSearchInput').value;
        if (val) {{
          renderIndexPage(val);
          closeSuggestions();
        }}
      }}
    }}

    function formatStoryForReader(text) {{
      let lines = text.split('\\n');
      let html = '';
      let curPara = [];

      for (let line of lines) {{
        let trimmed = line.trim();
        if (!trimmed) {{
          if (curPara.length) {{
            html += `<p>${{escapeHtml(curPara.join(' '))}}</p>`;
            curPara = [];
          }}
          continue;
        }}

        if (trimmed.startsWith('#') || /^(?:Chapter|ACT|PROLOGUE|EPILOGUE|ISSUE|Story\\s+\\d+)/i.test(trimmed)) {{
          if (curPara.length) {{
            html += `<p>${{escapeHtml(curPara.join(' '))}}</p>`;
            curPara = [];
          }}
          let cleanH = trimmed.replace(/^#+\\s*/, '');
          html += `<h2 style="font-family:var(--font-serif); border-bottom:1px solid var(--wiki-border-light); padding-bottom:0.3rem; margin-top:2rem;">${{escapeHtml(cleanH)}}</h2>`;
        }} else {{
          curPara.push(trimmed);
        }}
      }}

      if (curPara.length) {{
        html += `<p>${{escapeHtml(curPara.join(' '))}}</p>`;
      }}

      return html;
    }}

    function toggleTheme() {{
      const current = document.body.getAttribute('data-theme');
      const next = current === 'dark' ? 'light' : 'dark';
      document.body.setAttribute('data-theme', next);
      document.getElementById('themeToggleBtn').innerText = next === 'dark' ? '☀️ Light' : '🌙 Dark';
    }}

    function exportArchive() {{
      const blob = new Blob([JSON.stringify(database, null, 2)], {{ type: 'application/json' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'fictionpedia_database.json';
      a.click();
      URL.revokeObjectURL(url);
    }}

    function escapeHtml(str) {{
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }}

    // Start on Main Page
    window.addEventListener('DOMContentLoaded', () => {{
      renderMainPage();
    }});
  </script>
</body>
</html>
"""

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[✓] Successfully generated Wikipedia-style Fictionpedia at {output_html}!")

if __name__ == '__main__':
    db = Path("fiction_database.json")
    out_idx = Path("index.html")
    out_wiki = Path("fiction_wiki.html")
    
    build_wikipedia_style_html(db, out_idx)
    build_wikipedia_style_html(db, out_wiki)
