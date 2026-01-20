import os
import time
import streamlit as st
from dotenv import load_dotenv
from huggingface_hub import login

# Local modules
from modules.utils import ensure_dirs, save_uploaded_file, load_css
from modules.stt import transcribe_audio
from modules.nlp import summarize_text, extract_key_points, generate_flashcards
from modules.quiz import generate_quiz, score_quiz, render_quiz_feedback
from modules.gamify import (
    init_gamestate, award_xp, update_streak, update_study_streak,
    mini_game_flash_fill, progress_header, daily_challenge_button,
    achievements_panel, study_recommendations
)
from modules.exam_preprocess import load_and_clean
from modules.exam_analysis import (
    topic_frequency, marks_distribution, important_questions,
    plot_topic_frequency, plot_marks_distribution
)
from modules.report import generate_report

# ------------------ ENV & AUTH ------------------
load_dotenv()
hf_token = os.getenv("HUGGINGFACE_TOKEN")
if hf_token:
    try:
        login(hf_token)
    except Exception:
        pass

# ------------------ STREAMLIT SETUP ------------------
st.set_page_config(page_title="AI Study Assistant", page_icon="📚", layout="wide")
load_css()
ensure_dirs()
init_gamestate()

# ------------------ SIDEBAR ------------------
st.sidebar.title("AI Study Assistant")
st.sidebar.markdown("Lecture → Notes → Flashcards → Quiz → Exam Analysis")
daily_challenge_button()
st.sidebar.markdown(
    f"**XP:** {st.session_state.xp} | "
    f"**Streak:** {st.session_state.streak} | "
    f"**Coins:** {st.session_state.coins}"
)

# ------------------ TABS ------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🎙️ Lecture → Notes",
    "🧠 Flashcards",
    "📝 Quiz",
    "📊 Exam Analysis",
    "📑 Study Report",
    "🏆 Progress"
])

# ------------------ TAB 1: Lecture to Notes ------------------
with tab1:
    progress_header()
    st.header("Lecture to Structured Notes")
    audio_file = st.file_uploader("Upload lecture audio", type=["mp3", "wav", "m4a"])
    chunk_size = st.slider("Chunk size (seconds)", 30, 120, 60)
    language = st.selectbox("Language", ["en-IN", "en-US", "hi-IN"])
    
    # Summary focus options
    focus = st.selectbox("Summary focus", ["General", "Concepts", "Definitions", "Examples", "Processes"])
    focus_map = {
        "General": None,
        "Concepts": "concepts",
        "Definitions": "definitions",
        "Examples": "examples",
        "Processes": "processes"
    }

    if audio_file and st.button("Process Lecture"):
        with st.spinner("🔄 Processing lecture... please wait"):
            path = save_uploaded_file(audio_file, "data/user_uploads")
            result = transcribe_audio(path, language, chunk_size)
            transcript = result["transcript"]
            segments = result["segments"]
            time.sleep(0.5)
            
            # Update study streak
            update_study_streak()

        st.success("✅ Lecture processed successfully!")
        st.toast("📝 Transcript and notes ready!")

        st.subheader("Transcript")
        with st.expander("View full transcript"):
            for s in segments:
                st.write("•", s)

        st.subheader("Summary Notes")
        summary = summarize_text(transcript, focus=focus_map[focus])
        st.markdown(summary, unsafe_allow_html=True)
        
        # Check for first summary achievement
        if not st.session_state.achievements["first_summary"]:
            st.session_state.achievements["first_summary"] = True
            st.session_state.badges.append("📝 First Summary")
            st.balloons()

        st.subheader("Key Points")
        for kp in extract_key_points(transcript):
            st.markdown(kp, unsafe_allow_html=True)

        award_xp(15)

# ------------------ TAB 2: Flashcards ------------------
with tab2:
    progress_header()
    st.header("Flashcards & Practice")
    text = st.text_area("Paste notes or transcript", height=200)
    n = st.slider("Number of flashcards", 4, 20, 8)
    
    # Flashcard type selection
    card_types = st.multiselect(
        "Select card types to generate",
        ["Definition", "Example", "Explanation", "Fill-in-the-blank"],
        default=["Definition", "Example"]
    )

    if st.button("Generate Flashcards"):
        cards = generate_flashcards(text, n)
        if cards:
            # Filter by selected types
            type_map = {
                "Definition": "definition",
                "Example": "example",
                "Explanation": "explanation",
                "Fill-in-the-blank": "fill_blank"
            }
            
            filtered_types = [type_map[t] for t in card_types]
            filtered_cards = [c for c in cards if c.get("type") in filtered_types]
            
            # Display cards
            for i, c in enumerate(filtered_cards):
                card_type = c.get("type", "definition")
                icon = "📝" if card_type == "definition" else "💡" if card_type == "example" else "🔍" if card_type == "explanation" else "✏️"
                
                st.markdown(
                    f"<div class='flashcard'><b>{icon} Q{i+1}:</b> {c['question']}<br>"
                    f"<b>A:</b> {c['answer']}</div>",
                    unsafe_allow_html=True
                )
            
            award_xp(10)
            mini_game_flash_fill(filtered_cards)
        else:
            st.warning("Insufficient content.")

