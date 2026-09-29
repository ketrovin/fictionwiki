import os
import sys
import re
import json
import zipfile
import html
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

try:
    import docx
except ImportError:
    docx = None

try:
    import pypdf
except ImportError:
    pypdf = None

EXCLUDE_DIRS = {
    'node_modules', '.git', '.venv', 'venv', '__pycache__', 'site-packages',
    'appdata', 'swarmui', 'comfyui', 'ruinedfooocus', 'wan2gp', 'sadtalker',
    'open-sora-plan', 'open-sora', 'jdk17', 'dedrm_tools', 'pip', 'wheel', 'dist', 'build',
    'bin', 'obj', '.gemini', 'miniconda3', 'anaconda3', 'cache', '.cache', 'packages',
    'assets', 'weights', 'checkpoints', 'lib', 'include', '100 for dummies series books collection',
    '100 for dummies series books collection pack-2', 'vid'
}

EXCLUDE_FILENAMES = {
    'requirements.txt', 'package.json', 'license.txt', 'license.md', 'license',
    'cm-cli.md', 'requirements_avatar.txt', 'merges.txt', 'genres_vocab.txt',
    'editorial_profile_template.md', 'skill.md', 'readme.md', 'changelog.md',
    'contributing.md', 'dockerfile', 'makefile', 'setup.py', 'test_mean_face.txt',
    'std_exp.txt', 'add own csv files here.txt', 'colors.txt', 'put your finetunes here.txt',
    'ref_voice.txt', 'pizzatime.txt', 'icon-attrib.txt', 'technical report'
}

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\r', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def strip_rtf(rtf_text: str) -> str:
    pattern = re.compile(r'\\([a-z]{1,32})(-?\d+)? ?|\\\'([0-9a-f]{2})|\\([^a-z])|([{}])|[\r\n]+|(.)', re.I)
    destinations = frozenset([
        'colortbl', 'fonttbl', 'generator', 'info', 'stylesheet', 'pict',
        'footer', 'footerf', 'footerl', 'footerr', 'header', 'headerf', 'headerl', 'headerr'
    ])
    stack = []
    ignorable = False
    out = []
    for match in pattern.finditer(rtf_text):
        word, arg, hex_char, char, brace, raw = match.groups()
        if brace:
            if brace == '{':
                stack.append(ignorable)
            elif brace == '}':
                if stack:
                    ignorable = stack.pop()
        elif word:
            if word in destinations:
                ignorable = True
            elif word in {'par', 'line', 'sect'}:
                if not ignorable:
                    out.append('\n')
            elif word == 'tab':
                if not ignorable:
                    out.append('\t')
        elif hex_char:
            if not ignorable:
                try:
                    c = bytes.fromhex(hex_char).decode('cp1252', errors='ignore')
                    out.append(c)
                except Exception:
                    pass
        elif raw:
            if not ignorable:
                out.append(raw)
    return "".join(out)

def read_file_content(path: Path) -> tuple[str, str]:
    ext = path.suffix.lower()
    if ext in {'.md', '.markdown', '.txt'}:
        encodings = ['utf-8', 'utf-8-sig', 'cp1252', 'latin-1']
        for enc in encodings:
            try:
                with open(path, 'r', encoding=enc, errors='replace') as f:
                    return clean_text(f.read()), ext[1:]
            except Exception:
                continue
        return "", ext[1:]

    elif ext == '.rtf':
        try:
            with open(path, 'r', encoding='latin-1', errors='ignore') as f:
                return clean_text(strip_rtf(f.read())), 'rtf'
        except Exception:
            return "", 'rtf'

    elif ext == '.docx' and docx is not None:
        try:
            doc = docx.Document(path)
            fullText = [para.text for para in doc.paragraphs if para.text.strip()]
            return clean_text("\n\n".join(fullText)), 'docx'
        except Exception:
            return "", 'docx'

    elif ext == '.pdf' and pypdf is not None:
        try:
            reader = pypdf.PdfReader(path)
            pages = []
            for p in reader.pages[:30]:
                text = p.extract_text()
                if text:
                    pages.append(text)
            return clean_text("\n\n".join(pages)), 'pdf'
        except Exception:
            return "", 'pdf'

    elif ext == '.epub':
        try:
            with zipfile.ZipFile(path, 'r') as z:
                html_files = [f for f in z.namelist() if f.endswith(('.html', '.xhtml', '.htm'))]
                text_parts = []
                for h in sorted(html_files):
                    content = z.read(h).decode('utf-8', errors='ignore')
                    plain = re.sub(r'<[^>]+>', ' ', content)
                    plain = re.sub(r'&[a-z0-9]+;', ' ', plain)
                    text_parts.append(plain)
                return clean_text("\n\n".join(text_parts)), 'epub'
        except Exception:
            return "", 'epub'

    return "", ext[1:]

def extract_entities(text: str) -> list[str]:
    dialogue_names = re.findall(r'(?i)\b(?:said|asked|whispered|shouted|replied|muttered|grunted|gasped|commanded)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', text)
    subj_names = re.findall(r'([A-Z][a-z]+)\s+(?:said|whispered|glanced|looked|nodded|stepped|smiled|frowned|turned|drew|sighed|remembered|paused|reached)', text)
    
    stopwords = {'The', 'He', 'She', 'They', 'It', 'Then', 'When', 'As', 'After', 'Before', 'His', 'Her', 'Their', 'One', 'There', 'Here', 'What', 'Who', 'How', 'Why', 'Someone', 'Everyone', 'No', 'Yes', 'Wait', 'Look', 'Chapter', 'Part', 'Act', 'Scene', 'Figure', 'Table', 'Section', 'Open-Sora', 'Loss', 'Model', 'Dataset', 'Batch', 'Step'}
    
    all_names = [n for n in dialogue_names + subj_names if n not in stopwords and len(n) > 2]
    counts = Counter(all_names)
    return [name for name, count in counts.most_common(8) if count >= 2]

