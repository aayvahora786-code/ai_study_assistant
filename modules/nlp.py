"""
modules/nlp.py
Enhanced NLP engine — sentence splitting, keyword extraction (TF-IDF),
extractive summarisation, key-point categorisation, and flashcard generation.
No external ML dependencies — runs fully offline.
"""
import re
import html
import math
from collections import Counter
from heapq import nlargest

# ─────────────────────────────────────────────────────────────
# 1. SENTENCE TOKENISER
# ─────────────────────────────────────────────────────────────

# Map abbreviation patterns → temporary placeholders so the splitter
# does not break on "Dr. Smith" etc.
_ABBREV_PATTERNS = [
    (re.compile(r'\bMr\.'),   'MR'),
    (re.compile(r'\bMrs\.'),  'MRS'),
    (re.compile(r'\bMs\.'),   'MS'),
    (re.compile(r'\bDr\.'),   'DR'),
    (re.compile(r'\bProf\.'), 'PROF'),
    (re.compile(r'\bSr\.'),   'SR'),
    (re.compile(r'\bJr\.'),   'JR'),
    (re.compile(r'\bvs\.'),   'VS'),
    (re.compile(r'\betc\.'),  'ETC'),
    (re.compile(r'\be\.g\.'), 'EG'),
    (re.compile(r'\bi\.e\.'), 'IE'),
    (re.compile(r'\bFig\.'),  'FIG'),
    (re.compile(r'\bEq\.'),   'EQ'),
    (re.compile(r'\bNo\.'),   'NO'),
    (re.compile(r'\bSt\.'),   'ST'),
    (re.compile(r'\bAve\.'),  'AVE'),
]
_PLACEHOLDER_RE = re.compile(r'__(MR|MRS|MS|DR|PROF|SR|JR|VS|ETC|EG|IE|FIG|EQ|NO|ST|AVE)__')


def _sentences(text: str) -> list:
    """Split text into clean, substantial sentences."""
    if not text or not text.strip():
        return []

    t = text
    for pattern, token in _ABBREV_PATTERNS:
        t = pattern.sub(f'__{token}__', t)

    # Split on '.', '!', '?' followed by whitespace + capital letter
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z\u0900-\u097F])', t.strip())

    sentences = []
    for s in parts:
        s = s.strip()
        # Restore abbreviations
        s = _PLACEHOLDER_RE.sub(lambda m: m.group(1).capitalize() + '.', s)
        # Strip leading bullet / number markers
        s = re.sub(r'^[\s\-\*•\d]+[\.\)]\s*', '', s)
        if len(s) > 15:
            sentences.append(s)
    return sentences


# ─────────────────────────────────────────────────────────────
# 2. WORD TOKENISER
# ─────────────────────────────────────────────────────────────

_CONTRACTIONS = [
    (re.compile(r"won't"),  "will not"),
    (re.compile(r"can't"),  "cannot"),
    (re.compile(r"n't"),    " not"),
    (re.compile(r"'re"),    " are"),
    (re.compile(r"'ll"),    " will"),
    (re.compile(r"'ve"),    " have"),
    (re.compile(r"'d"),     " would"),
    (re.compile(r"'s"),     ""),
]


def _words(text: str) -> list:
    """Return lowercase alphabetic tokens (≥3 chars) from text."""
    if not text:
        return []
    for pat, repl in _CONTRACTIONS:
        text = pat.sub(repl, text)
    return re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())


# ─────────────────────────────────────────────────────────────
# 3. STOPWORDS
# ─────────────────────────────────────────────────────────────

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "have", "will",
    "would", "could", "should", "about", "into", "onto", "over", "under",
    "between", "among", "because", "while", "where", "when", "which", "who",
    "whom", "whose", "what", "why", "how", "is", "are", "was", "were", "be",
    "been", "being", "has", "had", "do", "does", "did", "not", "no", "yes",
    "of", "in", "on", "at", "to", "by", "an", "a", "as", "it", "its", "but",
    "or", "if", "then", "else", "than", "so", "such", "very", "can", "may",
    "also", "however", "therefore", "thus", "hence", "moreover", "furthermore",
    "nevertheless", "nonetheless", "meanwhile", "otherwise", "although",
    "though", "each", "other", "these", "those", "they", "them", "their",
    "there", "here", "more", "most", "some", "any", "all", "both", "few",
    "many", "much", "own", "same", "too", "just", "only", "even", "new",
    "used", "use", "using", "one", "two", "three", "four", "five", "six",
    "seven", "eight", "nine", "ten",
}