# ------------------ TAB 3: Quiz ------------------
with tab3:
    progress_header()
    st.header("Auto-Generated Quiz")
    quiz_text = st.text_area("Paste study content", height=200)
    qn = st.slider("Number of questions", 3, 12, 6)
    difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"])
    
    # Question type selection
    question_types = st.multiselect(
        "Select question types",
        ["Multiple Choice", "True/False", "Fill in the Blank", "Matching"],
        default=["Multiple Choice", "True/False"]
    )
    
    type_map = {
        "Multiple Choice": "multiple_choice",
        "True/False": "true_false",
        "Fill in the Blank": "fill_blank",
        "Matching": "matching"
    }
    
    selected_types = [type_map[t] for t in question_types]

    if st.button("Generate Quiz"):
        quiz = generate_quiz(quiz_text, qn, difficulty, selected_types)
        responses = []

        for i, q in enumerate(quiz):
            q_type = q.get("type", "multiple_choice")
            
            st.write(f"**Q{i+1}. {q['question']}**")
            
            if q_type == "multiple_choice" or q_type == "true_false":
                choice = st.radio("Select answer", q["options"], key=i)
                responses.append({
                    "type": q_type,
                    "selected": q["options"].index(choice),
                    "answer_idx": q["answer_idx"]
                })
            elif q_type == "fill_blank":
                answer = st.text_input("Your answer", key=i)
                responses.append({
                    "type": q_type,
                    "answer": answer,
                    "correct_answer": q["answer"]
                })
            elif q_type == "matching":
                # Create matching interface
                matches = {}
                for j, term in enumerate(q["terms"]):
                    matches[str(j)] = st.selectbox(
                        f"Match for: {term}",
                        options=list(range(len(q["definitions"]))),
                        format_func=lambda x: f"{chr(65+x)}",
                        key=f"match_{i}_{j}"
                    )
                
                responses.append({
                    "type": q_type,
                    "matches": matches,
                    "answer_map": q["answer_map"]
                })

        if st.button("Submit Quiz"):
            correct, total = score_quiz(responses)
            st.success(f"Score: {correct}/{total}")
            
            # Check for perfect quiz achievement
            if correct == total and not st.session_state.achievements["perfect_quiz"]:
                st.session_state.achievements["perfect_quiz"] = True
                st.session_state.badges.append("✨ Perfect Score")
                st.balloons()
            
            # Check for first quiz achievement
            if not st.session_state.achievements["first_quiz"]:
                st.session_state.achievements["first_quiz"] = True
                st.session_state.badges.append("🧠 First Quiz")
            
            render_quiz_feedback(quiz, responses)
            update_streak(correct / max(1, total))
            award_xp(int(20 * correct / total))

# ------------------ TAB 4: Exam Analysis ------------------
with tab4:
    progress_header()
    st.header("Past Paper Analysis")
    exam = st.selectbox("Select Exam", ["Board", "NEET", "JEE", "GATE"])
    path = f"data/kaggle_papers/{exam.lower()}.csv"

    if os.path.exists(path):
        df = load_and_clean(path)
        st.dataframe(df.head())

        st.plotly_chart(plot_topic_frequency(topic_frequency(df)), use_container_width=True)
        st.plotly_chart(plot_marks_distribution(marks_distribution(df)), use_container_width=True)
        st.dataframe(important_questions(df))
        award_xp(25)
    else:
        st.warning("Dataset not found.")

# ------------------ TAB 5: Report ------------------
with tab5:
    progress_header()
    st.header("Generate Study Report")
    exam = st.selectbox("Exam", ["Board", "NEET", "JEE", "GATE"])

    if st.button("Generate Report"):
        df = load_and_clean(f"data/kaggle_papers/{exam.lower()}.csv")
        data = {
            "exam_name": exam,
            "topic_freq": topic_frequency(df).to_dict("records"),
            "imp_questions": important_questions(df).to_dict("records"),
            "xp": st.session_state.xp,
            "streak": st.session_state.streak,
            "coins": st.session_state.coins,
            "badges": st.session_state.badges,
            "achievements": st.session_state.achievements
        }
        out = generate_report(data)

        st.success(f"📑 Report for {exam} generated successfully!")
        st.toast(f"Report for {exam} ready.")
        st.info(
            f"Your report has been saved as **report_{exam.lower()}.html**. "
            "Open this file in your browser to view the full analysis."
        )

# ------------------ TAB 6: Progress ------------------
with tab6:
    progress_header()
    st.header("Your Learning Progress")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Statistics")
        st.metric("Current Level", st.session_state.level)
        st.metric("Total XP", st.session_state.xp)
        st.metric("Current Streak", f"{st.session_state.streak} days")
        st.metric("Coins Earned", st.session_state.coins)
        
        if st.session_state.last_study_date:
            st.metric("Last Study", st.session_state.last_study_date)
        
        if st.session_state.study_streak:
            st.metric("Study Streak", f"{st.session_state.study_streak} days")
    
    with col2:
        st.subheader("🏆 Recent Badges")
        if st.session_state.badges:
            for badge in st.session_state.badges[-5:]:  # Show last 5 badges
                st.success(badge)
        else:
            st.info("No badges earned yet. Keep studying!")
    
    st.subheader("🎯 Achievements")
    achievements_panel()
    
    st.subheader("📚 Study Recommendations")
    study_recommendations()