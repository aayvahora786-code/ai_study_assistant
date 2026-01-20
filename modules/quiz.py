import random
import streamlit as st
from .nlp import _sentences, _keywords

def generate_quiz(text: str, num_q: int = 6, difficulty: str = "medium", question_types: list = None):
    """
    Enhanced quiz generation with multiple question types.
    
    Args:
        text (str): Text to generate quiz from
        num_q (int): Number of questions
        difficulty (str): Difficulty level (easy, medium, hard)
        question_types (list): Types of questions to include
            (multiple_choice, true_false, fill_blank, matching)
    """
    if question_types is None:
        question_types = ["multiple_choice", "true_false", "fill_blank", "matching"]
    
    sentences = _sentences(text)
    keywords = _keywords(text)
    quiz = []
    q_per_type = max(1, num_q // len(question_types))
    
    if not sentences or not keywords:
        return quiz
    
    random.shuffle(sentences)
    pool = keywords[:20] if len(keywords) > 20 else keywords
    
    # Generate different types of questions
    for q_type in question_types:
        if q_type == "multiple_choice":
            quiz.extend(_generate_mcq(sentences, pool, q_per_type, difficulty))
        elif q_type == "true_false":
            quiz.extend(_generate_tf(sentences, q_per_type, difficulty))
        elif q_type == "fill_blank":
            quiz.extend(_generate_fill_blank(sentences, q_per_type, difficulty))
        elif q_type == "matching":
            quiz.extend(_generate_matching(sentences, pool, q_per_type, difficulty))
    
    # Shuffle and limit to requested number
    random.shuffle(quiz)
    return quiz[:num_q]

def _generate_mcq(sentences, keywords, num_q, difficulty):
    """
    Generate multiple choice questions.
    """
    questions = []
    
    for s in sentences[:num_q*2]:  # Get more sentences than needed to filter
        kw_hits = [kw for kw in keywords if kw in s.lower()]
        if not kw_hits:
            continue
            
        kw = random.choice(kw_hits)
        
        # Create distractors
        distractors = [w for w in keywords if w != kw and len(w) > 3]
        options = random.sample(distractors, min(3, len(distractors))) + [kw]
        random.shuffle(options)
        
        # Phrase question differently based on difficulty
        if difficulty == "easy":
            question = f"What keyword matches this sentence?\n\"{s}\""
        elif difficulty == "hard":
            # For hard questions, remove the keyword from the sentence
            masked = s.replace(kw, "_____")
            question = f"What term should fill the blank?\n\"{masked}\""
        else:
            question = f"Identify the main concept in:\n\"{s}\""
        
        questions.append({
            "type": "multiple_choice",
            "question": question,
            "options": options,
            "answer_idx": options.index(kw),
            "explanation": f"The sentence emphasizes '{kw}', making it the best choice."
        })
        
        if len(questions) >= num_q:
            break
    
    return questions

def _generate_tf(sentences, num_q, difficulty):
    """
    Generate true/false questions.
    """
    questions = []
    
    for s in sentences[:num_q*2]:
        # Create a statement that might be true or false
        if difficulty == "easy":
            # For easy, use the original sentence as true
            statement = s
            is_true = True
        else:
            # For medium/hard, modify the sentence to sometimes be false
            if random.random() < 0.5:
                statement = s
                is_true = True
            else:
                # Change a key term to make it false
                words = s.split()
                keywords_in_sent = [w for w in words if w.lower().strip(".,!?") in _keywords(s)]
                if keywords_in_sent:
                    # Replace a keyword with an antonym or unrelated term
                    term_to_replace = random.choice(keywords_in_sent).strip(".,!?")
                    replacements = {
                        "increase": "decrease",
                        "decrease": "increase",
                        "important": "insignificant",
                        "similar": "different",
                        "cause": "effect",
                        "effect": "cause",
                        "more": "less",
                        "less": "more",
                        "higher": "lower",
                        "lower": "higher"
                    }
                    
                    replacement = replacements.get(term_to_replace.lower(), "unrelated")
                    statement = s.replace(term_to_replace, replacement, 1)
                    is_true = False
                else:
                    statement = s
                    is_true = True
        
        questions.append({
            "type": "true_false",
            "question": statement,
            "options": ["True", "False"],
            "answer_idx": 0 if is_true else 1,
            "explanation": f"The statement is {'true' if is_true else 'false'} based on the text."
        })
        
        if len(questions) >= num_q:
            break
    
    return questions

def _generate_fill_blank(sentences, num_q, difficulty):
    """
    Generate fill-in-the-blank questions.
    """
    questions = []
    
    for s in sentences[:num_q*2]:
        words = s.split()
        if len(words) < 8:
            continue
            
        # Find keywords in the sentence
        keywords_in_sent = [w for w in words if w.lower().strip(".,!?") in _keywords(s)]
        
        if keywords_in_sent:
            # Select a word to blank out
            blank_word = random.choice(keywords_in_sent).strip(".,!?")
            blanked = s.replace(blank_word, "_____")
            
            # For harder questions, provide hints
            hint = ""
            if difficulty == "easy":
                hint = f" (Hint: The word starts with '{blank_word[0]}')"
            
            questions.append({
                "type": "fill_blank",
                "question": f"Fill in the blank: {blanked}{hint}",
                "answer": blank_word,
                "explanation": f"The correct word is '{blank_word}' based on the context."
            })
            
            if len(questions) >= num_q:
                break
    
    return questions

def _generate_matching(sentences, keywords, num_q, difficulty):
    """
    Generate matching questions (term to definition).
    """
    questions = []
    
    # Find definition sentences
    definitions = []
    for s in sentences:
        lower = s.lower()
        if any(ind in lower for ind in [" is ", " defined as ", " refers to "]):
            if " is " in lower:
                parts = s.split(" is ", 1)
                if len(parts) == 2:
                    term, desc = parts[0].strip(), parts[1].strip()
                    if len(term.split()) <= 4 and len(desc) > 10:
                        definitions.append((term, desc))
            elif " defined as " in lower:
                parts = s.split(" defined as ", 1)
                if len(parts) == 2:
                    term, desc = parts[0].strip(), parts[1].strip()
                    if len(term.split()) <= 4 and len(desc) > 10:
                        definitions.append((term, desc))
    
    # Create matching questions
    if definitions:
        # Group definitions into pairs
        pairs = min(num_q, len(definitions) // 2)
        for i in range(pairs):
            # Select 2-4 definitions
            pair_size = min(4, max(2, len(definitions) - i * 2))
            selected = definitions[i*2:i*2 + pair_size]
            
            terms = [t for t, d in selected]
            defs = [d for t, d in selected]
            random.shuffle(defs)
            
            # Create the question
            term_list = "\n".join([f"{j+1}. {term}" for j, term in enumerate(terms)])
            def_list = "\n".join([f"{chr(65+j)}. {def_[:50]}..." for j, def_ in enumerate(defs)])
            
            # Create answer mapping
            answer_map = {}
            for j, term in enumerate(terms):
                for k, def_ in enumerate(defs):
                    if def_.startswith(selected[terms.index(term)][1]):
                        answer_map[j] = k
                        break
            
            questions.append({
                "type": "matching",
                "question": f"Match the terms with their definitions:\n\n{term_list}\n\n{def_list}",
                "terms": terms,
                "definitions": defs,
                "answer_map": answer_map,
                "explanation": "Match each term with its correct definition based on the text."
            })
    
    return questions

def score_quiz(responses):
    """
    Score quiz responses for different question types.
    """
    correct = 0
    total = len(responses)
    
    for r in responses:
        q_type = r.get("type", "multiple_choice")
        
        if q_type == "multiple_choice" or q_type == "true_false":
            if r["selected"] == r["answer_idx"]:
                correct += 1
        elif q_type == "fill_blank":
            # Case-insensitive partial matching
            user_answer = r["answer"].lower().strip()
            correct_answer = r["correct_answer"].lower().strip()
            
            # Check for exact match or partial match
            if user_answer == correct_answer or correct_answer.startswith(user_answer):
                correct += 1
        elif q_type == "matching":
            # Check if all matches are correct
            all_correct = True
            for term_idx, def_idx in r["matches"].items():
                if r["answer_map"].get(int(term_idx)) != int(def_idx):
                    all_correct = False
                    break
            if all_correct:
                correct += 1
    
    return correct, total

def render_quiz_feedback(quiz, responses):
    """
    Render feedback for each quiz question.
    """
    for i, (q, r) in enumerate(zip(quiz, responses)):
        q_type = q.get("type", "multiple_choice")
        
        if q_type == "multiple_choice" or q_type == "true_false":
            if r["selected"] == q["answer_idx"]:
                st.success(f"Q{i+1}: ✅ Correct")
            else:
                correct_option = q["options"][q["answer_idx"]]
                explanation = q.get("explanation", "")
                st.error(f"Q{i+1}: ❌ Incorrect. Correct: {correct_option}\nℹ️ {explanation}")
        elif q_type == "fill_blank":
            user_answer = r["answer"].lower().strip()
            correct_answer = q["answer"].lower().strip()
            
            if user_answer == correct_answer or correct_answer.startswith(user_answer):
                st.success(f"Q{i+1}: ✅ Correct")
            else:
                explanation = q.get("explanation", "")
                st.error(f"Q{i+1}: ❌ Incorrect. Correct answer: {q['answer']}\nℹ️ {explanation}")
        elif q_type == "matching":
            all_correct = True
            for term_idx, def_idx in r["matches"].items():
                if q["answer_map"].get(int(term_idx)) != int(def_idx):
                    all_correct = False
                    break
            
            if all_correct:
                st.success(f"Q{i+1}: ✅ All matches correct")
            else:
                st.error(f"Q{i+1}: ❌ Some matches incorrect")
                # Show correct matches
                correct_matches = []
                for j, term in enumerate(q["terms"]):
                    correct_idx = q["answer_map"][j]
                    correct_matches.append(f"{term} → {q['definitions'][correct_idx][:30]}...")
                st.info("Correct matches:\n" + "\n".join(correct_matches))