# ─────────────────────────────────────────────────────────────
# 4. TF-IDF KEYWORD EXTRACTION
# ─────────────────────────────────────────────────────────────

def _keywords(text: str, k: int = 20) -> list:
    """
    Return the top-k keywords ranked by TF-IDF.
    Prefers domain-specific, longer, multi-occurrence words.
    """
    if not text or not text.strip():
        return []

    words = [w for w in _words(text) if w not in STOPWORDS]
    if not words:
        return []

    freq   = Counter(words)
    total  = len(words)
    tf     = {w: c / total for w, c in freq.items()}

    sents  = _sentences(text)
    n_sents = max(1, len(sents))
    idf    = {
        w: math.log((n_sents + 1) / (1 + sum(1 for s in sents if w in s.lower())))
        for w in freq
    }

    # Bonus for longer, capitalized-in-original words (likely proper nouns / terms)
    bonus = {}
    for w in freq:
        b = 0.0
        if len(w) >= 7:
            b += 0.2
        # Check if word appears capitalized in original text
        if re.search(r'\b' + re.escape(w.capitalize()) + r'\b', text):
            b += 0.3
        bonus[w] = b

    tfidf = {w: tf[w] * idf[w] * (1 + bonus[w]) for w in tf}
    return [w for w, _ in sorted(tfidf.items(), key=lambda x: -x[1])[:k]]


# ─────────────────────────────────────────────────────────────
# 5. EXTRACTIVE SUMMARISER
# ─────────────────────────────────────────────────────────────

_FOCUS_MAP = {
    'concepts':    ['concept', 'idea', 'theory', 'principle', 'notion',
                    'framework', 'model', 'hypothesis'],
    'definitions': ['defined', 'definition', 'means', 'refers', 'denotes',
                    'known as', 'called', 'term'],
    'examples':    ['example', 'instance', 'illustration', 'such as',
                    'like', 'namely', 'case'],
    'processes':   ['process', 'step', 'procedure', 'method', 'approach',
                    'technique', 'stage', 'phase', 'workflow'],
}


def summarize_text(text: str, bullets: int = 7, focus: str = None) -> str:
    """
    Extractive summary returning an HTML-rich string ready for st.markdown.
    Each bullet preserves the original sentence.  Focus biases the scorer
    toward sentences matching a thematic category.
    """
    if not text or not text.strip():
        return "⚠️ No content provided for summarisation."

    sents    = _sentences(text)
    keywords = _keywords(text, k=40)

    if not sents or not keywords:
        return "⚠️ Not enough content to generate a summary."

    kw_set   = set(keywords)
    weights  = {kw: 1 + i * 0.02 for i, kw in enumerate(reversed(keywords))}
    focus_kws = _FOCUS_MAP.get(focus, [])

    scores = {}
    for sent in sents:
        w = _words(sent)
        if len(w) < 6:
            continue
        score = sum(weights.get(wrd, 0) for wrd in w if wrd in kw_set)

        # Focus boost
        if focus_kws and any(fk in sent.lower() for fk in focus_kws):
            score *= 1.6

        # Multi-keyword density bonus
        n_kw = sum(1 for wrd in w if wrd in kw_set)
        if n_kw > 2:
            score *= (1 + 0.15 * min(n_kw, 6))

        # Sentence-position bonus (first 30 % of document)
        pos_ratio = sents.index(sent) / max(1, len(sents))
        if pos_ratio < 0.30:
            score *= 1.2

        # Length normalisation — prefer 12-25 word sentences
        ideal = 18
        length_factor = 1 - abs(len(w) - ideal) / (ideal * 2)
        score *= max(0.5, length_factor)

        if score > 0:
            scores[sent] = score

    if not scores:
        return "⚠️ Could not extract meaningful summary sentences."

    # Pick top sentences, keep document order
    top = set(nlargest(min(bullets, len(scores)), scores, key=scores.get))
    ordered = [s for s in sents if s in top]

    # Build rich HTML
    focus_label = focus.capitalize() if focus else "General"
    lines = [
        f'<div class="summary-box">',
        f'<h3>📌 Smart Summary &nbsp;<small style="font-weight:400;font-size:0.78rem;'
        f'color:#64748b">Focus: {focus_label} • {len(ordered)} bullets</small></h3>',
    ]
    icons = ["💡", "📖", "🔑", "✅", "📌", "🔍", "⚡", "🧩"]
    for i, sent in enumerate(ordered):
        icon = icons[i % len(icons)]
        clean = html.escape(sent.strip().rstrip('.').capitalize() + '.')
        lines.append(
            f'<div class="summary-bullet">'
            f'<span class="summary-bullet-icon">{icon}</span>'
            f'<span>{clean}</span>'
            f'</div>'
        )
    lines.append('</div>')
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# 6. KEY-POINT EXTRACTOR
# ─────────────────────────────────────────────────────────────

