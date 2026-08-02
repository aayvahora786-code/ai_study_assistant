# AI Study Assistant (India)

Convert lectures to notes, flashcards, quizzes, and analyze 5-year past papers (Board, NEET, JEE, GATE). Built with Streamlit, Google Speech Recognition, and Jinja2.

---

## Features

| Tab | Feature |
|-----|---------|
| 🎙️ Lecture → Notes | Upload audio → transcribe → smart summary + key points |
| 🧠 Flashcards | Paste text → generate definition / fill-blank / example cards + mini-game |
| 📝 Quiz | Paste text → MCQ / True-False / Fill-blank / Matching quiz |
| 📊 Exam Analysis | Load CSV → topic frequency + marks distribution charts |
| 📑 Study Report | Generate HTML report with exam stats |
| 🏆 Progress | XP, streaks, badges, achievements, study recommendations |

---

## Quick Start

### 1. Prerequisites

- Python 3.10 or later — [python.org](https://www.python.org/downloads/)
- `ffmpeg` must be available (bundled via `imageio-ffmpeg` — no manual install needed for most setups)

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
# Copy the example file
cp .env.example .env
```

Open `.env` and fill in your values:

```
HUGGINGFACE_TOKEN=hf_your_token_here   # optional
```

> **Note:** A HuggingFace token is only needed if you want to access gated HuggingFace models. The core features (STT, NLP, quiz, exam analysis) work without it.

### 5. Add exam CSV datasets (for Exam Analysis & Reports)

Place CSV files in `data/kaggle_papers/` with these exact names:

| File | Exam |
|------|------|
| `board.csv` | Board exams |
| `neet.csv` | NEET |
| `jee.csv` | JEE |
| `gate.csv` | GATE |

Expected CSV columns: `question`, `topic`, `subject`, `marks`, `year`

### 6. Run the app

```bash
streamlit run app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Project Structure

```
ai_study_assistant/
├── app.py                    # Main Streamlit app
├── modules/
│   ├── nlp.py                # Text summarization, keywords, flashcards
│   ├── quiz.py               # Quiz generation and scoring
│   ├── stt.py                # Audio transcription (Google STT)
│   ├── gamify.py             # XP, streaks, spaced repetition
│   ├── exam_preprocess.py    # CSV loading and cleaning
│   ├── exam_analysis.py      # Topic frequency, marks distribution
│   ├── report.py             # Jinja2 HTML report generation
│   └── utils.py              # Directory setup, file saving, CSS loader
├── templates/
│   └── report_template.html  # HTML report template
├── assets/
│   └── styles.css            # Custom Streamlit styles
├── data/
│   ├── kaggle_papers/        # Exam CSV files (board, neet, jee, gate)
│   └── user_uploads/         # Uploaded audio files
├── requirements.txt
├── .env.example
└── README.md
```

---

## Supported Audio Formats

- `.mp3`, `.wav`, `.m4a`

Audio is split into configurable chunks (30–120 s) and sent to Google's free Speech-to-Text API. An internet connection is required for transcription.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Dataset not found` warning in Exam Analysis | Add the matching CSV to `data/kaggle_papers/` |
| `[Error] Could not read audio file` | Make sure ffmpeg is accessible; reinstall `imageio-ffmpeg` |
| Transcription returns empty text | Check internet connection; try a different language code |
| `TemplateNotFound` on report generation | Ensure `templates/report_template.html` exists |
