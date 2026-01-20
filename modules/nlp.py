import re
import html
from collections import Counter
from heapq import nlargest
import random

# --- 1. IMPROVED TOKENIZATION HELPERS ---

def _sentences(text: str):
    """
    Improved sentence splitter using regex.
    Better handling of abbreviations and special cases.
    """
    # First, replace common abbreviations with temporary markers
    abbrev_map = {
        r'\bMr\.\s': 'MR_ABBREV ',
        r'\bMrs\.\s': 'MRS_ABBREV ',
        r'\bMs\.\s': 'MS_ABBREV ',
        r'\bDr\.\s': 'DR_ABBREV ',
        r'\bProf\.\s': 'PROF_ABBREV ',
        r'\bSr\.\s': 'SR_ABBREV ',
        r'\bJr\.\s': 'JR_ABBREV ',
        r'\bvs\.\s': 'VS_ABBREV ',
        r'\betc\.\s': 'ETC_ABBREV ',
        r'\be\.g\.\s': 'EG_ABBREV ',
        r'\bi\.e\.\s': 'IE_ABBREV ',
        r'\bFig\.\s': 'FIG_ABBREV ',
        r'\bEq\.\s': 'EQ_ABBREV '
    }
    
    # Apply replacements
    processed_text = text
    for abbrev, marker in abbrev_map.items():
        processed_text = re.sub(abbrev, marker, processed_text)
    
    # Split on sentence boundaries
    raw_sentences = re.split(r'[.!?]+(?=\s+[A-Z]|\s*$)', processed_text.strip())
    
    # Clean up and filter valid sentences
    sentences = []
    for s in raw_sentences:
        s = s.strip()
        if len(s) > 10:  # Only include substantial sentences
            # Restore abbreviations
            for marker, original in [(v, k) for k, v in abbrev_map.items()]:
                s = s.replace(marker, original.replace(r'\b', '').replace(r'\s', ' '))
            sentences.append(s)
    
    return sentences

def _words(text: str):
    """
    Extract words (alphabetic only) with improved handling of contractions.
    """
    # Handle contractions by temporarily replacing them
    text = re.sub(r"won't", "will not", text)
    text = re.sub(r"can't", "cannot", text)
    text = re.sub(r"n't", " not", text)
    text = re.sub(r"'re", " are", text)
    text = re.sub(r"'ll", " will", text)
    text = re.sub(r"'ve", " have", text)
    text = re.sub(r"'d", " would", text)
    
    return re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

# --- 2. ENHANCED KEYWORD EXTRACTION ---

STOPWORDS = {
    "the","and","for","with","that","this","from","have","will","would","could",
    "should","about","into","onto","over","under","between","among","because",
    "while","where","when","which","who","whom","whose","what","why","how",
    "is","are","was","were","be","been","being","has","had","do","does","did",
    "not","no","yes","of","in","on","at","to","by","an","a","as","it","its",
    "but","or","if","then","else","than","so","such","very","can","may",
    "also","however","therefore","thus","hence","moreover","furthermore",
    "nevertheless","nonetheless","meanwhile","otherwise","although","though"
}

def _keywords(text: str, k: int = 20):
    """
    Enhanced keyword extraction with TF-IDF-like scoring.
    """
    words = [w for w in _words(text) if w not in STOPWORDS]
    freq = Counter(words)
    
    # Calculate term frequency
    total_words = len(words)
    tf = {word: count/total_words for word, count in freq.items()}
    
    # Simple approximation of IDF based on word length and position
    idf = {}
    sentences = _sentences(text)
    total_sentences = len(sentences)
    
    for word in freq:
        # Count sentences containing the word
        sent_count = sum(1 for s in sentences if word in s.lower())
        # Avoid division by zero
        sent_count = max(1, sent_count)
        # IDF score (inverse sentence frequency)
        idf[word] = 1.0 / (sent_count / total_sentences)
    
    # TF-IDF score
    tfidf = {word: tf[word] * idf[word] for word in tf}
    
    # Return top keywords by TF-IDF
    return [w for w, _ in sorted(tfidf.items(), key=lambda x: x[1], reverse=True)[:k]]

# --- 3. ENHANCED SUMMARY GENERATION ---

