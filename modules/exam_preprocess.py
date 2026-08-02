import pandas as pd
from typing import Union


def load_and_clean(path: Union[str, bytes]) -> pd.DataFrame:
    """
    Load exam dataset from CSV and clean columns.
    Ensures consistent types for marks, year, subject, question, topic.
    """
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]

    # Use safe column access: check existence before filling
    if "marks" not in df.columns:
        df["marks"] = 0
    df["marks"] = pd.to_numeric(df["marks"], errors="coerce").fillna(0).astype(int)

    if "year" not in df.columns:
        df["year"] = 0
    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)

    if "subject" not in df.columns:
        df["subject"] = "Unknown"
    df["subject"] = df["subject"].fillna("Unknown").astype(str)

    if "question" not in df.columns:
        df["question"] = ""
    df["question"] = df["question"].fillna("").astype(str)

    if "topic" not in df.columns:
        df["topic"] = "Misc"
    df["topic"] = df["topic"].fillna("Misc").astype(str)

    # Normalize text formatting
    df["topic"] = df["topic"].str.strip().str.title()
    df["subject"] = df["subject"].str.strip().str.title()

    # Drop invalid rows (empty questions/topics)
    df = df[df["question"].str.len() > 5]
    df = df[df["topic"].str.len() > 2]

    return df.reset_index(drop=True)
