"""
clean_explanations.py
─────────────────────
Reads the SQLite DB, cleans each explanation field:
  • Merges accidental mid-sentence line-breaks from PDF extraction
  • Preserves intentional paragraph separators (double-newlines)
  • Preserves list markers (1., 2., Option (a):, •, IN NEWS:, etc.)
  • Writes cleaned text back to the DB
"""

import os, re, sys, sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), 'db.sqlite3')

# ─── Rules for what constitutes a "real" line break ──────────────────────────
# A line break is REAL (keep as \n) when the NEXT line starts with:
REAL_BREAK_NEXT = re.compile(
    r'^('
    r'\d+\.'          # numbered point: 1. 2. etc.
    r'|[Oo]ption\s*\(' # Option (a): etc.
    r'|[A-Z][A-Z\s]+:'  # ALL-CAPS heading with colon
    r'|IN\s+NEWS'      # IN NEWS
    r'|About\s'        # About Xyz
    r'|•'              # bullet
    r'|\*'             # asterisk bullet
    r'|●'
    r'|\t'
    r'|─'
    r')'
)

# A line break is REAL when the CURRENT line ends with one of these signals:
REAL_BREAK_CURR = re.compile(
    r'('
    r'\.$'             # sentence ends
    r'|\.$'
    r'|:$'             # colon (heading)
    r'|correct\s*$'    # verdict words
    r'|incorrect\s*$'
    r'|\(Correct\)\s*$'
    r'|\(Incorrect\)\s*$'
    r')'
    , re.IGNORECASE
)


def normalize_bullets(text):
    """Normalize various bullet chars to •"""
    text = text.replace('\x07', '•')
    # PDF '?' used as bullet when preceded/followed by space
    text = re.sub(r'(?<!\w)\?(?=\s)', '•', text)
    return text


def clean_explanation(raw: str) -> str:
    if not raw:
        return raw

    raw = raw.replace('\r\n', '\n').replace('\r', '\n')
    raw = normalize_bullets(raw)

    lines = raw.split('\n')
    output_lines = []
    buf = ''

    for i, line in enumerate(lines):
        line = line.rstrip()
        stripped = line.strip()

        if not stripped:
            # Empty line = paragraph break — flush buffer with double newline
            if buf:
                output_lines.append(buf)
                buf = ''
            output_lines.append('')  # paragraph gap
            continue

        if not buf:
            buf = stripped
            continue

        next_line = lines[i + 1].strip() if i + 1 < len(lines) else ''

        # Decide whether to keep the newline or merge
        keep_break = (
            REAL_BREAK_NEXT.match(stripped) or       # next line starts a new block
            REAL_BREAK_NEXT.match(next_line) or       # the line after next starts a new block
            REAL_BREAK_CURR.search(buf) or            # current buffer ends a sentence
            len(stripped) < 20                        # very short line = likely a header
        )

        if keep_break:
            output_lines.append(buf)
            buf = stripped
        else:
            # Merge — join with space only
            if buf.endswith('-'):
                # PDF hyphenated word split: "depre-\nciation" → "depreciation"
                buf = buf[:-1] + stripped
            else:
                buf = buf + ' ' + stripped

    if buf:
        output_lines.append(buf)

    # Collapse 3+ blank lines to 2
    result = '\n'.join(output_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)

    # Strip leading/trailing whitespace
    return result.strip()


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT id, explanation FROM quiz_question")
    rows = cur.fetchall()
    print(f"Loaded {len(rows)} questions from DB")

    updated = 0
    for qid, expl in rows:
        cleaned = clean_explanation(expl)
        if cleaned != expl:
            cur.execute("UPDATE quiz_question SET explanation=? WHERE id=?", (cleaned, qid))
            updated += 1

    conn.commit()
    conn.close()
    print(f"Done. Cleaned {updated} / {len(rows)} explanation fields in DB")


if __name__ == '__main__':
    run()
