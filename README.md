# ✦ Personal Fiction Wiki & Archive Vault

A comprehensive, automated, standalone personal wiki indexing your entire fiction writing archive, novels, serialized chapters, worldbuilding lore, screenplays, and character codex across your hard drive.

---

## 🚀 Quick Start: Viewing Your Wiki

Simply open [`index.html`](index.html) (or [`fiction_wiki.html`](fiction_wiki.html)) directly in any web browser (Chrome, Edge, Firefox, Brave, Safari). 

- **100% Offline & Standalone**: Requires no server, no internet connection, and zero dependencies.
- **Embedded Database**: Contains your full archive of indexed stories, chapters, excerpts, and searchable text.

---

## 📖 Key Features

1. **Instant Search & Deep Filtering**:
   - Real-time search across story titles, characters, universe names, and full story text.
   - Filter by **Universe / Saga**, **Category** (*Manuscript / Novel, Novella, Novelette, Short Story, Serialized Chapter, Worldbuilding & Lore, Screenplay*), and **Word Count Tier**.
2. **Universes & Sagas Hub**:
   - Automatically groups stories into their fictional universes (e.g. *The Dead Down Under*, *The Dead and the Signal*, *The Dead and the Rust*, *The Dead and the Sand*, *The Raven's Wake*, *Gravebound*, *The Head Wife / Proud Hopper*, *Unspoken Series*, *Reborn as Death's Right Hand Woman*, *Alpha Teams*, *Dead Ledger*, *Dating Among The Dead*, *Echos in the Wire*, *Ashen Path*, *Shard*, *Indigenous & Mythic Lore*).
3. **Character & Entity Codex**:
   - Discovers recurring character names and personas via dialogue attribution and entity extraction.
   - Click on any character to see every manuscript and chapter they appear in.
4. **Immersive Reader Mode**:
   - Built-in distraction-free reader with **Dark Slate**, **Clean Light**, **Sepia Parchment**, and **OLED Black** themes.
   - Font size scaling (`A-` / `A+`).
   - Interactive **Table of Contents** side drawer for chapters and scene breaks.
   - One-click **Print / PDF export**.
5. **Archive Analytics & Export**:
   - Total story count, total word counts, reading time estimates.
   - One-click **Export JSON** to back up the complete structured database.

---

## 🔄 Updating / Re-Scanning Your HDD

Whenever you write new chapters, edit stories, or create new manuscripts, re-run the builder:

```bash
# Scan default locations (Documents, Desktop, Downloads)
py build_wiki.py

# Or scan specific folder(s) / external drives:
py build_wiki.py "C:\Users\ketro\Documents\Stories" "D:\Writing" "Z:\Archives"
```

### Supported Formats
- Markdown (`.md`, `.markdown`)
- Plain Text (`.txt`)
- Microsoft Word (`.docx`)
- Rich Text (`.rtf`)
- E-Books (`.epub`)
- PDF Manuscripts (`.pdf`)

---

## 📁 File Structure
- [`index.html`](index.html) — Master single-file interactive Fiction Wiki.
- [`fiction_wiki.html`](fiction_wiki.html) — Duplicate standalone HTML copy for easy sharing or archiving.
- [`fiction_database.json`](fiction_database.json) — Full structured JSON dataset with all extracted metadata, word counts, and text.
- [`build_wiki.py`](build_wiki.py) — The Python indexing and HTML generator script.
