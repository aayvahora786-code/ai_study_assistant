import pandas as pd
from typing import Union

def load_and_clean(path: Union[str, bytes]) -> pd.DataFrame:
    """
    Load exam dataset from CSV and clean columns.
    Ensures consistent types for marks, year, subject, question, topic.
    """
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]

    df["marks"] = pd.to_numeric(df.get("marks", 0), errors="coerce").fillna(0).astype(int)
    df["year"] = pd.to_numeric(df.get("year", 0), errors="coerce").fillna(0).astype(int)
    df["subject"] = df.get("subject", "Unknown").fillna("Unknown").astype(str)
    df["question"] = df.get("question", "").fillna("").astype(str)
    df["topic"] = df.get("topic", "Misc").fillna("Misc").astype(str)

    # Normalize text formatting
    df["topic"] = df["topic"].str.strip().str.title()
    df["subject"] = df["subject"].str.strip().str.title()

    # Drop invalid rows (empty questions/topics)
    df = df[df["question"].str.len() > 5]
    df = df[df["topic"].str.len() > 2]

    return df