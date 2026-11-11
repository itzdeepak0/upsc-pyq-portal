import re
from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape

register = template.Library()


def _parse_blocks(text):
    """Parse raw explanation text into typed blocks for structured rendering."""
    # Normalize line endings and bullet characters from PDF extraction
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # PDF often extracts '?' or '\x07' as bullet markers — normalize
    text = text.replace('\x07', '•').replace('?', '•')

    lines = text.split('\n')
    blocks = []  # list of dicts: {type, content, items}

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        # Skip truly blank lines between blocks
        if not line.strip():
            i += 1
            continue

        stripped = line.strip()

        # === IN NEWS line ===
        if stripped.upper().startswith('IN NEWS:'):
            news_text = stripped[8:].strip()
            # Collect continuation lines
            j = i + 1
            while j < len(lines) and lines[j].strip() and not _is_new_block(lines[j].strip()):
                news_text += ' ' + lines[j].strip()
                j += 1
            blocks.append({'type': 'news', 'content': news_text})
            i = j
            continue

        # === Numbered statement heading: "1. Title text" ===
        m = re.match(r'^(\d+)\.\s+(.+)$', stripped)
        if m:
            num = m.group(1)
            heading = m.group(2)
            # Collect body lines until next numbered statement or new block
            body_lines = []
            j = i + 1
            while j < len(lines):
                nxt = lines[j].rstrip()
                nxt_s = nxt.strip()
                if not nxt_s:
                    j += 1
                    continue
                if re.match(r'^\d+\.\s+', nxt_s) or _is_new_block(nxt_s):
                    break
                body_lines.append(nxt_s)
                j += 1
            blocks.append({'type': 'statement', 'num': num, 'heading': heading, 'body': body_lines})
            i = j
            continue

        # === Option analysis: "Option (a):", "Option(a):" ===
        m = re.match(r'^[Oo]ption\s*\(([a-dA-D])\)\s*[:\-]?\s*(.*)', stripped)
        if m:
            opt_key = m.group(1).upper()
            opt_text = m.group(2).strip()
            j = i + 1
            while j < len(lines):
                nxt_s = lines[j].strip()
                if not nxt_s:
                    j += 1
                    continue
                if re.match(r'^[Oo]ption\s*\(', nxt_s) or _is_new_block(nxt_s):
                    break
                opt_text += ' ' + nxt_s
                j += 1
            blocks.append({'type': 'option', 'key': opt_key, 'content': opt_text})
            i = j
            continue

        # === Bullet list block ===
        if stripped.startswith('•') or stripped.startswith('\t•') or stripped.startswith('\t'):
            items = []
            j = i
            while j < len(lines):
                nxt_s = lines[j].strip()
                if not nxt_s:
                    j += 1
                    break  # end of bullet block
                if nxt_s.startswith('•'):
                    items.append(('bullet', nxt_s.lstrip('•').strip()))
                elif re.match(r'^\d+\.\s+', nxt_s) or _is_new_block(nxt_s):
                    break
                else:
                    # sub-continuation of previous item
                    if items:
                        items[-1] = (items[-1][0], items[-1][1] + ' ' + nxt_s)
                    else:
                        items.append(('text', nxt_s))
                j += 1
            if items:
                blocks.append({'type': 'bullets', 'items': items})
            i = j
            continue

        # === Section heading (all-caps or Title Case short line ending without period) ===
        if _is_section_heading(stripped):
            blocks.append({'type': 'heading', 'content': stripped})
            i += 1
            continue

        # === Key-value table row (e.g., "Meaning Rock engravings or carvings") ===
        # Detect these only when several consecutive lines look like key-value pairs
        # Try to collect a table block
        table_rows = []
        j = i
        while j < len(lines):
            nxt_s = lines[j].strip()
            if not nxt_s:
                break
            kv = _as_key_value(nxt_s)
            if kv:
                table_rows.append(kv)
            elif re.match(r'^\d+\.\s+', nxt_s) or _is_new_block(nxt_s):
                break
            else:
                # not KV — stop collecting table
                break
            j += 1
        if len(table_rows) >= 2:
            blocks.append({'type': 'table', 'rows': table_rows})
            i = j
            continue

        # === Default: paragraph ===
        para = stripped
        j = i + 1
        while j < len(lines):
            nxt_s = lines[j].strip()
            if not nxt_s:
                break
            if _is_new_block(nxt_s) or re.match(r'^\d+\.\s+', nxt_s):
                break
            para += ' ' + nxt_s
            j += 1
        blocks.append({'type': 'para', 'content': para})
        i = j

    return blocks


