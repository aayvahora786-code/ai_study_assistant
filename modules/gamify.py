import random
import streamlit as st
import time

LEVEL_XP_STEP = 120  # XP needed per level (scaled by level)
STREAK_BONUS_STEP = 5
DAILY_CHALLENGE_XP = 15
SPACED_REPETITION_INTERVALS = [1, 3, 7, 14, 30]  # Days


def init_gamestate():
    """Initialize gamification state variables."""
    st.session_state.setdefault("xp", 0)
    st.session_state.setdefault("streak", 0)
    st.session_state.setdefault("coins", 0)
    st.session_state.setdefault("level", 1)
    st.session_state.setdefault("badges", [])
    st.session_state.setdefault("daily_done", False)
    st.session_state.setdefault("study_streak", 0)
    st.session_state.setdefault("last_study_date", None)
    st.session_state.setdefault("flashcard_progress", {})
    st.session_state.setdefault("current_quiz", None)
    st.session_state.setdefault("quiz_responses", [])
    st.session_state.setdefault("achievements", {
        "first_summary": False,
        "first_quiz": False,
        "perfect_quiz": False,
        "streak_week": False,
        "level_5": False,
        "level_10": False,
        "collector": False
    })


def _level_threshold(level: int) -> int:
    return level * LEVEL_XP_STEP


def award_xp(amount: int):
    """Award XP and handle level ups with achievements."""
    st.session_state.xp += max(0, amount)

    # Check for level up
    while st.session_state.xp >= _level_threshold(st.session_state.level):
        st.session_state.level += 1
        st.session_state.badges.append(f"Level {st.session_state.level} Achieved")
        st.toast(f"🎉 Level Up! You reached Level {st.session_state.level}")

        if st.session_state.level == 5 and not st.session_state.achievements["level_5"]:
            st.session_state.achievements["level_5"] = True
            st.session_state.badges.append("🏆 Level 5 Master")
            st.balloons()
        elif st.session_state.level == 10 and not st.session_state.achievements["level_10"]:
            st.session_state.achievements["level_10"] = True
            st.session_state.badges.append("🏆 Level 10 Expert")
            st.balloons()


def award_coins(amount: int):
    """Award coins."""
    st.session_state.coins += max(0, amount)

    if st.session_state.coins >= 100 and not st.session_state.achievements["collector"]:
        st.session_state.achievements["collector"] = True
        st.session_state.badges.append("💰 Coin Collector")
        st.balloons()


def update_streak(score_ratio: float):
    """Update streak based on quiz score ratio."""
    if score_ratio >= 0.6:
        st.session_state.streak += 1
        award_coins(2)

        if st.session_state.streak >= 7 and not st.session_state.achievements["streak_week"]:
            st.session_state.achievements["streak_week"] = True
            st.session_state.badges.append("🔥 Week Streak")
            st.balloons()

        if st.session_state.streak % STREAK_BONUS_STEP == 0:
            st.success(f"🔥 Streak {st.session_state.streak}! Bonus {STREAK_BONUS_STEP} XP")
            award_xp(STREAK_BONUS_STEP)
    else:
        st.warning("Streak broken ❌")
        st.session_state.streak = 0


def update_study_streak():
    """Update daily study streak."""
    today = time.strftime("%Y-%m-%d")
    yesterday = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))

    if st.session_state.last_study_date == today:
        return  # Already studied today

    if st.session_state.last_study_date == yesterday:
        st.session_state.study_streak += 1
    else:
        st.session_state.study_streak = 1

    st.session_state.last_study_date = today

    if st.session_state.study_streak > 1:
        streak_xp = min(10, st.session_state.study_streak)
        st.success(f"📚 Study streak: {st.session_state.study_streak} days! +{streak_xp} XP")
        award_xp(streak_xp)


def daily_challenge_button():
    """Daily challenge button for bonus XP."""
    if not st.session_state.daily_done:
        if st.button("🎯 Daily Challenge (Earn XP)", key="btn_daily_challenge"):
            st.session_state.daily_done = True
            award_xp(DAILY_CHALLENGE_XP)
            st.success(f"+{DAILY_CHALLENGE_XP} XP for completing today's challenge!")
    else:
        st.info("Daily challenge completed. Come back tomorrow!")