def summarize_text(text: str, bullets: int = 6, focus: str = None):
    """
    Enhanced summary generation with optional focus area.
    Focus can be 'concepts', 'definitions', 'examples', 'processes', or None.
    """
    sentences = _sentences(text)
    keywords = _keywords(text, k=30)

    if not keywords or not sentences:
        return "Not enough content to generate a summary."

    keyword_weights = Counter(keywords)
    max_freq = max(keyword_weights.values()) if keyword_weights else 1
    weights = {w: c/max_freq for w, c in keyword_weights.items()}

    # Adjust scoring based on focus
    focus_keywords = []
    if focus == 'concepts':
        focus_keywords = ['concept', 'idea', 'theory', 'principle', 'notion', 'framework']
    elif focus == 'definitions':
        focus_keywords = ['definition', 'defined as', 'means', 'refers to', 'is', 'are']
    elif focus == 'examples':
        focus_keywords = ['example', 'for instance', 'such as', 'like', 'illustration']
    elif focus == 'processes':
        focus_keywords = ['process', 'step', 'procedure', 'method', 'approach', 'technique']

    sentence_scores = {}
    for sent in sentences:
        words = _words(sent)
        score = sum(weights.get(w, 0) for w in words)
        
        # Boost score for focus-related sentences
        if focus and any(fk in sent.lower() for fk in focus_keywords):
            score *= 1.5
            
        # Boost score for sentences with multiple keywords
        keyword_count = sum(1 for w in words if w in keywords)
        if keyword_count > 1:
            score *= (1 + 0.2 * keyword_count)
            
        # Adjust score by sentence length (prefer medium-length sentences)
        length_factor = min(1.0, len(words) / 15)
        score *= length_factor
        
        if score > 0 and len(words) >= 8:
            sentence_scores[sent] = score

    if not sentence_scores:
        return "Not enough content to generate a summary."

    selected = nlargest(bullets, sentence_scores, key=sentence_scores.get)
    selected_sorted = [s for s in sentences if s in selected]

    output = ["### 📌 Smart Summary"]
    for sent in selected_sorted:
        clean = sent.strip().capitalize()
        output.append(f"- {html.escape(clean)}")

    return "\n".join(output)

# --- 4. ENHANCED KEY POINTS EXTRACTION ---

def extract_key_points(text: str, max_points: int = 8):
    """
    Enhanced key points extraction with categorization.
    """
    sentences = _sentences(text)
    keywords = set(_keywords(text, k=25))
    points = []
    
    # Categories for key points
    categories = {
        "definition": ["defined as", "refers to", "means", "is a", "is an"],
        "example": ["for example", "for instance", "such as", "like", "illustrated by"],
        "process": ["first", "second", "third", "finally", "next", "then", "step"],
        "comparison": ["similar", "different", "whereas", "while", "however", "in contrast"],
        "conclusion": ["therefore", "thus", "hence", "consequently", "as a result"]
    }
    
    for sent in sentences:
        clean_sent = sent.strip()
        words = _words(sent)
        score = sum(1 for w in words if w in keywords)
        
        # Determine category
        category = None
        for cat, indicators in categories.items():
            if any(ind in sent.lower() for ind in indicators):
                category = cat
                score += 2  # Boost score for categorized sentences
                break
        
        # Select sentences with good keyword density and appropriate length
        if score >= 2 and 10 < len(words) < 30 and len(points) < max_points:
            icon = "📌"
            if category == "definition":
                icon = "📝"
            elif category == "example":
                icon = "💡"
            elif category == "process":
                icon = "🔄"
            elif category == "comparison":
                icon = "⚖️"
            elif category == "conclusion":
                icon = "✅"
                
            points.append(f"{icon} {html.escape(clean_sent)}")

    if not points:
        return ["No strong key points found."]
    return points

# --- 5. ENHANCED FLASHCARDS ---