def _is_new_block(s):
    return (s.upper().startswith('IN NEWS') or
            bool(re.match(r'^[Oo]ption\s*\(', s)) or
            _is_section_heading(s))


def _is_section_heading(s):
    """Heuristic: short line, Title Case or ALL CAPS, no sentence-ending period in middle."""
    if len(s) > 80:
        return False
    if s.endswith(':'):
        return True
    words = s.split()
    if len(words) <= 7 and all(w[0].isupper() or not w[0].isalpha() for w in words if w):
        # Make sure it's not an option or numbered line
        if not re.match(r'^\d+\.', s) and '(' not in s[:3]:
            return True
    return False


def _as_key_value(s):
    """Try to split a line into a key-value pair at a capital word boundary."""
    # e.g., "Meaning Rock engravings or carvings" — first 1-3 title-case words are key
    m = re.match(r'^([A-Z][a-zA-Z /]+?)\s{2,}(.+)$', s)
    if m:
        return (m.group(1).strip(), m.group(2).strip())
    return None


def _verdict_badge(text):
    """Extract verdict from option body and return a styled badge string."""
    low = text.lower()
    if 'is correct' in low:
        return '<span class="exp-badge exp-correct">✓ Correct</span>'
    elif 'is incorrect' in low or 'is not correct' in low:
        return '<span class="exp-badge exp-wrong">✗ Incorrect</span>'
    return ''


def _blocks_to_html(blocks):
    html = ''
    for b in blocks:
        t = b['type']

        if t == 'para':
            html += f'<p class="exp-para">{escape(b["content"])}</p>'

        elif t == 'heading':
            html += f'<div class="exp-section-heading"><span>{escape(b["content"])}</span></div>'

        elif t == 'statement':
            body_html = ''
            for line in b['body']:
                if line.startswith('•'):
                    body_html += f'<li>{escape(line.lstrip("•").strip())}</li>'
                else:
                    body_html += f'<p class="exp-stmt-body">{escape(line)}</p>'
            # Wrap bullets in ul if any
            if '<li>' in body_html:
                body_html = re.sub(r'(<li>.*?</li>)', r'<ul class="exp-bullets">\1</ul>', body_html, flags=re.DOTALL)

            # Verdict from last body line
            verdict = ''
            for line in reversed(b['body']):
                v = _verdict_badge(line)
                if v:
                    verdict = v
                    break

            html += f'''<div class="exp-statement">
  <div class="exp-stmt-num">{escape(b["num"])}</div>
  <div class="exp-stmt-content">
    <div class="exp-stmt-heading">{escape(b["heading"])} {verdict}</div>
    {body_html}
  </div>
</div>'''

        elif t == 'option':
            verdict = _verdict_badge(b['content'])
            opt_key = b['key']
            html += f'''<div class="exp-option">
  <div class="exp-opt-key">({opt_key})</div>
  <div class="exp-opt-body">
    <p>{escape(b["content"])}</p>
    {verdict}
  </div>
</div>'''

        elif t == 'bullets':
            items_html = ''.join(
                f'<li>{escape(item[1])}</li>' for item in b['items']
            )
            html += f'<ul class="exp-bullets">{items_html}</ul>'

        elif t == 'table':
            rows_html = ''.join(
                f'<tr><th>{escape(k)}</th><td>{escape(v)}</td></tr>'
                for k, v in b['rows']
            )
            html += f'<div class="exp-table-wrap"><table class="exp-table">{rows_html}</table></div>'

        elif t == 'news':
            html += f'''<div class="exp-news-banner">
  <span class="exp-news-label">📰 IN NEWS</span>
  <span class="exp-news-text">{escape(b["content"])}</span>
</div>'''

    return html


@register.filter(name='format_explanation')
def format_explanation(text):
    """Convert raw explanation text into rich structured HTML."""
    if not text:
        return ''
    blocks = _parse_blocks(str(text))
    return mark_safe(_blocks_to_html(blocks))