_CATEGORIES = {
    "definition": (
        ["defined as", "refers to", "means", "is a", "is an", "known as",
         "called", "denotes", "stands for"],
        "📝", "def",  "Definition"
    ),
    "example": (
        ["for example", "for instance", "such as", "like", "e.g.", "namely",
         "illustrated by", "including"],
        "💡", "ex",   "Example"
    ),
    "process": (
        ["first", "second", "third", "finally", "next", "then", "step",
         "stage", "phase", "procedure", "algorithm"],
        "🔄", "proc", "Process"
    ),
    "comparison": (
        ["similar", "different", "whereas", "while", "however", "in contrast",
         "on the other hand", "unlike", "compared"],
        "⚖️", "cmp",  "Compare"
    ),
    "conclusion": (
        ["therefore", "thus", "hence", "consequently", "as a result",
         "in conclusion", "in summary", "overall"],
        "✅", "con",  "Conclusion"
    ),
}


def extract_key_points(text: str, max_points: int = 9) -> list:
    """
    Return a list of HTML strings, each representing a categorised key point.
    """
    if not text or not text.strip():
        return ["<p>No content provided.</p>"]

    sents    = _sentences(text)
    kw_set   = set(_keywords(text, k=30))
    results  = []
    seen     = set()

    for sent in sents:
        if len(results) >= max_points:
            break
        w     = _words(sent)
        score = sum(1 for wrd in w if wrd in kw_set)

        cat_key = None
        cat_icon = "📌"
        cat_css  = "gen"
        cat_label = "General"
        for key, (indicators, icon, css, label) in _CATEGORIES.items():
            if any(ind in sent.lower() for ind in indicators):
                cat_key   = key
                cat_icon  = icon
                cat_css   = css
                cat_label = label
                score    += 2
                break

        # Skip duplicate or low-value sentences
        sig = frozenset(w[:8])
        if sig in seen:
            continue
        if score < 2 or not (8 < len(w) < 45):
            continue

        seen.add(sig)
        clean = html.escape(sent.strip())
        results.append(
            f'<div class="kp-card">'
            f'<span class="kp-tag kp-tag-{cat_css}">{cat_icon} {cat_label}</span><br>'
            f'{clean}'
            f'</div>'
        )

    if not results:
        return ['<div class="kp-card"><span class="kp-tag kp-tag-gen">📌 General</span>'
                '<br>No strong key points detected. Try providing more detailed text.</div>']
    return results


# ─────────────────────────────────────────────────────────────
# 7. FLASHCARD GENERATOR
# ─────────────────────────────────────────────────────────────