def extract_chapters(text: str) -> list[dict]:
    chapters = []
    lines = text.split('\n')
    
    patterns = [
        r'^(?:#+\s*)?(?:Chapter|CHAPTER)\s+([0-9IVXLCDMivxlcdm]+|\w+)(?:[:\.\s—-]+(.*))?$',
        r'^(?:#+\s*)?(?:ACT|Act)\s+([0-9IVXLCDMivxlcdm]+)(?:[:\.\s—-]+(.*))?$',
        r'^(?:#+\s*)?(?:PROLOGUE|Prologue|EPILOGUE|Epilogue|INTERLUDE|Interlude)(?:[:\.\s—-]+(.*))?$',
        r'^(?:#+\s*)?(?:ISSUE|Issue)\s+([0-9IVXLCDMivxlcdm]+)(?:[:\.\s—-]+(.*))?$',
        r'^(?:#+\s*)?(?:Story\s+\d+[:\.\s—-]+.*)$',
        r'^#\s+([^#\n]+)$'
    ]
    
    for i, line in enumerate(lines):
        line_s = line.strip()
        if not line_s:
            continue
        for pat in patterns:
            m = re.match(pat, line_s, re.IGNORECASE)
            if m:
                title = line_s.lstrip('#').strip()
                if len(title) <= 80:
                    chapters.append({
                        'title': title,
                        'line': i,
                        'snippet': ""
                    })
                break
    return chapters

def infer_universe(path: Path, title: str) -> str:
    str_path = str(path).lower()
    title_lower = title.lower()

    if 'thedeaddownunder' in str_path or 'dead down under' in title_lower:
        return 'The Dead Down Under'
    if 'thedeadandtherust' in str_path or 'dead and the rust' in title_lower:
        return 'The Dead and the Rust'
    if 'thedeadandthesand' in str_path or 'dead and the sand' in title_lower:
        return 'The Dead and the Sand'
    if 'thedeadandthesignal' in str_path or 'dead and the signal' in title_lower or 'deadandthesignal' in str_path:
        return 'The Dead and the Signal'
    if 'gravebound' in str_path or 'gravebound' in title_lower:
        return 'Gravebound Universe'
    if 'proud-hopper' in str_path or 'proud_hopper' in str_path or 'proud hopper' in title_lower or 'head wife' in title_lower:
        return 'The Head Wife / Proud Hopper'
    if 'dating among the dead' in str_path or 'dating among the dead' in title_lower:
        return 'Dating Among The Dead'
    if 'dead ledger' in str_path or 'dead ledger' in title_lower:
        return 'Dead Ledger'
    if 'reborn as death' in str_path or 'reborn as death' in title_lower:
        return 'Reborn as Death\'s Right Hand Woman'
    if 'alpha teams' in str_path or 'alpha teams' in title_lower:
        return 'Alpha Teams Series'
    if 'unspoken' in str_path or 'unspoken' in title_lower or 'winter sanctuary' in title_lower:
        return 'Unspoken Series'
    if 'ashenpath' in str_path or 'ashen path' in str_path or 'ashen' in title_lower:
        return 'Ashen Path'
    if 'echosinthewire' in str_path or 'echos in the wire' in title_lower or 'echos in the wire' in str_path:
        return 'Echos in the Wire'
    if 'indigenize' in str_path or 'mikmaq' in str_path or 'yamatai' in title_lower or 'himeko' in title_lower:
        return 'Indigenous & Mythic Lore'
    if 'shard' in str_path or 'shard' in title_lower:
        return 'Shard Saga'
    if 'comix' in str_path or 'kaelen' in title_lower:
        return 'Comix & Character Profiles'
    if 'film ideas' in str_path or 'film_concepts' in str_path:
        return 'Screenplays & Concepts'
    if 'rpg' in str_path or 'curios' in str_path:
        return 'Tabletop & Curiosities'

    parent = path.parent.name
    if parent and parent.lower() not in {'stories', 'manuscripts', 'chapters', 'documents', 'desktop', 'downloads', 'projects', 'lore', 'wiki'}:
        return parent.replace('-', ' ').replace('_', ' ').title()
        
    return 'Standalone Works'

def infer_tags(text: str, universe: str, category: str) -> list[str]:
    tags = set()
    low_text = text.lower()
    
    if universe != 'Standalone Works':
        tags.add(universe)
        
    tags.add(category)
    
    if any(k in low_text for k in ['zombie', 'undead', 'infection', 'corpse', 'necro', 'rot', 'graveyard', 'grave', 'the dead']):
        tags.add('Post-Apocalyptic')
        tags.add('Horror / Outbreak')
    if any(k in low_text for k in ['cyber', 'neural', 'hacker', 'wire', 'terminal', 'ai', 'algorithm', 'drone', 'matrix']):
        tags.add('Cyberpunk / Sci-Fi')
    if any(k in low_text for k in ['sword', 'magic', 'sorcerer', 'realm', 'blade', 'emperor', 'clan', 'spell', 'dungeon']):
        tags.add('Fantasy')
    if any(k in low_text for k in ['detective', 'murder', 'investigation', 'case', 'crime', 'clue', 'alibi', 'ledger']):
        tags.add('Mystery / Noir')
    if any(k in low_text for k in ['date', 'romance', 'kiss', 'attraction', 'love', 'flirt', 'dating']):
        tags.add('Romance / Dark Comedy')
    if any(k in low_text for k in ['mikmaq', 'indigenous', 'treaty', 'sacred', 'elder', 'tribe', 'yamatai', 'spirit']):
        tags.add('Mythic & Indigenous Lore')
    if any(k in low_text for k in ['screenplay', 'int.', 'ext.', 'cut to:', 'fade in:']):
        tags.add('Screenplay')
    if any(k in low_text for k in ['rpg', 'd20', 'stat', 'item', 'inventory', 'quest', 'curio']):
        tags.add('RPG / World Codex')
        
    return sorted(list(tags))

def get_word_count_tier(word_count: int) -> str:
    if word_count < 1000:
        return "Flash (< 1k words)"
    elif word_count < 7500:
        return "Short Story (1k – 7.5k)"
    elif word_count < 17500:
        return "Novelette (7.5k – 17.5k)"
    elif word_count < 40000:
        return "Novella (17.5k – 40k)"
    else:
        return "Novel / Epic (40k+ words)"

