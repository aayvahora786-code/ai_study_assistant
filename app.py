"""
app.py — AI Study Assistant
Streamlit front-end: Lecture→Notes, Flashcards, Quiz, Exam Analysis, Report, Progress
"""
import os
import time
import html as html_mod
import streamlit as st
from dotenv import load_dotenv
from huggingface_hub import login

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
    topic_frequency, marks_distribution, subject_distribution,
    year_trend, topic_year_heatmap, important_questions,
    plot_topic_frequency, plot_marks_distribution,
    plot_subject_distribution, plot_year_trend, plot_topic_heatmap
)
from modules.report import generate_report

# ── ENV & AUTH ─────────────────────────────────────────────
load_dotenv()
hf_token = os.getenv("HUGGINGFACE_TOKEN")
if hf_token:
    try:
        login(hf_token)
    except Exception:
        pass

# ── PAGE CONFIG ────────────────────────────────────────────
st.set_page_config(
    page_title="AI Study Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)
load_css()
ensure_dirs()
init_gamestate()

# ── SIDEBAR ────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center;padding:1.2rem 0 0.5rem;">
          <div style="font-size:2.6rem;">🎓</div>
          <div style="font-size:1.25rem;font-weight:700;color:#fff;
                      font-family:'Poppins',sans-serif;margin-top:4px;">
            AI Study Assistant
          </div>
          <div style="font-size:0.75rem;color:rgba(255,255,255,0.6);margin-top:2px;">
            Learn smarter, not harder
          </div>
        </div>
        <hr style="border-color:rgba(255,255,255,0.15);margin:0.8rem 0;">
        """,
        unsafe_allow_html=True,
    )
    daily_challenge_button()
    st.markdown("<hr style='border-color:rgba(255,255,255,0.15);margin:0.6rem 0;'>",
                unsafe_allow_html=True)

    # XP progress in sidebar
    from modules.gamify import _level_threshold
    threshold = _level_threshold(st.session_state.level)
    pct = min(100, int(100 * st.session_state.xp / threshold)) if threshold else 0
    st.markdown(
        f"""
        <div style="padding:0 0.5rem;">
          <div style="font-size:0.72rem;color:rgba(255,255,255,0.6);
                      text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">
            Level {st.session_state.level} Progress
          </div>
          <div class="xp-bar-wrap">
            <div class="xp-bar-fill" style="width:{pct}%"></div>
          </div>
          <div class="xp-bar-label">{st.session_state.xp} / {threshold} XP</div>
          <div class="stat-pills" style="margin-top:10px;">
            <span class="stat-pill">⚡ {st.session_state.xp} XP</span>
            <span class="stat-pill">🔥 {st.session_state.streak} Streak</span>
            <span class="stat-pill">🪙 {st.session_state.coins} Coins</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<hr style='border-color:rgba(255,255,255,0.15);margin:0.8rem 0;'>",
                unsafe_allow_html=True)
    st.markdown(
        """
        <div style="font-size:0.72rem;color:rgba(255,255,255,0.5);padding:0 0.5rem 1rem;">
          <b style="color:rgba(255,255,255,0.7);">Features</b><br>
          🎙️ Audio Transcription<br>
          📝 Smart Summarisation<br>
          🧠 AI Flashcards<br>
          📝 Auto Quiz<br>
          📊 Past Paper Analysis<br>
          🏆 Gamified Progress
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── TABS ───────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🎙️ Lecture → Notes",
    "🧠 Flashcards",
    "📝 Quiz",
    "📊 Exam Analysis",
    "📑 Study Report",
    "🏆 Progress",
])

# ═══════════════════════════════════════════════════════════
# TAB 1 — LECTURE → NOTES
# ═══════════════════════════════════════════════════════════
with tab1:
    progress_header()
    st.markdown(
        """
        <div class="hero-banner">
          <h2>🎙️ Lecture to Structured Notes</h2>
          <p>Upload an audio lecture and get an instant transcript, smart summary,
             key points, and topic extraction — all automatically.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_l, col_r = st.columns([3, 2])
    with col_l:
        audio_file  = st.file_uploader("Upload lecture audio (MP3 / WAV / M4A)",
                                       type=["mp3", "wav", "m4a"])
        chunk_size  = st.slider("Chunk size (seconds)", 30, 120, 60, key="chunk_size")
        language    = st.selectbox("Recognition language",
                                   ["en-IN", "en-US", "en-GB", "hi-IN"], key="stt_lang")
    with col_r:
        focus       = st.selectbox("Summary focus",
                                   ["General", "Concepts", "Definitions",
                                    "Examples", "Processes"], key="summary_focus")
        n_bullets   = st.slider("Summary bullets", 4, 12, 7, key="summary_bullets")
        n_keypoints = st.slider("Key points", 4, 12, 8, key="n_keypoints")

    focus_map = {
        "General": None, "Concepts": "concepts", "Definitions": "definitions",
        "Examples": "examples", "Processes": "processes",
    }

    if audio_file and st.button("▶ Process Lecture", key="btn_process_lecture"):
        with st.spinner("🔄 Transcribing audio…"):
            path       = save_uploaded_file(audio_file, "data/user_uploads")
            result     = transcribe_audio(path, language, chunk_size)
            transcript = result["transcript"]
            segments   = result["segments"]
            update_study_streak()

        if not transcript.strip():
            st.warning("⚠️ Could not extract speech. Check the file or try a different language.")
        else:
            st.success(f"✅ Transcription complete — {len(segments)} chunk(s) processed.")

            # Transcript
            st.markdown(
                '<div class="section-header">'
                '<div class="sh-icon">📜</div><h3>Transcript</h3></div>',
                unsafe_allow_html=True,
            )
            with st.expander("View full transcript", expanded=False):
                for seg in segments:
                    # Split label from text for nicer rendering
                    if "]" in seg:
                        label, text_part = seg.split("]", 1)
                        st.markdown(
                            f'<div class="transcript-line">'
                            f'<div class="chunk-label">{label.lstrip("[")}</div>'
                            f'{html_mod.escape(text_part.strip())}</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f'<div class="transcript-line">{html_mod.escape(seg)}</div>',
                            unsafe_allow_html=True,
                        )

            # Summary
            st.markdown(
                '<div class="section-header">'
                '<div class="sh-icon">📌</div><h3>Smart Summary</h3></div>',
                unsafe_allow_html=True,
            )
            summary = summarize_text(transcript, bullets=n_bullets, focus=focus_map[focus])
            st.markdown(summary, unsafe_allow_html=True)

            # Key Points
            st.markdown(
                '<div class="section-header">'
                '<div class="sh-icon">🔑</div><h3>Key Points</h3></div>',
                unsafe_allow_html=True,
            )
            kps = extract_key_points(transcript, max_points=n_keypoints)
            st.markdown('<div class="kp-grid">' + "".join(kps) + '</div>',
                        unsafe_allow_html=True)

            # Download transcript
            st.download_button(
                "⬇ Download Transcript",
                data="\n\n".join(segments),
                file_name="transcript.txt",
                mime="text/plain",
                key="dl_transcript",
            )

            # First summary achievement
            if not st.session_state.achievements["first_summary"]:
                st.session_state.achievements["first_summary"] = True
                st.session_state.badges.append("📝 First Summary")
                st.balloons()
                st.success("🏅 Achievement unlocked: **First Summary**!")

            award_xp(15)

    # ── Manual text input fallback ──────────────────────────
    st.markdown("<hr class='fancy-divider'>", unsafe_allow_html=True)
    st.markdown(
        '<div class="section-header">'
        '<div class="sh-icon">✍️</div><h3>Or summarise text directly</h3></div>',
        unsafe_allow_html=True,
    )
    manual_text = st.text_area("Paste any text here to summarise",
                                height=180, key="manual_text")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("📌 Generate Summary", key="btn_manual_summary"):
            if not manual_text.strip():
                st.warning("Please paste some text first.")
            else:
                s = summarize_text(manual_text, bullets=n_bullets, focus=focus_map[focus])
                st.markdown(s, unsafe_allow_html=True)
                award_xp(5)
    with col_b:
        if st.button("🔑 Extract Key Points", key="btn_manual_kp"):
            if not manual_text.strip():
                st.warning("Please paste some text first.")
            else:
                kps = extract_key_points(manual_text, max_points=n_keypoints)
                st.markdown('<div class="kp-grid">' + "".join(kps) + '</div>',
                            unsafe_allow_html=True)
                award_xp(5)

# ═══════════════════════════════════════════════════════════
# TAB 2 — FLASHCARDS
# ═══════════════════════════════════════════════════════════
with tab2:
    progress_header()
    st.markdown(
        """
        <div class="hero-banner">
          <h2>🧠 Flashcards & Practice</h2>
          <p>Paste any study text — the AI extracts definitions, examples, and key concepts
             into interactive flashcards with spaced-repetition practice.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    fc_col1, fc_col2 = st.columns([3, 1])
    with fc_col1:
        fc_text = st.text_area("Paste notes or study text",
                                height=220, key="flashcard_text",
                                placeholder="Paste your lecture notes, textbook excerpt, or any study material here…")
    with fc_col2:
        n_cards     = st.slider("Number of cards", 4, 20, 8, key="fc_num")
        card_types  = st.multiselect(
            "Card types",
            ["Definition", "Example", "Explanation", "Fill-in-the-blank",
             "Process", "Importance", "True/False"],
            default=["Definition", "Example", "Explanation"],
            key="fc_types",
        )

    type_map_fc = {
        "Definition": "definition", "Example": "example",
        "Explanation": "explanation", "Fill-in-the-blank": "fill_blank",
        "Process": "process", "Importance": "importance",
        "True/False": "true_false",
    }

    if st.button("✨ Generate Flashcards", key="btn_gen_flashcards"):
        if not fc_text.strip():
            st.warning("⚠️ Please paste some text to generate flashcards.")
        else:
            with st.spinner("Generating flashcards…"):
                all_cards = generate_flashcards(fc_text, n_cards)

            if not all_cards:
                st.warning("Not enough content to generate flashcards.")
            else:
                selected_types = {type_map_fc[t] for t in card_types} if card_types else None
                filtered = [c for c in all_cards
                            if selected_types is None or c.get("type") in selected_types]
                if not filtered:
                    filtered = all_cards
                    st.info("No cards matched the selected types — showing all.")

                st.session_state["generated_cards"] = filtered
                st.success(f"✅ {len(filtered)} flashcard(s) generated!")
                award_xp(10)

    # Render cards
    if st.session_state.get("generated_cards"):
        cards = st.session_state["generated_cards"]
        type_colors = {
            "definition":  ("#4f46e5", "Definition"),
            "example":     ("#10b981", "Example"),
            "explanation": ("#f59e0b", "Explanation"),
            "fill_blank":  ("#7c3aed", "Fill Blank"),
            "process":     ("#0891b2", "Process"),
            "importance":  ("#dc2626", "Importance"),
            "true_false":  ("#6366f1", "True / False"),
            "review":      ("#64748b", "Review"),
            "question":    ("#475569", "Question"),
        }

        # Stats row
        type_counts = {}
        for c in cards:
            t = c.get("type", "review")
            type_counts[t] = type_counts.get(t, 0) + 1
        pills = "".join(
            f'<span style="background:{type_colors.get(t, ("#64748b",""))[0]}22;'
            f'color:{type_colors.get(t, ("#64748b",""))[0]};border-radius:999px;'
            f'padding:2px 10px;font-size:0.75rem;font-weight:600;margin-right:6px;">'
            f'{type_colors.get(t, (None, t.title()))[1]}: {n}</span>'
            for t, n in type_counts.items()
        )
        st.markdown(f'<div style="margin-bottom:12px;">{pills}</div>',
                    unsafe_allow_html=True)

        # Card grid
        html_cards = []
        for i, c in enumerate(cards):
            ctype = c.get("type", "review")
            color, label = type_colors.get(ctype, ("#4f46e5", ctype.title()))
            icon = c.get("icon", "📖")
            q = html_mod.escape(c["question"])
            a = html_mod.escape(c["answer"])
            html_cards.append(
                f'<div class="flashcard">'
                f'  <div class="fc-header" style="background:linear-gradient(135deg,{color},{color}cc);">'
                f'    <div class="fc-num">{i+1}</div>'
                f'    <span style="color:white;font-size:1rem;">{icon}</span>'
                f'    <span class="fc-type-badge">{label}</span>'
                f'  </div>'
                f'  <div class="fc-question">{q}</div>'
                f'  <div class="fc-answer">💬 {a}</div>'
                f'</div>'
            )

        st.markdown('<div class="fc-grid">' + "".join(html_cards) + '</div>',
                    unsafe_allow_html=True)

        # Download flashcards as text
        fc_txt = "\n\n".join(
            f"Q{i+1} [{c.get('type','').upper()}]:\n{c['question']}\n\nA: {c['answer']}"
            for i, c in enumerate(cards)
        )
        st.download_button("⬇ Download Flashcards", data=fc_txt,
                           file_name="flashcards.txt", mime="text/plain",
                           key="dl_flashcards")

        st.markdown("<hr class='fancy-divider'>", unsafe_allow_html=True)
        mini_game_flash_fill(cards)

# ═══════════════════════════════════════════════════════════
# TAB 3 — QUIZ
# ═══════════════════════════════════════════════════════════
with tab3:
    progress_header()
    st.markdown(
        """
        <div class="hero-banner">
          <h2>📝 Auto-Generated Quiz</h2>
          <p>Paste your study content and get a fully scored quiz — MCQ, True/False,
             Fill-in-the-blank, and Matching questions.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    qz_col1, qz_col2 = st.columns([3, 1])
    with qz_col1:
        quiz_text = st.text_area("Paste study content",
                                  height=220, key="quiz_text",
                                  placeholder="Paste textbook content, notes, or lecture transcript here…")
    with qz_col2:
        qn         = st.slider("Number of questions", 3, 15, 6, key="quiz_num")
        difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"],
                                   index=1, key="quiz_difficulty")
        q_types    = st.multiselect(
            "Question types",
            ["Multiple Choice", "True/False", "Fill in the Blank", "Matching"],
            default=["Multiple Choice", "True/False"],
            key="quiz_qtypes",
        )

    type_map_quiz = {
        "Multiple Choice": "multiple_choice",
        "True/False": "true_false",
        "Fill in the Blank": "fill_blank",
        "Matching": "matching",
    }
    selected_types = [type_map_quiz[t] for t in q_types]

    diff_badge = {"easy": "diff-easy", "medium": "diff-medium", "hard": "diff-hard"}

    if st.button("🎯 Generate Quiz", key="btn_gen_quiz"):
        if not quiz_text.strip():
            st.warning("⚠️ Please paste some study content.")
        elif not selected_types:
            st.warning("⚠️ Please select at least one question type.")
        else:
            with st.spinner("Generating quiz…"):
                quiz = generate_quiz(quiz_text, qn, difficulty, selected_types)
            if not quiz:
                st.warning("⚠️ Not enough content to generate quiz questions. Provide more text.")
            else:
                st.session_state["current_quiz"] = quiz
                st.session_state["quiz_submitted"] = False
                st.success(f"✅ {len(quiz)} question(s) ready!")

    # Render active quiz
    if st.session_state.get("current_quiz") and not st.session_state.get("quiz_submitted"):
        quiz = st.session_state["current_quiz"]
        responses = []

        for i, q in enumerate(quiz):
            qtype  = q.get("type", "multiple_choice")
            d_cls  = diff_badge.get(difficulty, "diff-medium")
            q_html = html_mod.escape(q["question"])

            st.markdown(
                f'<div class="quiz-card">'
                f'<div class="quiz-q-num">Question {i+1} of {len(quiz)}'
                f' &nbsp;<span class="diff-badge {d_cls}">{difficulty}</span></div>'
                f'<div class="quiz-question">{q_html}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            if qtype in ("multiple_choice", "true_false"):
                choice = st.radio("Select your answer:", q["options"],
                                  key=f"quiz_q_{i}", label_visibility="collapsed")
                responses.append({
                    "type": qtype,
                    "selected": q["options"].index(choice),
                    "answer_idx": q["answer_idx"],
                })
            elif qtype == "fill_blank":
                ans = st.text_input("Your answer:", key=f"quiz_q_{i}",
                                    placeholder="Type the missing word…")
                responses.append({
                    "type": qtype,
                    "answer": ans,
                    "correct_answer": q["answer"],
                })
            elif qtype == "matching":
                matches = {}
                for j, term in enumerate(q["terms"]):
                    matches[str(j)] = st.selectbox(
                        f"Match: **{term}**",
                        options=list(range(len(q["definitions"]))),
                        format_func=lambda x, defs=q["definitions"]: f"{chr(65+x)}: {defs[x][:50]}",
                        key=f"match_{i}_{j}",
                    )
                responses.append({
                    "type": qtype,
                    "matches": matches,
                    "answer_map": q["answer_map"],
                })

        st.session_state["quiz_responses"] = responses

        if st.button("✅ Submit Quiz", key="btn_submit_quiz"):
            st.session_state["quiz_submitted"] = True
            st.rerun()

    # Show results after submission
    if st.session_state.get("quiz_submitted") and st.session_state.get("current_quiz"):
        quiz      = st.session_state["current_quiz"]
        responses = st.session_state.get("quiz_responses", [])
        correct, total = score_quiz(responses)
        pct = int(100 * correct / max(1, total))

        # Score display
        grade_cls = "great" if pct >= 75 else "ok" if pct >= 50 else "poor"
        grade_msg = "Excellent! 🎉" if pct >= 75 else "Good effort! 👍" if pct >= 50 else "Keep practicing! 💪"
        st.markdown(
            f'<div class="score-ring-wrap">'
            f'  <div class="score-big {grade_cls}">{pct}%</div>'
            f'  <div class="score-label">{correct}/{total} correct — {grade_msg}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Achievements
        if correct == total and not st.session_state.achievements["perfect_quiz"]:
            st.session_state.achievements["perfect_quiz"] = True
            st.session_state.badges.append("✨ Perfect Score")
            st.balloons()
            st.success("🏅 Achievement unlocked: **Perfect Score**!")
        if not st.session_state.achievements["first_quiz"]:
            st.session_state.achievements["first_quiz"] = True
            st.session_state.badges.append("🧠 First Quiz")
            st.success("🏅 Achievement unlocked: **First Quiz**!")

        st.markdown("<br>", unsafe_allow_html=True)
        render_quiz_feedback(quiz, responses)
        update_streak(correct / max(1, total))
        award_xp(int(20 * correct / max(1, total)))

        if st.button("🔄 Try Again", key="btn_retry_quiz"):
            st.session_state["current_quiz"]  = None
            st.session_state["quiz_submitted"] = False
            st.rerun()

# ═══════════════════════════════════════════════════════════
# TAB 4 — EXAM ANALYSIS
# ═══════════════════════════════════════════════════════════
with tab4:
    progress_header()
    st.markdown(
        """
        <div class="hero-banner">
          <h2>📊 Past Paper Analysis</h2>
          <p>Deep-dive into 5-year question trends, topic heatmaps, marks distribution,
             and high-importance question identification for Board, NEET, JEE &amp; GATE.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    exam_sel  = st.selectbox("Select Exam", ["Board", "NEET", "JEE", "GATE"],
                              key="exam_analysis_select")
    exam_path = f"data/kaggle_papers/{exam_sel.lower()}.csv"

    if not os.path.exists(exam_path):
        st.warning(
            f"📂 Dataset `{exam_path}` not found. "
            "Add the CSV file to enable analysis. "
            "Expected columns: `question`, `topic`, `subject`, `marks`, `year`"
        )
    else:
        with st.spinner("Loading dataset…"):
            df = load_and_clean(exam_path)

        # Summary metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Questions", f"{len(df):,}")
        m2.metric("Unique Topics",   df["topic"].nunique())
        m3.metric("Subjects",        df["subject"].nunique())
        years_valid = df[df["year"] > 0]["year"]
        year_range = f"{years_valid.min()} – {years_valid.max()}" if len(years_valid) else "N/A"
        m4.metric("Year Range", year_range)

        st.markdown("<hr class='fancy-divider'>", unsafe_allow_html=True)

        # Row 1: Topic frequency + Marks distribution
        c1, c2 = st.columns([3, 2])
        with c1:
            st.plotly_chart(plot_topic_frequency(topic_frequency(df)),
                            use_container_width=True)
        with c2:
            st.plotly_chart(plot_marks_distribution(marks_distribution(df)),
                            use_container_width=True)

        # Row 2: Year trend + Subject distribution
        c3, c4 = st.columns(2)
        with c3:
            st.plotly_chart(plot_year_trend(year_trend(df)),
                            use_container_width=True)
        with c4:
            st.plotly_chart(plot_subject_distribution(subject_distribution(df)),
                            use_container_width=True)

        # Heatmap
        pivot = topic_year_heatmap(df, top_n=10)
        if not pivot.empty:
            st.plotly_chart(plot_topic_heatmap(pivot), use_container_width=True)

        # Important questions table
        st.markdown(
            '<div class="section-header">'
            '<div class="sh-icon">⭐</div><h3>Most Important Questions</h3></div>',
            unsafe_allow_html=True,
        )
        imp_df = important_questions(df)
        st.dataframe(
            imp_df[["norm_q", "frequency", "avg_marks", "latest_year", "score"]]
            .rename(columns={
                "norm_q": "Question",
                "frequency": "Times Asked",
                "avg_marks": "Avg Marks",
                "latest_year": "Latest Year",
                "score": "Priority Score",
            }),
            use_container_width=True,
            height=400,
        )

        award_xp(25)

# ═══════════════════════════════════════════════════════════
# TAB 5 — STUDY REPORT
# ═══════════════════════════════════════════════════════════
with tab5:
    progress_header()
    st.markdown(
        """
        <div class="hero-banner">
          <h2>📑 Generate Study Report</h2>
          <p>Export a beautiful, printable HTML report with exam analysis, topic breakdown,
             important questions, and your personal progress stats.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    exam_rep    = st.selectbox("Select Exam for Report",
                                ["Board", "NEET", "JEE", "GATE"], key="exam_report_select")
    report_path = f"data/kaggle_papers/{exam_rep.lower()}.csv"

    if not os.path.exists(report_path):
        st.warning(f"Dataset `{report_path}` not found. Add the CSV file first.")
    else:
        if st.button("📑 Generate Report", key="btn_gen_report"):
            with st.spinner("Building report…"):
                try:
                    df = load_and_clean(report_path)
                    data = {
                        "exam_name":    exam_rep,
                        "topic_freq":   topic_frequency(df).to_dict("records"),
                        "subj_freq":    subject_distribution(df).to_dict("records"),
                        "marks_dist":   marks_distribution(df).to_dict("records"),
                        "imp_questions": important_questions(df).to_dict("records"),
                        "total_q":      len(df),
                        "n_topics":     df["topic"].nunique(),
                        "n_subjects":   df["subject"].nunique(),
                        "xp":           st.session_state.xp,
                        "streak":       st.session_state.streak,
                        "coins":        st.session_state.coins,
                        "level":        st.session_state.level,
                        "badges":       st.session_state.badges,
                        "achievements": st.session_state.achievements,
                    }
                    html_out = generate_report(data)
                    fname    = f"report_{exam_rep.lower()}.html"

                    st.success(f"✅ Report generated: **{fname}**")
                    st.download_button(
                        "⬇ Download Report (HTML)",
                        data=html_out,
                        file_name=fname,
                        mime="text/html",
                        key="dl_report",
                    )
                    st.info("You can also open the saved file directly in any browser.")
                except Exception as e:
                    st.error(f"❌ Report generation failed: {e}")

# ═══════════════════════════════════════════════════════════
# TAB 6 — PROGRESS
# ═══════════════════════════════════════════════════════════
with tab6:
    progress_header()
    st.markdown(
        """
        <div class="hero-banner">
          <h2>🏆 Your Learning Progress</h2>
          <p>Track your XP, streaks, achievements, and get personalised study recommendations
             powered by your activity.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Stats row
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("🎮 Level",         st.session_state.level)
    s2.metric("⚡ Total XP",      st.session_state.xp)
    s3.metric("🔥 Quiz Streak",   f"{st.session_state.streak} days")
    s4.metric("🪙 Coins",         st.session_state.coins)

    if st.session_state.study_streak:
        st.metric("📚 Study Streak", f"{st.session_state.study_streak} day(s)")
    if st.session_state.last_study_date:
        st.caption(f"Last studied: {st.session_state.last_study_date}")

    st.markdown("<hr class='fancy-divider'>", unsafe_allow_html=True)

    # Recent badges
    st.markdown(
        '<div class="section-header">'
        '<div class="sh-icon">🏅</div><h3>Recent Badges</h3></div>',
        unsafe_allow_html=True,
    )
    if st.session_state.badges:
        chips = "".join(
            f'<span class="badge-chip earned">{b}</span>'
            for b in st.session_state.badges[-10:]
        )
        st.markdown(f'<div class="badge-grid">{chips}</div>', unsafe_allow_html=True)
    else:
        st.info("No badges yet — complete quizzes, summaries, and daily challenges to earn them!")

    st.markdown("<hr class='fancy-divider'>", unsafe_allow_html=True)

    # Achievements
    st.markdown(
        '<div class="section-header">'
        '<div class="sh-icon">🎯</div><h3>Achievements</h3></div>',
        unsafe_allow_html=True,
    )
    achievements_panel()

    st.markdown("<hr class='fancy-divider'>", unsafe_allow_html=True)

    # Study recommendations
    st.markdown(
        '<div class="section-header">'
        '<div class="sh-icon">💡</div><h3>Personalised Recommendations</h3></div>',
        unsafe_allow_html=True,
    )
    study_recommendations()
