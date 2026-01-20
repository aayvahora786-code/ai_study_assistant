import os
import streamlit as st

def ensure_dirs():
    """
    Ensure required directories exist for uploads and datasets.
    """
    os.makedirs("data/kaggle_papers", exist_ok=True)
    os.makedirs("data/user_uploads", exist_ok=True)

def save_uploaded_file(uploaded_file, folder="data/user_uploads"):
    """
    Save uploaded file to a folder and return its path.
    """
    path = os.path.join(folder, uploaded_file.name)
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path

def load_css():
    """
    Load custom CSS from assets/styles.css into Streamlit app.
    """
    try:
        with open("assets/styles.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("⚠️ styles.css not found in assets/ folder.")