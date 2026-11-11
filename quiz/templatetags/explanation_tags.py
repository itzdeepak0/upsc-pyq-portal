"""
explanation_tags.py – Custom Django template filter for structured explanation rendering.
Parses cleaned explanation text into typed HTML blocks.
"""

import re
from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape

register = template.Library()


# ─── Bullet normalization ─────────────────────────────────────────────────────
_BULLET_RE = re.compile(r'^\s*[•●\*\-]\s*')
_NUM_RE     = re.compile(r'^\s*(\d+)\.\s+(.+)', re.DOTALL)
_OPT_RE     = re.compile(r'^\s*[Oo]ption\s*\(([a-dA-D])\)\s*[:\-]?\s*(.*)', re.DOTALL)
_NEWS_RE    = re.compile(r'^\s*In\s+NEWS\s*[:\-]?\s*(.*)', re.IGNORECASE | re.DOTALL)
_HEAD_RE    = re.compile(r'^[A-Z][A-Za-z\s\/\-]+:?\s*$')


def _verdict(text):
    low = text.lower()
    if re.search(r'is\s+correct', low):
        return 'correct'
    if re.search(r'is\s+(in)?correct|is\s+not\s+correct', low):
        return 'wrong'
    return None


def _verdict_badge(v):
    if v == 'correct':
        return '<span class="exp-badge exp-correct"><svg class="exp-icon" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>Correct</span>'
    if v == 'wrong':
        return '<span class="exp-badge exp-wrong"><svg class="exp-icon" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/></svg>Incorrect</span>'
    return ''


def _parse(text):
    """Split text into logical blocks."""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Normalize exotic bullet chars
    text = text.replace('\x07', '•').replace('●', '•').replace('*', '•')

    paragraphs = re.split(r'\n\s*\n', text.strip())
    blocks = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        lines = [l.strip() for l in para.split('\n') if l.strip()]
        if not lines:
            continue
        joined = ' '.join(lines)

        # ── IN NEWS ──
        m = _NEWS_RE.match(joined)
        if m:
            blocks.append({'type': 'news', 'text': m.group(1).strip()})
            continue

        # ── Numbered statement  "1. Heading text..." ──
        m = _NUM_RE.match(joined)
        if m:
            num = m.group(1)
            rest = m.group(2).strip()
            # verdict detection
            v = _verdict(rest)
            # find sub-bullets inside rest
            sub_bullets = []
            rest_clean = rest
            if '•' in rest:
                parts = rest.split('•')
                rest_clean = parts[0].strip()
                sub_bullets = [p.strip() for p in parts[1:] if p.strip()]
            blocks.append({
                'type': 'statement',
                'num': num,
                'text': rest_clean,
                'verdict': v,
                'bullets': sub_bullets,
            })
            continue

        # ── Option (a)/(b)/(c)/(d) ──
        m = _OPT_RE.match(joined)
        if m:
            key = m.group(1).upper()
            body = m.group(2).strip()
            v = _verdict(body)
            blocks.append({'type': 'option', 'key': key, 'text': body, 'verdict': v})
            continue

        # ── Pure bullet list block ──
        if all(_BULLET_RE.match(l) for l in lines) and len(lines) > 1:
            items = [_BULLET_RE.sub('', l) for l in lines]
            blocks.append({'type': 'bullets', 'items': items})
            continue

        # ── Single-line section heading ──
        if len(lines) == 1 and len(joined) < 70 and _HEAD_RE.match(joined):
            blocks.append({'type': 'heading', 'text': joined})
            continue

        # ── Default paragraph — split out inline bullets if any ──
        if '•' in joined:
            parts = joined.split('•')
            intro = parts[0].strip()
            items = [p.strip() for p in parts[1:] if p.strip()]
            if intro:
                blocks.append({'type': 'para', 'text': intro})
            if items:
                blocks.append({'type': 'bullets', 'items': items})
        else:
            blocks.append({'type': 'para', 'text': joined})

    return blocks


def _html(blocks):
    out = []
    for b in blocks:
        t = b['type']
        e = escape

        if t == 'para':
            out.append(f'<p class="exp-para">{e(b["text"])}</p>')

        elif t == 'heading':
            icon = '<svg class="exp-head-icon" viewBox="0 0 20 20" fill="currentColor"><path d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.396 0 2.698.37 3.8 1.015A6.98 6.98 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.968 7.968 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z"/></svg>'
            out.append(f'<div class="exp-section-heading">{icon}<span>{e(b["text"])}</span></div>')

        elif t == 'statement':
            badge = _verdict_badge(b.get('verdict'))
            body_text = e(b['text'])
            bullets_html = ''
            if b.get('bullets'):
                items_li = ''.join(f'<li>{e(item)}</li>' for item in b['bullets'])
                bullets_html = f'<ul class="exp-bullets exp-bullets-sm">{items_li}</ul>'
            out.append(
                f'<div class="exp-statement">'
                f'  <div class="exp-stmt-num">{e(b["num"])}</div>'
                f'  <div class="exp-stmt-content">'
                f'    <p class="exp-stmt-text">{body_text}</p>'
                f'    {bullets_html}'
                f'    {badge}'
                f'  </div>'
                f'</div>'
            )

        elif t == 'option':
            badge = _verdict_badge(b.get('verdict'))
            # Colour the option key chip based on verdict
            chip_cls = {
                'correct': 'exp-opt-key exp-opt-key--correct',
                'wrong':   'exp-opt-key exp-opt-key--wrong',
                None:      'exp-opt-key',
            }[b.get('verdict')]
            out.append(
                f'<div class="exp-option">'
                f'  <div class="{chip_cls}">({e(b["key"])})</div>'
                f'  <div class="exp-opt-body">'
                f'    <p>{e(b["text"])}</p>'
                f'    {badge}'
                f'  </div>'
                f'</div>'
            )

        elif t == 'bullets':
            items_li = ''.join(f'<li>{e(item)}</li>' for item in b['items'])
            out.append(f'<ul class="exp-bullets">{items_li}</ul>')

        elif t == 'news':
            news_icon = '📰'
            out.append(
                f'<div class="exp-news-banner">'
                f'  <span class="exp-news-label">{news_icon} IN NEWS</span>'
                f'  <span class="exp-news-text">{e(b["text"])}</span>'
                f'</div>'
            )

    return ''.join(out)


@register.filter(name='format_explanation')
def format_explanation(text):
    if not text:
        return ''
    blocks = _parse(str(text))
    return mark_safe(_html(blocks))