_DEF_PATTERNS = [
    (" is ",           "What is"),
    (" are ",          "What are"),
    (" defined as ",   "Define"),
    (" refers to ",    "What does"),
    (" means ",        "What does"),
    (" can be defined as ", "Define"),
    (" is defined as ", "Define"),
    (" describes ",    "What does"),
    (" explains ",     "What does"),
    (" involves ",     "What does"),
    (" includes ",     "What does"),
    (" consists of ",  "What does"),
    (" known as ",     "What is known as"),
    (" denotes ",      "What does"),
]


def generate_flashcards(text: str, n: int = 8) -> list:
    """
    Generate up to n flashcards from text.
    Priority order: definitions → keyword explanations → fill-in-blank → review.
    Each card: {question, answer, type, icon}
    """
    import random

    if not text or not text.strip():
        return []

    sents    = _sentences(text)
    keywords = _keywords(text, k=20)
    cards    = []
    used_q   = set()

    def _add(q, a, ctype, icon):
        key = q[:60].lower()
        if key not in used_q and a.strip():
            used_q.add(key)
            cards.append({"question": q, "answer": a.strip(), "type": ctype, "icon": icon})

    # ── Type 1: Definition cards ──────────────────────────────
    for sent in sents:
        if len(cards) >= max(n // 2, 3):
            break
        lower = sent.lower()
        for pattern, prefix in _DEF_PATTERNS:
            if pattern in lower:
                parts = sent.split(pattern, 1)
                if len(parts) == 2:
                    term, desc = parts[0].strip(), parts[1].strip()
                    # Clean trailing punctuation from desc
                    desc = desc.rstrip('.,;')
                    if 1 <= len(term.split()) <= 6 and 8 <= len(desc):
                        _add(f"{prefix} {term}?", desc, "definition", "📖")
                        break

    # ── Type 2: Example cards ─────────────────────────────────
    for sent in sents:
        if len(cards) >= n:
            break
        lower = sent.lower()
        if any(ind in lower for ind in ["for example", "for instance", "such as", "e.g.", "namely"]):
            w = _words(sent)
            kws_in = [kw for kw in keywords if kw in lower]
            if kws_in:
                topic = kws_in[0]
                _add(f"Give an example related to '{topic}'.", sent.strip(), "example", "💡")

    # ── Type 3: Keyword-context cards ────────────────────────
    for kw in keywords:
        if len(cards) >= n:
            break
        if any(kw in c['question'].lower() for c in cards):
            continue
        rel = [s for s in sents if kw in s.lower() and len(s.split()) > 8]
        if not rel:
            continue
        context = max(rel, key=lambda s: sum(1 for k in keywords if k in s.lower()))
        lower = context.lower()
        if any(ind in lower for ind in ["process", "step", "procedure", "method", "algorithm"]):
            _add(f"Describe the process of {kw}.", context.strip(), "process", "🔄")
        elif any(ind in lower for ind in ["important", "significant", "key", "critical", "essential"]):
            _add(f"Why is {kw} important?", context.strip(), "importance", "⭐")
        else:
            _add(f"Explain {kw} in your own words.", context.strip(), "explanation", "🔍")

    # ── Type 4: Fill-in-the-blank cards ───────────────────────
    random.shuffle(sents)
    for sent in sents:
        if len(cards) >= n:
            break
        w = sent.split()
        if len(w) < 8:
            continue
        kws_in = [wd for wd in w if wd.lower().strip(".,!?;:") in keywords]
        if not kws_in:
            continue
        blank_word = random.choice(kws_in).strip(".,!?;:")
        blanked    = sent.replace(blank_word, "______", 1)
        _add(f"Fill in the blank:\n{blanked}", blank_word, "fill_blank", "✏️")

    # ── Type 5: True/False cards ──────────────────────────────
    for sent in sents:
        if len(cards) >= n:
            break
        w = sent.split()
        if len(w) > 10:
            _add(f"True or False: {sent.strip()}", "True", "true_false", "✔️")

    # ── Fallback review cards ─────────────────────────────────
    chunks = [c.strip() for c in text.split('\n\n') if len(c.strip()) > 20]
    for i, chunk in enumerate(chunks):
        if len(cards) >= n:
            break
        _add(f"Review point {i + 1}:", chunk[:200], "review", "📋")

    return cards[:n]