def extract_title(text: str, path: Path) -> str:
    m = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
    if m:
        t = m.group(1).strip()
        if len(t) < 80 and not t.lower().startswith('chapter'):
            return t

    clean_stem = path.stem.replace('_', ' ').replace('-', ' ').strip()
    clean_stem = re.sub(r'^(?i)chapter\s+(\d+)\s+', r'Chapter \1: ', clean_stem)
    return clean_stem.title()

def scan_all_fiction(scan_paths: list[Path]) -> list[dict]:
    print(f"[*] Beginning fiction archive scan across {len(scan_paths)} roots...", flush=True)
    stories = []
    seen_hashes = set()
    
    for root_dir in scan_paths:
        if not root_dir.exists():
            continue
        print(f"[*] Scanning root: {root_dir}", flush=True)
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d.lower() not in EXCLUDE_DIRS]
            
            path_parts = [p.lower() for p in Path(root).parts]
            if any(bad in path_parts for bad in EXCLUDE_DIRS):
                continue
                
            for f in files:
                if f.lower() in EXCLUDE_FILENAMES:
                    continue
                ext = Path(f).suffix.lower()
                if ext in {'.md', '.markdown', '.txt', '.docx', '.rtf', '.epub', '.pdf'}:
                    file_path = Path(root) / f
                    
                    try:
                        stat = file_path.stat()
                        size = stat.st_size
                        if size < 80:
                            continue
                            
                        content, fmt = read_file_content(file_path)
                        if not content or len(content) < 100:
                            continue
                            
                        # Quick hash deduplication for exact copies
                        content_sample = content[:300] + str(len(content))
                        if content_sample in seen_hashes:
                            continue
                        seen_hashes.add(content_sample)
                        
                        words = content.split()
                        word_count = len(words)
                        if word_count < 20:
                            continue
                            
                        lower_c = content.lower()
                        # Strict code/AI paper exclusion
                        if ('import ' in lower_c[:300] and 'def ' in lower_c[:300] and 'return ' in lower_c[:500]) or \
                           ('npm install' in lower_c[:500]) or ('git clone' in lower_c[:300] and 'pip install' in lower_c[:500]) or \
                           ('video autoencoder' in lower_c[:500]) or ('open-sora' in lower_c[:500]) or ('wan2gp' in lower_c[:500]):
                            continue
                            
                        if 'profile' in file_path.stem.lower() or 'concept' in file_path.stem.lower() or 'guide' in file_path.stem.lower() or 'notes' in file_path.stem.lower() or 'curios' in file_path.stem.lower() or 'bestiary' in file_path.stem.lower() or 'lore' in file_path.stem.lower():
                            category = "Worldbuilding & Lore"
                        elif 'film' in file_path.stem.lower() or bool(re.search(r'(?m)^(INT\.|EXT\.|FADE IN:)', content[:1500])):
                            category = "Screenplay / Script"
                        elif re.search(r'(?i)chapter|issue|story\s+\d+|ch\d+', file_path.stem):
                            category = "Serialized Chapter"
                        elif word_count >= 40000:
                            category = "Manuscript / Novel"
                        elif word_count >= 17500:
                            category = "Novella"
                        elif word_count >= 7500:
                            category = "Novelette"
                        elif word_count >= 1000:
                            category = "Short Story"
                        else:
                            category = "Flash Fiction / Scene"

                        title = extract_title(content, file_path)
                        universe = infer_universe(file_path, title)
                        tags = infer_tags(content, universe, category)
                        characters = extract_entities(content)
                        chapters = extract_chapters(content)
                        tier = get_word_count_tier(word_count)
                        
                        read_mins = max(1, round(word_count / 225))
                        read_time_str = f"{read_mins} min read" if read_mins < 60 else f"{read_mins//60}h {read_mins%60}m read"
                        
                        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip() and not p.strip().startswith('#')]
                        excerpt = " ".join(paragraphs[:3])[:450]
                        if len(excerpt) == 450:
                            excerpt += "..."

                        story_id = re.sub(r'[^a-zA-Z0-9_-]', '_', file_path.stem).lower() + f"_{len(stories)}"
                        mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                        
                        stories.append({
                            'id': story_id,
                            'title': title,
                            'universe': universe,
                            'category': category,
                            'word_count': word_count,
                            'char_count': len(content),
                            'tier': tier,
                            'read_time': read_time_str,
                            'read_mins': read_mins,
                            'format': fmt.upper(),
                            'size_kb': round(size / 1024, 1),
                            'last_modified': mtime,
                            'file_path': str(file_path),
                            'filename': file_path.name,
                            'tags': tags,
                            'characters': characters,
                            'chapters': chapters,
                            'excerpt': excerpt,
                            'content': content
                        })
                        print(f"  [+] Indexed ({category}): {title} [{universe}] - {word_count:,} words", flush=True)
                    except Exception:
                        pass

    print(f"\n[✓] Total indexed creative fiction works: {len(stories)}", flush=True)
    return stories

