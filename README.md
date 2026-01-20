# AI Study Assistant (India)

Convert lectures to notes, flashcards, quizzes, and analyze 5-year past papers (Board, NEET, JEE, GATE). Built with Streamlit, Hugging Face.

## Quick Start
1. Install Python 3.12 from [python.org](https://www.python.org/downloads/).
2. Create virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate   # Windows

## Install Dependencies
pip install -r requirements.txt

## Set up environment variables:
Copy .env.example to .env.
Open .env and add your API keys (e.g., HUGGINGFACE_TOKEN=your_token).

## Run the app:
streamlit run app.py