def progress_header():
    """Display progress bar and gamification stats."""
    threshold = _level_threshold(st.session_state.level)
    pct = min(100, int(100 * st.session_state.xp / threshold)) if threshold else 0
    st.markdown(
        f"""
        <div style="display:flex;gap:12px;align-items:center;">
          <div style="flex:1;">
            <div style="height:10px;background:#e2e8f0;border-radius:8px;">
              <div style="width:{pct}%;height:10px;background:#2563eb;border-radius:8px;"></div>
            </div>
            <div style="font-size:0.9rem;color:#64748b;margin-top:6px;">
              XP: {st.session_state.xp}/{threshold} &bull; Level {st.session_state.level} &bull;
              Streak {st.session_state.streak} &bull; Coins {st.session_state.coins}
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def mini_game_flash_fill(cards):
    """
    Mini-game: Flashcard practice with spaced repetition.
    Handles different card types gracefully.
    """
    st.subheader("Mini Game: Flashcard Practice")
    if not cards:
        st.info("Add some flashcards first.")
        return

    card = select_card_for_review(cards)
    card_type = card.get("type", "definition")

    if card_type == "fill_blank":
        answer_words = card["answer"].split()
        if len(answer_words) < 3:
            st.info("Answer too short for masking—showing full card instead.")
            st.write(f"❓ {card['question']}")
            with st.expander("Show Answer"):
                st.write(card["answer"])
            return

        mask_count = max(1, min(3, len(answer_words) // 3))
        idx = sorted(random.sample(range(len(answer_words)), mask_count))
        masked = ["____" if i in idx else w for i, w in enumerate(answer_words)]

        st.write(f"❓ {card['question']}")
        st.write(" ".join(masked))

        guess = st.text_input("Type the missing words or full answer", key="mini_game_guess")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Check Answer", key="mini_game_check"):
                normalized_guess = " ".join(guess.lower().split())
                normalized_answer = " ".join(card["answer"].lower().split())
                g_tokens = set(normalized_guess.split())
                a_tokens = set(normalized_answer.split())
                overlap = len(g_tokens & a_tokens) / max(1, len(a_tokens))

                if normalized_guess in normalized_answer or overlap >= 0.6:
                    st.success("✅ Correct! +5 XP")
                    award_xp(5)
                    award_coins(1)
                    update_card_progress(card, True)
                else:
                    st.error(f"❌ Correct answer: {card['answer']}")
                    update_card_progress(card, False)

        with col2:
            if st.button("Show Answer", key="mini_game_show"):
                st.info(f"Answer: {card['answer']}")
                update_card_progress(card, False)

    elif card_type in ("definition", "explanation", "process"):
        st.write(f"❓ {card['question']}")

        with st.expander("Show Answer"):
            st.write(card["answer"])

        col1, col2 = st.columns(2)
        with col1:
            if st.button("I knew this", key="mini_game_knew"):
                st.success("✅ Great job! +3 XP")
                award_xp(3)
                award_coins(1)
                update_card_progress(card, True)

        with col2:
            if st.button("I didn't know this", key="mini_game_didnt_know"):
                st.info("Keep practicing! +1 XP")
                award_xp(1)
                update_card_progress(card, False)

    elif card_type == "true_false":
        st.write(f"❓ {card['question']}")
        answer = st.radio("Your answer:", ["True", "False"], key="mini_game_tf")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Submit", key="mini_game_tf_submit"):
                if answer == card.get("answer", "True"):
                    st.success("✅ Correct! +3 XP")
                    award_xp(3)
                    award_coins(1)
                    update_card_progress(card, True)
                else:
                    st.error(f"❌ Incorrect. The answer is: {card['answer']}")
                    update_card_progress(card, False)

        with col2:
            if st.button("Show Answer", key="mini_game_tf_show"):
                st.info(f"Answer: {card['answer']}")
                update_card_progress(card, False)

    else:
        # Generic review for other types
        st.write(f"❓ {card['question']}")

        with st.expander("Show Answer"):
            st.write(card["answer"])

        if st.button("Mark as Reviewed", key="mini_game_reviewed"):
            st.success("✅ Reviewed! +2 XP")
            award_xp(2)
            award_coins(1)
            update_card_progress(card, True)


def select_card_for_review(cards):
    """Select a card for review based on spaced repetition algorithm."""
    if not st.session_state.flashcard_progress:
        return random.choice(cards)

    today = time.time()
    cards_with_scores = []

    for card in cards:
        card_id = f"{card['question']}:{card['answer']}"
        if card_id in st.session_state.flashcard_progress:
            progress = st.session_state.flashcard_progress[card_id]
            next_review = progress.get("next_review", 0)

            if next_review <= today:
                cards_with_scores.append((card, 100))
            else:
                days_until = (next_review - today) / 86400
                cards_with_scores.append((card, max(1, 10 - days_until)))
        else:
            cards_with_scores.append((card, 50))

    cards_with_scores.sort(key=lambda x: x[1], reverse=True)
    top_cards = [c for c, _ in cards_with_scores[:3]]
    return random.choice(top_cards)


def update_card_progress(card, correct: bool):
    """Update card progress based on the SM-2 spaced repetition algorithm."""
    card_id = f"{card['question']}:{card['answer']}"
    today = time.time()

    if card_id not in st.session_state.flashcard_progress:
        st.session_state.flashcard_progress[card_id] = {
            "review_count": 0,
            "ease_factor": 2.5,
            "interval": 1,
            "next_review": today
        }

    progress = st.session_state.flashcard_progress[card_id]
    progress["review_count"] += 1

    if correct:
        if progress["review_count"] == 1:
            progress["interval"] = 1
        elif progress["review_count"] == 2:
            progress["interval"] = 6
        else:
            # SM-2 interval calculation
            progress["interval"] = max(1, int(progress["interval"] * progress["ease_factor"]))
        # Slightly increase ease factor for correct answers (SM-2 quality = 4 approximation)
        progress["ease_factor"] = max(1.3, progress["ease_factor"] + 0.1)
    else:
        # Reset interval and reduce ease factor for incorrect answers
        progress["interval"] = 1
        progress["ease_factor"] = max(1.3, progress["ease_factor"] - 0.2)

    progress["next_review"] = today + (progress["interval"] * 86400)


def achievements_panel():
    """Display achievements panel."""
    with st.expander("🏆 Achievements"):
        cols = st.columns(3)

        achievements_list = [
            ("first_summary", "📝 First Summary", "Generate your first summary"),
            ("first_quiz", "🧠 First Quiz", "Complete your first quiz"),
            ("perfect_quiz", "✨ Perfect Score", "Get 100% on a quiz"),
            ("streak_week", "🔥 Week Streak", "Maintain a 7-day streak"),
            ("level_5", "🏆 Level 5", "Reach level 5"),
            ("level_10", "🏆 Level 10", "Reach level 10"),
            ("collector", "💰 Coin Collector", "Earn 100 coins")
        ]

        for i, (key, title, desc) in enumerate(achievements_list):
            with cols[i % 3]:
                if st.session_state.achievements.get(key):
                    st.success(f"**{title}**\n{desc}")
                else:
                    st.markdown(f"**{title}**\n{desc}")


def study_recommendations():
    """Provide study recommendations based on user progress."""
    recommendations = []

    if st.session_state.level < 3:
        recommendations.append("Focus on generating summaries to build foundational knowledge.")
    elif st.session_state.level < 7:
        recommendations.append("Try more challenging quizzes to test your understanding.")
    else:
        recommendations.append("Challenge yourself with hard difficulty quizzes and daily challenges.")

    if st.session_state.streak == 0:
        recommendations.append("Start with easier quizzes to build your streak.")
    elif st.session_state.streak < 3:
        recommendations.append("Keep going! You're building momentum.")
    else:
        recommendations.append("Great job maintaining your streak! Try a daily challenge.")

    if st.session_state.flashcard_progress:
        due_cards = sum(
            1 for p in st.session_state.flashcard_progress.values()
            if p.get("next_review", 0) <= time.time()
        )
        if due_cards > 0:
            recommendations.append(f"You have **{due_cards}** flashcard(s) due for review.")

    for rec in recommendations:
        st.info(rec)
