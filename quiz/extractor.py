import re
import os
import pypdf
from typing import List, Dict, Any, Optional

SUBJECT_KEYWORDS = {
    'Polity & Governance': [
        'article', 'constitution', 'supreme court', 'high court', 'parliament',
        'governor', 'president', 'election commission', 'panchayat', 'cag', 'attorney general',
        'tribunal', 'fundamental rights', 'lok sabha', 'rajya sabha', 'judicial', 'ordinance',
        'speaker', 'amendment', 'writs', 'citizenship', 'sir - phase', 'delphi', 'delimitation',
        'preventive detention', 'anti-defection', 'sedition', 'collegium'
    ],
    'Economy': [
        'gdp', 'inflation', 'rbi', 'reserve bank', 'fiscal', 'monetary', 'deficit',
        'repo', 'tax', 'gst', 'banking', 'exchange rate', 'foreign exchange', 'fdi',
        'current account', 'sebi', 'trade', 'bonds', 'budget', 'niti aayog', 'svanidhi',
        'revenue', 'disinvestment', 'liquidity', 'nbfc', 'rupee', 'depreciation', 'tariff',
        'wto', 'subsidy', 'msme', 'upi', 'financial inclusion'
    ],
    'Environment & Ecology': [
        'tiger', 'wildlife', 'forest', 'biodiversity', 'iucn', 'wetland', 'ramsar',
        'national park', 'sanctuary', 'pollution', 'climate change', 'species',
        'carbon', 'endangered', 'ecosystem', 'mangrove', 'coral', 'babesiosis', 'lion',
        'elephant', 'conservation', 'flora', 'fauna', 'cites', 'unfccc', 'air quality',
        'cop28', 'cop29', 'greenhouse', 'biopiracy', 'ecotourism'
    ],
    'Science & Technology': [
        'isro', 'nasa', 'satellite', 'orbit', 'ai', 'artificial intelligence', 'quantum',
        'semiconductor', 'nuclear', 'vaccine', 'dna', 'genome', 'crispr', 'cyber',
        'virus', 'outbreak', 'disease', 'missile', 'drdo', 'biotechnology', '5g', '6g',
        'fusion', 'supercomputer', 'space telescope', 'nanotechnology'
    ],
    'Geography': [
        'river', 'plateau', 'mountain', 'tributary', 'lake', 'strait', 'ocean',
        'monsoon', 'basin', 'soil', 'cyclone', 'trench', 'volcano', 'valley', 'desert',
        'ghepan', 'chenab', 'beas', 'western ghats', 'himalayas', 'glacier', 'el nino',
        'la nina', 'trade winds', 'volcanic', 'earthquake', 'tectonic'
    ],
    'History & Culture': [
        'buddha', 'jain', 'ashoka', 'mauryan', 'gupta', 'mughal', 'temple',
        'inscription', 'dynasty', 'chola', 'architecture', 'veda', 'sultanate',
        'harappa', 'indus valley', 'bhakti', 'sufi', 'cave', 'chand baori', 'pallava',
        'vijayanagara', 'ancient', 'medieval', 'freedom struggle', 'gandhi', 'non-cooperation',
        'rock-cut', 'stupa', 'numismatics'
    ],
    'International Relations': [
        'un', 'g20', 'brics', 'sco', 'asean', 'treaty', 'bilateral', 'summit',
        'wto', 'who', 'imf', 'world bank', 'security council', 'geopolitics',
        'nato', 'quad', 'iaea', 'international court', 'extradition', 'free trade agreement'
    ],
}


def detect_subject(topic: str, text: str) -> str:
    combined = f"{topic} {text}".lower()
    scores = {}
    for subj, keywords in SUBJECT_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', combined):
                score += 2 if kw in topic.lower() else 1
        if score > 0:
            scores[subj] = score

    if scores:
        return max(scores, key=scores.get)
    return 'General Studies'


def clean_text(text: str) -> str:
    text = text.replace('\xa0', ' ').replace('\u2013', '-').replace('\u2014', '--')
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    return text


def detect_edition_title(pdf_path: str) -> str:
    """
    Auto-detects the test series edition name (e.g. 'GMT - July 2026')
    from the PDF cover pages or filename.
    """
    try:
        reader = pypdf.PdfReader(pdf_path)
        cover_text = ''
        for p in range(min(4, len(reader.pages))):
            cover_text += '\n' + (reader.pages[p].extract_text() or '')

        # Check for Month + Year pattern
        m = re.search(
            r'(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s*(\d{4})',
            cover_text,
            re.IGNORECASE
        )
        if m:
            month = m.group(1).title()
            year = m.group(2)
            prefix = 'GMT' if ('good morning test' in cover_text.lower() or 'gmt' in cover_text.lower()) else 'UPSC Prelims'
            return f"{prefix} - {month} {year}"
    except Exception:
        pass

    # Fallback to filename
    base = os.path.basename(pdf_path)
    clean_name = os.path.splitext(base)[0].replace('_', ' ').replace('-', ' ').strip().title()
    return clean_name