def generate_html_wiki(stories: list[dict], output_path: Path):
    print(f"[*] Generating standalone HTML Fiction Wiki at {output_path}...", flush=True)
    
    total_words = sum(s['word_count'] for s in stories)
    total_fiction_count = len(stories)
    
    universes = Counter(s['universe'] for s in stories)
    categories = Counter(s['category'] for s in stories)
    
    char_map = defaultdict(list)
    for s in stories:
        for c in s['characters']:
            char_map[c].append({'id': s['id'], 'title': s['title'], 'universe': s['universe']})
    
    json_data = json.dumps(stories, ensure_ascii=False)
    
    html_template = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Personal Fiction Wiki & Archive Vault</title>
  <style>
    :root {{
      --bg-base: #0a0d14;
      --bg-surface: #111827;
      --bg-card: #1a2234;
      --bg-hover: #26334a;
      --border: #2e3d56;
      --border-focus: #6366f1;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --accent: #6366f1;
      --accent-hover: #4f46e5;
      --accent-glow: rgba(99, 102, 241, 0.25);
      --badge-bg: rgba(99, 102, 241, 0.15);
      --badge-text: #a5b4fc;
      --reader-bg: #0a0d14;
      --reader-text: #e2e8f0;
      --reader-font: "Charter", "Georgia", "Cambria", serif;
      --reader-size: 1.15rem;
      --reader-line: 1.85;
      --reader-max-w: 800px;
    }}

    [data-theme="light"] {{
      --bg-base: #f8fafc;
      --bg-surface: #ffffff;
      --bg-card: #f1f5f9;
      --bg-hover: #e2e8f0;
      --border: #cbd5e1;
      --border-focus: #4f46e5;
      --text-main: #0f172a;
      --text-muted: #64748b;
      --accent: #4f46e5;
      --accent-hover: #4338ca;
      --accent-glow: rgba(79, 70, 229, 0.15);
      --badge-bg: #e0e7ff;
      --badge-text: #3730a3;
      --reader-bg: #ffffff;
      --reader-text: #1e293b;
    }}

    [data-theme="sepia"] {{
      --bg-base: #f5eedb;
      --bg-surface: #ede3cc;
      --bg-card: #e2d6bc;
      --bg-hover: #d5c7a9;
      --border: #c4b596;
      --border-focus: #8b5cf6;
      --text-main: #3e2f1d;
      --text-muted: #725e46;
      --accent: #935a24;
      --accent-hover: #784518;
      --accent-glow: rgba(147, 90, 36, 0.2);
      --badge-bg: #d9c5ab;
      --badge-text: #4a2c0c;
      --reader-bg: #f5eedb;
      --reader-text: #3e2f1d;
    }}

    [data-theme="oled"] {{
      --bg-base: #000000;
      --bg-surface: #0a0a0a;
      --bg-card: #121212;
      --bg-hover: #1c1c1c;
      --border: #262626;
      --border-focus: #00ffaa;
      --text-main: #ffffff;
      --text-muted: #888888;
      --accent: #00ffaa;
      --accent-hover: #00cc88;
      --accent-glow: rgba(0, 255, 170, 0.25);
      --badge-bg: rgba(0, 255, 170, 0.15);
      --badge-text: #00ffaa;
      --reader-bg: #000000;
      --reader-text: #f0f0f0;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background-color: var(--bg-base);
      color: var(--text-main);
      line-height: 1.6;
      transition: background-color 0.25s ease, color 0.25s ease;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}

    header {{
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 40;
      backdrop-filter: blur(12px);
    }}

    .nav-container {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 0.85rem 1.5rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
    }}

    .logo-area {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      cursor: pointer;
    }}

    .logo-badge {{
      width: 40px;
      height: 40px;
      border-radius: 10px;
      background: linear-gradient(135deg, var(--accent), #ec4899);
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-weight: 800;
      font-size: 1.25rem;
      box-shadow: 0 4px 12px var(--accent-glow);
    }}

    .logo-title {{
      font-size: 1.25rem;
      font-weight: 800;
      letter-spacing: -0.02em;
    }}

    .logo-sub {{
      font-size: 0.75rem;
      color: var(--text-muted);
    }}

    .nav-tabs {{
      display: flex;
      gap: 0.5rem;
      background: var(--bg-card);
      padding: 0.3rem;
      border-radius: 8px;
      border: 1px solid var(--border);
    }}

    .tab-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 0.5rem 1rem;
      border-radius: 6px;
      font-size: 0.875rem;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.4rem;
      transition: all 0.2s ease;
    }}

    .tab-btn.active, .tab-btn:hover {{
      color: var(--text-main);
      background: var(--bg-hover);
    }}

    .tab-btn.active {{
      background: var(--accent);
      color: #ffffff;
    }}

    .nav-controls {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}

    .icon-btn {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      color: var(--text-main);
      padding: 0.5rem 0.85rem;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.85rem;
      display: flex;
      align-items: center;
      gap: 0.4rem;
      transition: all 0.2s ease;
    }}

    .icon-btn:hover {{
      background: var(--bg-hover);
      border-color: var(--border-focus);
    }}

    main {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 1.75rem;
      flex: 1;
      width: 100%;
    }}

    .hero-stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1rem;
      margin-bottom: 2rem;
    }}

    .stat-card {{
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.25rem 1.5rem;
      position: relative;
      overflow: hidden;
      box-shadow: 0 4px 16px rgba(0,0,0,0.15);
    }}

    .stat-card::after {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 4px;
      height: 100%;
      background: var(--accent);
    }}

    .stat-label {{
      font-size: 0.8rem;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 700;
      letter-spacing: 0.05em;
    }}

    .stat-value {{
      font-size: 1.85rem;
      font-weight: 800;
      margin-top: 0.25rem;
      color: var(--text-main);
    }}

    .stat-desc {{
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-top: 0.25rem;
    }}

    .controls-panel {{
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.25rem;
      margin-bottom: 2rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }}

    .search-row {{
      display: flex;
      gap: 0.75rem;
    }}

    .search-box {{
      flex: 1;
      position: relative;
    }}

    .search-input {{
      width: 100%;
      padding: 0.85rem 1rem 0.85rem 3rem;
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 8px;
      color: var(--text-main);
      font-size: 1rem;
      outline: none;
      transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }}

    .search-input:focus {{
      border-color: var(--border-focus);
      box-shadow: 0 0 0 3px var(--accent-glow);
    }}

    .search-icon {{
      position: absolute;
      left: 1.1rem;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
      font-size: 1.1rem;
    }}

    .filter-chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      align-items: center;
    }}

    .chip-label {{
      font-size: 0.82rem;
      color: var(--text-muted);
      font-weight: 700;
      margin-right: 0.25rem;
    }}

    .chip {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 0.4rem 0.85rem;
      border-radius: 20px;
      font-size: 0.82rem;
      cursor: pointer;
      transition: all 0.2s ease;
    }}

    .chip:hover, .chip.active {{
      background: var(--accent);
      border-color: var(--accent);
      color: white;
    }}

    .view-toggle {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.25rem;
    }}

    .results-count {{
      font-size: 0.95rem;
      color: var(--text-muted);
      font-weight: 500;
    }}

    .story-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 1.35rem;
    }}

    .story-card {{
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.35rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 1rem;
      transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
      cursor: pointer;
      position: relative;
    }}

    .story-card:hover {{
      transform: translateY(-3px);
      border-color: var(--border-focus);
      box-shadow: 0 10px 28px rgba(0,0,0,0.35);
    }}

    .card-universe {{
      font-size: 0.75rem;
      font-weight: 700;
      color: var(--badge-text);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}

    .card-title {{
      font-size: 1.2rem;
      font-weight: 800;
      margin-top: 0.25rem;
      line-height: 1.35;
      color: var(--text-main);
    }}

    .card-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-top: 0.6rem;
    }}

    .meta-badge {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      font-size: 0.75rem;
      padding: 0.25rem 0.55rem;
      border-radius: 5px;
      color: var(--text-muted);
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
    }}

    .card-excerpt {{
      font-size: 0.88rem;
      color: var(--text-muted);
      line-height: 1.55;
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      overflow: hidden;
      font-style: italic;
    }}

    .card-chars {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
    }}

    .char-tag {{
      background: var(--badge-bg);
      color: var(--badge-text);
      font-size: 0.74rem;
      padding: 0.2rem 0.5rem;
      border-radius: 12px;
      font-weight: 500;
    }}

    .card-footer {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-top: 1px solid var(--border);
      padding-top: 0.85rem;
      font-size: 0.78rem;
      color: var(--text-muted);
    }}

    .read-btn {{
      background: var(--accent);
      color: white;
      border: none;
      padding: 0.45rem 1rem;
      border-radius: 6px;
      font-weight: 700;
      font-size: 0.82rem;
      cursor: pointer;
      transition: background 0.2s ease;
    }}

    .read-btn:hover {{
      background: var(--accent-hover);
    }}

    .universe-section {{
      margin-bottom: 3rem;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.5rem;
    }}

    .universe-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1.25rem;
      padding-bottom: 0.75rem;
      border-bottom: 2px solid var(--border);
    }}

    .universe-title {{
      font-size: 1.45rem;
      font-weight: 800;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}

    .codex-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 1.25rem;
    }}

    .codex-card {{
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.25rem;
      transition: border-color 0.2s ease;
    }}

    .codex-card:hover {{
      border-color: var(--border-focus);
    }}

    .codex-name {{
      font-size: 1.15rem;
      font-weight: 800;
      color: var(--text-main);
      margin-bottom: 0.6rem;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }}

    .codex-stories {{
      display: flex;
      flex-direction: column;
      gap: 0.45rem;
      max-height: 240px;
      overflow-y: auto;
    }}

    .codex-link {{
      font-size: 0.85rem;
      color: var(--badge-text);
      text-decoration: none;
      cursor: pointer;
      padding: 0.25rem 0.4rem;
      border-radius: 4px;
      transition: background 0.15s ease;
    }}

    .codex-link:hover {{
      background: var(--bg-hover);
      text-decoration: underline;
    }}

    .reader-modal {{
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: var(--reader-bg);
      color: var(--reader-text);
      z-index: 100;
      display: none;
      flex-direction: column;
      overflow-y: auto;
    }}

    .reader-modal.active {{
      display: flex;
    }}

    .reader-nav {{
      position: sticky;
      top: 0;
      background: var(--reader-bg);
      border-bottom: 1px solid var(--border);
      padding: 0.85rem 1.75rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      backdrop-filter: blur(12px);
      z-index: 10;
    }}

    .reader-title-area {{
      display: flex;
      flex-direction: column;
      max-width: 55%;
    }}

    .reader-story-title {{
      font-size: 1.2rem;
      font-weight: 800;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .reader-story-meta {{
      font-size: 0.8rem;
      color: var(--text-muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .reader-tools {{
      display: flex;
      align-items: center;
      gap: 0.6rem;
    }}

    .reader-content-wrap {{
      max-width: var(--reader-max-w);
      margin: 0 auto;
      padding: 3.5rem 1.5rem 7rem;
      font-family: var(--reader-font);
      font-size: var(--reader-size);
      line-height: var(--reader-line);
      width: 100%;
    }}

    .reader-content-wrap h1, .reader-content-wrap h2, .reader-content-wrap h3 {{
      font-family: system-ui, -apple-system, sans-serif;
      margin: 2.5rem 0 1.25rem;
      line-height: 1.3;
      color: var(--text-main);
    }}

    .reader-content-wrap p {{
      margin-bottom: 1.45rem;
      text-indent: 1.6em;
    }}

    .reader-content-wrap p:first-of-type, .reader-content-wrap h2 + p, .reader-content-wrap h3 + p {{
      text-indent: 0;
    }}

    .reader-content-wrap hr {{
      border: 0;
      height: 1px;
      background: var(--border);
      margin: 2.5rem auto;
      width: 40%;
      text-align: center;
    }}

    .reader-content-wrap blockquote {{
      background: var(--bg-card);
      border-left: 4px solid var(--accent);
      padding: 1rem 1.25rem;
      margin: 1.75rem 0;
      font-style: italic;
      text-indent: 0;
      border-radius: 0 8px 8px 0;
    }}

    .toc-drawer {{
      position: fixed;
      right: 0;
      top: 65px;
      bottom: 0;
      width: 340px;
      background: var(--bg-surface);
      border-left: 1px solid var(--border);
      padding: 1.5rem;
      overflow-y: auto;
      transform: translateX(100%);
      transition: transform 0.3s ease;
      z-index: 20;
      box-shadow: -6px 0 20px rgba(0,0,0,0.3);
    }}

    .toc-drawer.open {{
      transform: translateX(0);
    }}

    .toc-item {{
      padding: 0.6rem 0.5rem;
      border-bottom: 1px solid var(--border);
      font-size: 0.88rem;
      cursor: pointer;
      color: var(--text-muted);
      transition: color 0.15s ease, background 0.15s ease;
      border-radius: 4px;
    }}

    .toc-item:hover {{
      color: var(--accent);
      background: var(--bg-hover);
    }}

    @media print {{
      header, .controls-panel, .hero-stats, .reader-nav {{
        display: none !important;
      }}
      .reader-modal {{
        position: static;
        display: block !important;
        background: white !important;
        color: black !important;
      }}
      .reader-content-wrap {{
        max-width: 100% !important;
        padding: 0 !important;
        font-size: 11pt !important;
        line-height: 1.5 !important;
      }}
    }}
  </style>
</head>
<body data-theme="dark">

  <header>
    <div class="nav-container">
      <div class="logo-area" onclick="showView('all')">
        <div class="logo-badge">✦</div>
        <div>
          <div class="logo-title">Fiction Archive & Wiki</div>
          <div class="logo-sub">Comprehensive Personal Writing Vault</div>
        </div>
      </div>

      <nav class="nav-tabs">
        <button class="tab-btn active" id="tab-all" onclick="showView('all')">📚 All Works</button>
        <button class="tab-btn" id="tab-universes" onclick="showView('universes')">🌌 Universes & Sagas</button>
        <button class="tab-btn" id="tab-codex" onclick="showView('codex')">👥 Character Codex</button>
      </nav>

      <div class="nav-controls">
        <select class="icon-btn" id="themeSelect" onchange="changeTheme(this.value)">
          <option value="dark">🌙 Dark Slate</option>
          <option value="light">☀️ Clean Light</option>
          <option value="sepia">📜 Sepia Parchment</option>
          <option value="oled">🖤 OLED Black</option>
        </select>
        <button class="icon-btn" onclick="exportData()" title="Export JSON Database">📥 Export Archive</button>
      </div>
    </div>
  </header>

  <main>
    <section class="hero-stats">
      <div class="stat-card">
        <div class="stat-label">Total Creative Works</div>
        <div class="stat-value">{total_fiction_count}</div>
        <div class="stat-desc">Novels, novellas, serialized chapters & lore</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Total Archive Words</div>
        <div class="stat-value">{total_words:,}</div>
        <div class="stat-desc">Across all written manuscripts & sagas</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Story Universes</div>
        <div class="stat-value">{len(universes)}</div>
        <div class="stat-desc">Distinct fictional worlds & series</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Character Codex</div>
        <div class="stat-value">{len(char_map)}</div>
        <div class="stat-desc">Named characters & entities tracked</div>
      </div>
    </section>

    <section class="controls-panel" id="filterControls">
      <div class="search-row">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input type="text" id="searchInput" class="search-input" placeholder="Instant search across titles, characters, full story text, dialogue, or universe..." oninput="handleSearch()">
        </div>
      </div>
      
      <div class="filter-chips" id="universeFilters">
        <span class="chip-label">Universe:</span>
        <button class="chip active" onclick="setFilter('universe', 'ALL')">All Universes</button>
        {"".join([f'<button class="chip" onclick="setFilter(\'universe\', \'{html.escape(u)}\')">{html.escape(u)} ({count})</button>' for u, count in universes.most_common(9)])}
      </div>

      <div class="filter-chips" id="categoryFilters">
        <span class="chip-label">Category:</span>
        <button class="chip active" onclick="setFilter('category', 'ALL')">All Categories</button>
        {"".join([f'<button class="chip" onclick="setFilter(\'category\', \'{html.escape(c)}\')">{html.escape(c)} ({count})</button>' for c, count in categories.items()])}
      </div>

      <div class="filter-chips" id="tierFilters">
        <span class="chip-label">Length:</span>
        <button class="chip active" onclick="setFilter('tier', 'ALL')">All Lengths</button>
        <button class="chip" onclick="setFilter('tier', 'Novel / Epic (40k+ words)')">Novel (40k+)</button>
        <button class="chip" onclick="setFilter('tier', 'Novella (17.5k – 40k)')">Novella</button>
        <button class="chip" onclick="setFilter('tier', 'Novelette (7.5k – 17.5k)')">Novelette</button>
        <button class="chip" onclick="setFilter('tier', 'Short Story (1k – 7.5k)')">Short Story</button>
        <button class="chip" onclick="setFilter('tier', 'Flash (< 1k words)')">Flash</button>
      </div>
    </section>

    <div id="catalogView">
      <div class="view-toggle">
        <div class="results-count" id="resultsCount">Showing {len(stories)} documents</div>
        <div>
          <label style="font-size:0.85rem; color:var(--text-muted); margin-right:0.5rem;">Sort by:</label>
          <select class="icon-btn" id="sortSelect" onchange="renderCatalog()">
            <option value="words-desc">Word Count (Highest first)</option>
            <option value="words-asc">Word Count (Lowest first)</option>
            <option value="title-asc">Title (A-Z)</option>
            <option value="modified-desc">Recently Modified</option>
          </select>
        </div>
      </div>

      <div class="story-grid" id="storyGrid"></div>
    </div>

    <div id="universeView" style="display:none;"></div>

    <div id="codexView" style="display:none;">
      <h2 style="margin-bottom:1.5rem;">👥 Character & Entity Codex</h2>
      <div class="codex-grid" id="codexGrid"></div>
    </div>
  </main>

  <div class="reader-modal" id="readerModal">
    <div class="reader-nav">
      <div class="reader-title-area">
        <div class="reader-story-title" id="readerTitle">Story Title</div>
        <div class="reader-story-meta" id="readerMeta">Universe • 0 words • 0 min read</div>
      </div>
      <div class="reader-tools">
        <button class="icon-btn" onclick="toggleToc()">📑 Table of Contents</button>
        <button class="icon-btn" onclick="adjustFontSize(-1)">A-</button>
        <button class="icon-btn" onclick="adjustFontSize(1)">A+</button>
        <button class="icon-btn" onclick="window.print()">🖨️ Print / PDF</button>
        <button class="icon-btn" onclick="closeReader()" style="background:var(--accent); color:white;">✕ Close</button>
      </div>
    </div>

    <div class="toc-drawer" id="tocDrawer">
      <h3 style="margin-bottom:1rem;">Table of Contents</h3>
      <div id="tocList"></div>
    </div>

    <div class="reader-content-wrap" id="readerBody"></div>
  </div>

  <script>
    const database = {json_data};
    let currentFilter = {{
      universe: 'ALL',
      category: 'ALL',
      tier: 'ALL',
      search: ''
    }};

    let currentStory = null;
    let readerFontSize = 1.15;

    function renderCatalog() {{
      const grid = document.getElementById('storyGrid');
      const sortType = document.getElementById('sortSelect').value;
      
      let filtered = database.filter(item => {{
        if (currentFilter.universe !== 'ALL' && item.universe !== currentFilter.universe) return false;
        if (currentFilter.category !== 'ALL' && item.category !== currentFilter.category) return false;
        if (currentFilter.tier !== 'ALL' && item.tier !== currentFilter.tier) return false;
        if (currentFilter.search) {{
          const q = currentFilter.search.toLowerCase();
          const matchTitle = item.title.toLowerCase().includes(q);
          const matchExcerpt = item.excerpt.toLowerCase().includes(q);
          const matchUniv = item.universe.toLowerCase().includes(q);
          const matchChars = item.characters.some(c => c.toLowerCase().includes(q));
          const matchContent = item.content.toLowerCase().includes(q);
          if (!matchTitle && !matchExcerpt && !matchUniv && !matchChars && !matchContent) return false;
        }}
        return true;
      }});

      filtered.sort((a, b) => {{
        if (sortType === 'words-desc') return b.word_count - a.word_count;
        if (sortType === 'words-asc') return a.word_count - b.word_count;
        if (sortType === 'title-asc') return a.title.localeCompare(b.title);
        if (sortType === 'modified-desc') return b.last_modified.localeCompare(a.last_modified);
        return 0;
      }});

      document.getElementById('resultsCount').innerText = `Showing ${{filtered.length}} of ${{database.length}} documents`;

      grid.innerHTML = filtered.map(item => `
        <div class="story-card" onclick="openReader('${{item.id}}')">
          <div>
            <div class="card-universe">${{escapeHtml(item.universe)}}</div>
            <div class="card-title">${{escapeHtml(item.title)}}</div>
            
            <div class="card-meta">
              <span class="meta-badge">📖 ${{item.word_count.toLocaleString()}} words</span>
              <span class="meta-badge">⏱️ ${{item.read_time}}</span>
              <span class="meta-badge">📁 ${{item.format}}</span>
              <span class="meta-badge">🏷️ ${{item.category}}</span>
            </div>

            <p class="card-excerpt" style="margin-top:0.85rem;">${{escapeHtml(item.excerpt)}}</p>
          </div>

          <div>
            ${{item.characters && item.characters.length ? `
              <div class="card-chars" style="margin-bottom:0.85rem;">
                ${{item.characters.slice(0, 5).map(c => `<span class="char-tag">👤 ${{escapeHtml(c)}}</span>`).join('')}}
              </div>
            ` : ''}}

            <div class="card-footer">
              <span>📅 ${{item.last_modified}}</span>
              <button class="read-btn" onclick="event.stopPropagation(); openReader('${{item.id}}')">Read Story →</button>
            </div>
          </div>
        </div>
      `).join('');
    }}

    function renderUniverses() {{
      const container = document.getElementById('universeView');
      const groups = {{}};
      
      database.forEach(item => {{
        if (!groups[item.universe]) groups[item.universe] = [];
        groups[item.universe].push(item);
      }});

      container.innerHTML = Object.keys(groups).sort((a,b) => groups[b].length - groups[a].length).map(univ => {{
        const stories = groups[univ].sort((a,b) => b.word_count - a.word_count);
        const univWords = stories.reduce((sum, s) => sum + s.word_count, 0);
        return `
          <div class="universe-section">
            <div class="universe-header">
              <div class="universe-title">🌌 ${{escapeHtml(univ)}}</div>
              <div style="font-size:0.9rem; color:var(--text-muted); font-weight:600;">${{stories.length}} works • ${{univWords.toLocaleString()}} total words</div>
            </div>
            <div class="story-grid">
              ${{stories.map(item => `
                <div class="story-card" onclick="openReader('${{item.id}}')">
                  <div>
                    <div class="card-title">${{escapeHtml(item.title)}}</div>
                    <div class="card-meta">
                      <span class="meta-badge">📖 ${{item.word_count.toLocaleString()}} words</span>
                      <span class="meta-badge">⏱️ ${{item.read_time}}</span>
                      <span class="meta-badge">🏷️ ${{item.category}}</span>
                    </div>
                    <p class="card-excerpt" style="margin-top:0.75rem;">${{escapeHtml(item.excerpt)}}</p>
                  </div>
                  <div class="card-footer">
                    <span>📅 ${{item.last_modified}}</span>
                    <button class="read-btn" onclick="event.stopPropagation(); openReader('${{item.id}}')">Read →</button>
                  </div>
                </div>
              `).join('')}}
            </div>
          </div>
        `;
      }}).join('');
    }}

    function renderCodex() {{
      const container = document.getElementById('codexGrid');
      const charMap = {{}};
      
      database.forEach(item => {{
        item.characters.forEach(c => {{
          if (!charMap[c]) charMap[c] = [];
          charMap[c].push(item);
        }});
      }});

      const sortedChars = Object.keys(charMap).sort((a,b) => charMap[b].length - charMap[a].length);

      container.innerHTML = sortedChars.map(c => `
        <div class="codex-card">
          <div class="codex-name">👤 ${{escapeHtml(c)}}</div>
          <div style="font-size:0.8rem; color:var(--text-muted); margin-bottom:0.6rem;">Appears across ${{charMap[c].length}} manuscript(s):</div>
          <div class="codex-stories">
            ${{charMap[c].map(s => `
              <div class="codex-link" onclick="openReader('${{s.id}}')">📖 ${{escapeHtml(s.title)}} <span style="color:var(--text-muted)">(${{escapeHtml(s.universe)}})</span></div>
            `).join('')}}
          </div>
        </div>
      `).join('');
    }}

    function showView(view) {{
      document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
      document.getElementById('catalogView').style.display = view === 'all' ? 'block' : 'none';
      document.getElementById('filterControls').style.display = view === 'all' ? 'flex' : 'none';
      document.getElementById('universeView').style.display = view === 'universes' ? 'block' : 'none';
      document.getElementById('codexView').style.display = view === 'codex' ? 'block' : 'none';

      if (view === 'all') {{
        document.getElementById('tab-all').classList.add('active');
        renderCatalog();
      }} else if (view === 'universes') {{
        document.getElementById('tab-universes').classList.add('active');
        renderUniverses();
      }} else if (view === 'codex') {{
        document.getElementById('tab-codex').classList.add('active');
        renderCodex();
      }}
    }}

    function setFilter(type, value) {{
      currentFilter[type] = value;
      const parent = type === 'universe' ? 'universeFilters' : type === 'category' ? 'categoryFilters' : 'tierFilters';
      document.querySelectorAll(`#${{parent}} .chip`).forEach(chip => {{
        if ((value === 'ALL' && chip.innerText.startsWith('All')) || chip.innerText.startsWith(value)) {{
          chip.classList.add('active');
        }} else {{
          chip.classList.remove('active');
        }}
      }});
      renderCatalog();
    }}

    function handleSearch() {{
      currentFilter.search = document.getElementById('searchInput').value;
      renderCatalog();
    }}

    function openReader(storyId) {{
      const story = database.find(s => s.id === storyId);
      if (!story) return;
      currentStory = story;

      document.getElementById('readerTitle').innerText = story.title;
      document.getElementById('readerMeta').innerText = `${{story.universe}} • ${{story.word_count.toLocaleString()}} words • ${{story.read_time}} • ${{story.file_path}}`;
      
      const formatted = formatStoryContent(story.content);
      document.getElementById('readerBody').innerHTML = formatted;
      
      const tocList = document.getElementById('tocList');
      if (story.chapters && story.chapters.length) {{
        tocList.innerHTML = story.chapters.map((ch, idx) => `
          <div class="toc-item" onclick="scrollToChapter('ch-${{idx}}')">📌 ${{escapeHtml(ch.title)}}</div>
        `).join('');
      }} else {{
        tocList.innerHTML = '<div style="color:var(--text-muted); font-size:0.85rem;">No explicit chapter breaks detected.</div>';
      }}

      document.getElementById('readerModal').classList.add('active');
      document.getElementById('readerModal').scrollTop = 0;
    }}

    function closeReader() {{
      document.getElementById('readerModal').classList.remove('active');
      document.getElementById('tocDrawer').classList.remove('open');
    }}

    function toggleToc() {{
      document.getElementById('tocDrawer').classList.toggle('open');
    }}

    function scrollToChapter(chId) {{
      const el = document.getElementById(chId);
      if (el) el.scrollIntoView({{ behavior: 'smooth' }});
      document.getElementById('tocDrawer').classList.remove('open');
    }}

    function adjustFontSize(delta) {{
      readerFontSize = Math.max(0.85, Math.min(2.0, readerFontSize + delta * 0.1));
      document.documentElement.style.setProperty('--reader-size', `${{readerFontSize}}rem`);
    }}

    function changeTheme(theme) {{
      document.body.setAttribute('data-theme', theme);
    }}

    function formatStoryContent(text) {{
      let chIdx = 0;
      const lines = text.split('\\n');
      let html = '';
      let curPara = [];

      for (let line of lines) {{
        const trimmed = line.trim();
        if (!trimmed) {{
          if (curPara.length) {{
            html += `<p>${{formatInline(escapeHtml(curPara.join(' ')))}}</p>`;
            curPara = [];
          }}
          continue;
        }}

        if (trimmed.startsWith('#') || /^(?:Chapter|ACT|PROLOGUE|EPILOGUE|ISSUE|Story\\s+\\d+)/i.test(trimmed)) {{
          if (curPara.length) {{
            html += `<p>${{formatInline(escapeHtml(curPara.join(' ')))}}</p>`;
            curPara = [];
          }}
          const cleanH = trimmed.replace(/^#+\\s*/, '');
          html += `<h2 id="ch-${{chIdx++}}" style="border-bottom:1px solid var(--border); padding-bottom:0.4rem; margin-top:2.5rem;">${{escapeHtml(cleanH)}}</h2>`;
        }} else if (trimmed === '***' || trimmed === '---' || trimmed === '* * *') {{
          if (curPara.length) {{
            html += `<p>${{formatInline(escapeHtml(curPara.join(' ')))}}</p>`;
            curPara = [];
          }}
          html += `<hr>`;
        }} else {{
          curPara.push(trimmed);
        }}
      }}

      if (curPara.length) {{
        html += `<p>${{formatInline(escapeHtml(curPara.join(' ')))}}</p>`;
      }}

      return html;
    }}

    function formatInline(str) {{
      // Bold **text**
      str = str.replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>');
      // Italics *text* or _text_
      str = str.replace(/\\*(.*?)\\*/g, '<em>$1</em>');
      str = str.replace(/_(.*?)_/g, '<em>$1</em>');
      return str;
    }}

    function exportData() {{
      const blob = new Blob([JSON.stringify(database, null, 2)], {{ type: 'application/json' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'fiction_vault_archive.json';
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

    window.addEventListener('DOMContentLoaded', () => {{
      renderCatalog();
    }});
  </script>
</body>
</html>
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_template)
    print(f"[✓] Successfully wrote Fiction Wiki to {output_path}", flush=True)

if __name__ == '__main__':
    scan_paths = [
        Path.home() / "Documents",
        Path.home() / "Desktop",
        Path.home() / "Downloads"
    ]
    
    if len(sys.argv) > 1:
        scan_paths = [Path(p) for p in sys.argv[1:]]

    stories = scan_all_fiction(scan_paths)
    
    json_path = Path("fiction_database.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(stories, f, ensure_ascii=False, indent=2)
    print(f"[✓] Saved database to {json_path}", flush=True)
    
    html_path = Path("fiction_wiki.html")
    generate_html_wiki(stories, html_path)
    generate_html_wiki(stories, Path("index.html"))
    print("[✓] Build complete!", flush=True)
