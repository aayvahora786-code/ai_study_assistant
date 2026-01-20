import pandas as pd
import plotly.express as px

def topic_frequency(df: pd.DataFrame) -> pd.DataFrame:
    """
    Count frequency of topics in dataset.
    """
    if df.empty or "topic" not in df.columns:
        return pd.DataFrame(columns=["topic", "count"])
    freq = df["topic"].value_counts(dropna=False).reset_index()
    freq.columns = ["topic", "count"]
    return freq.sort_values("count", ascending=False)

def marks_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    Distribution of marks across questions.
    """
    if df.empty or "marks" not in df.columns:
        return pd.DataFrame(columns=["marks", "count"])
    return df.groupby("marks", dropna=False).size().reset_index(name="count")

def important_questions(df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """
    Identify important questions based on frequency, average marks, and recency.
    """
    if df.empty or "question" not in df.columns:
        return pd.DataFrame(columns=["norm_q","frequency","avg_marks","latest_year","score"])

    df = df.copy()
    df["norm_q"] = df["question"].str.lower().str.strip()

    imp = df.groupby("norm_q").agg(
        frequency=("question", "count"),
        avg_marks=("marks", "mean"),
        latest_year=("year", "max")
    ).reset_index()

    # Weighted score: frequency × marks × recency
    year_span = max(1, df["year"].max() - df["year"].min())
    imp["score"] = imp["frequency"] * (1 + imp["avg_marks"] / 10) * (
        1 + (imp["latest_year"] - df["year"].min()) / year_span
    )

    return imp.sort_values("score", ascending=False).head(top_n)

def plot_topic_frequency(freq_df: pd.DataFrame):
    """
    Bar chart of topic frequency.
    """
    if freq_df.empty:
        return px.bar(title="No topic data available")
    fig = px.bar(
        freq_df, x="topic", y="count",
        title="Topic Frequency (5-year)",
        color="count", color_continuous_scale="Blues"
    )
    fig.update_layout(xaxis_title="Topic", yaxis_title="Count", template="plotly_white")
    return fig

def plot_marks_distribution(marks_df: pd.DataFrame):
    """
    Pie chart of marks distribution.
    """
    if marks_df.empty:
        return px.pie(title="No marks data available")
    fig = px.pie(
        marks_df, names="marks", values="count",
        title="Marks Distribution", hole=0.35
    )
    fig.update_traces(textinfo="value+percent")
    fig.update_layout(template="plotly_white")
    return fig