def parse_pdf_questions(pdf_path: str, max_questions: Optional[int] = None) -> List[Dict[str, Any]]:
    reader = pypdf.PdfReader(pdf_path)
    pages_text = []

    for page in reader.pages:
        try:
            txt = page.extract_text() or ''
            # Strip running institution headers
            txt = re.sub(
                r'KingMakers IAS Academy[^\n]*\n(?:Chennai[^\n]*\n)?',
                '',
                txt,
                flags=re.IGNORECASE
            )
            pages_text.append(clean_text(txt))
        except Exception:
            continue

    combined = '\n'.join(pages_text)

    # Question header regex: e.g. "1. Article 124 in the Constitution of India \n Q."
    pattern = re.compile(
        r'(?:^|\n)\s*(\d+)\.\s+([A-Z0-9][^\n]+?)\s*\n\s*Q\.\s*',
        re.MULTILINE
    )

    splits = list(pattern.finditer(combined))
    parsed_questions = []

    for i, m in enumerate(splits):
        if max_questions and len(parsed_questions) >= max_questions:
            break

        q_num = int(m.group(1))
        topic = m.group(2).strip()
        start = m.end()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(combined)
        body = combined[start:end].strip()

        # Split into Question stem+options vs Answer+Explanation
        ans_match = re.search(r'\n\s*Answer:\s*\(([a-d])\)([^\n]*)', body, re.IGNORECASE)
        if not ans_match:
            ans_match = re.search(r'Answer:\s*\(([a-d])\)', body, re.IGNORECASE)
            if not ans_match:
                continue

        correct_opt = ans_match.group(1).lower()
        q_section = body[:ans_match.start()].strip()
        exp_section = body[ans_match.end():].strip()

        # Extract options (a), (b), (c), (d)
        opt_matches = list(re.finditer(
            r'(?:^|\n)\s*\(([a-d])\)\s*([\s\S]*?)(?=(?:\n\s*\([a-d]\))|$)',
            q_section,
            re.IGNORECASE
        ))

        options = {'a': '', 'b': '', 'c': '', 'd': ''}
        stem = q_section

        if len(opt_matches) >= 4:
            stem = q_section[:opt_matches[-4].start()].strip()
            for om in opt_matches[-4:]:
                opt_key = om.group(1).lower()
                options[opt_key] = re.sub(r'\s+', ' ', om.group(2)).strip()
        elif len(opt_matches) > 0:
            stem = q_section[:opt_matches[0].start()].strip()
            for om in opt_matches:
                opt_key = om.group(1).lower()
                options[opt_key] = re.sub(r'\s+', ' ', om.group(2)).strip()

        stem = re.sub(r'^[Q\.\s]+', '', stem).strip()

        # Extract "In NEWS"
        in_news = ''
        news_m = re.search(r'In NEWS:\s*([^\n]+(?:\n[^\n]+)?)', exp_section, re.IGNORECASE)
        if news_m:
            in_news = re.sub(r'\s+', ' ', news_m.group(1)).strip()

        # Extract "Value Addition" or "Note"
        value_addition = ''
        val_m = re.search(r'(?:Value Addition|Note):\s*([\s\S]+)', exp_section, re.IGNORECASE)
        if val_m:
            value_addition = val_m.group(1).strip()
            explanation_body = exp_section[:val_m.start()].strip()
        else:
            explanation_body = exp_section

        explanation_body = re.sub(r'^Explanation:\s*', '', explanation_body, flags=re.IGNORECASE).strip()
        subject = detect_subject(topic, f"{stem} {explanation_body}")

        parsed_questions.append({
            'question_number': q_num,
            'topic': topic,
            'subject': subject,
            'question_text': stem,
            'option_a': options.get('a', 'Option A'),
            'option_b': options.get('b', 'Option B'),
            'option_c': options.get('c', 'Option C'),
            'option_d': options.get('d', 'Option D'),
            'correct_option': correct_opt,
            'explanation': explanation_body,
            'value_addition': value_addition,
            'in_news': in_news,
            'difficulty': 'Medium',
        })

    return parsed_questions