def generate_flashcards(text: str, n: int = 6):
    """
    Enhanced flashcard generation with multiple question types.
    More robust handling of different content types.
    """
    sentences = _sentences(text)
    keywords = _keywords(text, k=15)
    cards = []
    
    # If no sentences or keywords, create basic cards from the text
    if not sentences or not keywords:
        # Split text into chunks and create basic cards
        text_chunks = text.split('\n\n')
        for i, chunk in enumerate(text_chunks[:n]):
            if chunk.strip():
                cards.append({
                    "question": f"Review point {i+1}:",
                    "answer": chunk.strip(),
                    "type": "review"
                })
        return cards[:n]
    
    # Type 1: Definition cards (more flexible matching)
    for sent in sentences:
        lower = sent.lower()
        
        # Try multiple patterns for definitions
        definition_patterns = [
            (" is ", "What is"),
            (" are ", "What are"),
            (" defined as ", "Define"),
            (" refers to ", "What does"),
            (" means ", "What does"),
            (" can be defined as ", "Define"),
            (" is defined as ", "Define"),
            (" describes ", "What does"),
            (" explains ", "What does"),
            (" involves ", "What does"),
            (" includes ", "What does"),
            (" consists of ", "What does")
        ]
        
        for pattern, question_prefix in definition_patterns:
            if pattern in lower:
                parts = sent.split(pattern, 1)
                if len(parts) == 2:
                    term, desc = parts[0].strip(), parts[1].strip()
                    # More flexible term length check
                    if 1 <= len(term.split()) <= 6 and len(desc) > 5:
                        cards.append({
                            "question": f"{question_prefix} {term}?", 
                            "answer": desc,
                            "type": "definition"
                        })
                        break  # Only create one card per sentence
        
        if len(cards) >= n // 2:
            break
    
    # Type 2: Keyword-based cards (more flexible)
    for kw in keywords:
        if len(cards) >= n:
            break
        if any(kw.lower() in c['question'].lower() for c in cards):
            continue
        
        # Find sentences with this keyword
        relevant_sents = [s for s in sentences if kw.lower() in s.lower()]
        if relevant_sents:
            # Create a question about the keyword
            context = random.choice(relevant_sents)
            if any(ind in context.lower() for ind in ["example", "such as", "like", "illustration"]):
                cards.append({
                    "question": f"Give an example of {kw}.",
                    "answer": context.strip(),
                    "type": "example"
                })
            elif any(ind in context.lower() for ind in ["process", "step", "procedure", "method"]):
                cards.append({
                    "question": f"Explain the process of {kw}.",
                    "answer": context.strip(),
                    "type": "process"
                })
            else:
                cards.append({
                    "question": f"Explain the importance of {kw}.",
                    "answer": context.strip(),
                    "type": "explanation"
                })
    
    # Type 3: Fill-in-the-blank cards (more flexible)
    for sent in sentences:
        if len(cards) >= n:
            break
        
        words = sent.split()
        if len(words) < 6:  # Reduced minimum word count
            continue
            
        # Find a keyword in the sentence
        sent_keywords = [w for w in words if w.lower().strip(".,!?") in keywords]
        if not sent_keywords:
            # If no keywords, pick a random word
            sent_keywords = [w for w in words if len(w) > 3]
        
        if sent_keywords:
            blank_word = random.choice(sent_keywords).strip(".,!?")
            blanked = sent.replace(blank_word, "_____")
            cards.append({
                "question": f"Fill in the blank: {blanked}",
                "answer": blank_word,
                "type": "fill_blank"
            })
    
    # Type 4: Question-answer pairs from sentences
    if len(cards) < n:
        for sent in sentences:
            if len(cards) >= n:
                break
            
            # Convert statement to question
            if sent.strip().endswith('?'):
                # Already a question
                cards.append({
                    "question": sent.strip(),
                    "answer": "Answer based on your knowledge of the topic.",
                    "type": "question"
                })
            else:
                # Convert statement to question
                words = sent.split()
                if len(words) > 5:
                    # Create a "What" question from the sentence
                    cards.append({
                        "question": f"What is described in the following: {sent.strip()}",
                        "answer": "Answer based on your knowledge of the topic.",
                        "type": "question"
                    })
    
    # Type 5: True/False cards
    if len(cards) < n:
        for sent in sentences:
            if len(cards) >= n:
                break
            
            words = sent.split()
            if len(words) > 5:
                # Create a true/false statement
                cards.append({
                    "question": f"True or False: {sent.strip()}",
                    "answer": "True",
                    "type": "true_false"
                })
    
    # If still not enough cards, create generic ones
    if len(cards) < n:
        for i in range(len(cards), n):
            cards.append({
                "question": f"Review point {i+1}:",
                "answer": "Review your notes on this topic.",
                "type": "review"
            })
    
    return cards[:n]