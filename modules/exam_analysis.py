import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def topic_frequency(df: pd.DataFrame) -> pd.DataFrame:
    """Count frequency of topics in dataset."""
    if df.empty or "topic" not in df.columns:
        return pd.DataFrame(columns=["topic", "count"])
    freq = df["topic"].value_counts(dropna=False).reset_index()
    freq.columns = ["topic", "count"]
    return freq.sort_values("count", ascending=False)


def marks_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Distribution of marks across questions."""
    if df.empty or "marks" not in df.columns:
        return pd.DataFrame(columns=["marks", "count"])
    return df.groupby("marks", dropna=False).size().reset_index(name="count")


def subject_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Count questions per subject."""
    if df.empty or "subject" not in df.columns:
        return pd.DataFrame(columns=["subject", "count"])
    freq = df["subject"].value_counts(dropna=False).reset_index()
    freq.columns = ["subject", "count"]
    return freq.sort_values("count", ascending=False)


def year_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Count questions per year."""
    if df.empty or "year" not in df.columns:
        return pd.DataFrame(columns=["year", "count"])
    t = df[df["year"] > 0].groupby("year").size().reset_index(name="count")
    return t.sort_values("year")


def topic_year_heatmap(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Return pivot: rows=topic, cols=year, values=count (top-n topics)."""
    if df.empty or "topic" not in df.columns or "year" not in df.columns:
        return pd.DataFrame()
    top_topics = topic_frequency(df).head(top_n)["topic"].tolist()
    sub = df[df["topic"].isin(top_topics) & (df["year"] > 0)]
    if sub.empty:
        return pd.DataFrame()
    pivot = sub.groupby(["topic", "year"]).size().unstack(fill_value=0)
    return pivot


def important_questions(df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """Identify important questions by frequency × marks × recency."""
    if df.empty or "question" not in df.columns:
        return pd.DataFrame(columns=["norm_q", "frequency", "avg_marks", "latest_year", "score"])

    df = df.copy()
    df["norm_q"] = df["question"].str.lower().str.strip()

    imp = df.groupby("norm_q").agg(
        frequency=("question", "count"),
        avg_marks=("marks", "mean"),
        latest_year=("year", "max")
    ).reset_index()

    year_span = max(1, df["year"].max() - df["year"].min())
    imp["score"] = imp["frequency"] * (1 + imp["avg_marks"] / 10) * (
        1 + (imp["latest_year"] - df["year"].min()) / year_span
    )
    imp["avg_marks"] = imp["avg_marks"].round(1)
    imp["score"] = imp["score"].round(2)

    return imp.sort_values("score", ascending=False).head(top_n)


# ── Plotly Charts ───────────────────────────────────────────

_PALETTE = px.colors.qualitative.Bold


def plot_topic_frequency(freq_df: pd.DataFrame, top_n: int = 20):
    """Horizontal bar chart of topic frequency."""
    if freq_df.empty:
        return px.bar(title="No topic data available")
    data = freq_df.head(top_n).sort_values("count")
    fig = px.bar(
        data, y="topic", x="count", orientation="h",
        title=f"Top {min(top_n, len(data))} Topics by Frequency",
        color="count",
        color_continuous_scale="Blues",
        text="count",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        xaxis_title="Number of Questions",
        yaxis_title="",
        coloraxis_showscale=False,
        template="plotly_white",
        height=max(350, len(data) * 28),
        margin=dict(l=10, r=30, t=50, b=30),
        font=dict(family="Inter, sans-serif", size=12),
    )
    return fig


def plot_marks_distribution(marks_df: pd.DataFrame):
    """Donut chart of marks distribution."""
    if marks_df.empty:
        return px.pie(title="No marks data available")
    fig = px.pie(
        marks_df, names="marks", values="count",
        title="Marks Distribution",
        hole=0.45,
        color_discrete_sequence=_PALETTE,
    )
    fig.update_traces(textinfo="value+percent", pull=[0.03] * len(marks_df))
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Inter, sans-serif", size=12),
        margin=dict(t=50, b=20),
    )
    return fig


def plot_subject_distribution(subject_df: pd.DataFrame):
    """Bar chart of subject distribution."""
    if subject_df.empty:
        return px.bar(title="No subject data available")
    fig = px.bar(
        subject_df, x="subject", y="count",
        title="Questions per Subject",
        color="subject",
        color_discrete_sequence=_PALETTE,
        text="count",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        xaxis_title="Subject",
        yaxis_title="Count",
        showlegend=False,
        template="plotly_white",
        font=dict(family="Inter, sans-serif", size=12),
        margin=dict(t=50, b=30),
    )
    return fig


def plot_year_trend(trend_df: pd.DataFrame):
    """Line + area chart of question count per year."""
    if trend_df.empty:
        return px.line(title="No year data available")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trend_df["year"], y=trend_df["count"],
        mode="lines+markers",
        fill="tozeroy",
        line=dict(color="#4f46e5", width=2.5),
        marker=dict(size=7, color="#4f46e5"),
        fillcolor="rgba(79,70,229,0.12)",
        name="Questions",
    ))
    fig.update_layout(
        title="Year-wise Question Trend",
        xaxis_title="Year",
        yaxis_title="Number of Questions",
        template="plotly_white",
        font=dict(family="Inter, sans-serif", size=12),
        margin=dict(t=50, b=30),
        hovermode="x unified",
    )
    return fig


def plot_topic_heatmap(pivot_df: pd.DataFrame):
    """Heatmap of topic × year question counts."""
    if pivot_df.empty:
        return go.Figure().update_layout(title="No heatmap data available")
    fig = px.imshow(
        pivot_df,
        title="Topic × Year Heatmap (Top Topics)",
        color_continuous_scale="Blues",
        aspect="auto",
        text_auto=True,
    )
    fig.update_layout(
        xaxis_title="Year",
        yaxis_title="Topic",
        template="plotly_white",
        font=dict(family="Inter, sans-serif", size=11),
        margin=dict(t=60, b=30),
        coloraxis_showscale=False,
    )
    return fig
