"""BigQuery queries for Panorama Gov.BR dashboard.

Uses Application Default Credentials from Cloud Run service account.
All queries target the dgb_gold dataset (Medallion gold layer).
"""

import streamlit as st
import pandas as pd
from google.cloud import bigquery

PROJECT_ID = "inspire-7-finep"
DATASET = "dgb_gold"


@st.cache_resource
def get_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID)


def _query(sql: str) -> pd.DataFrame:
    return get_client().query(sql).to_dataframe()


# =========================================================================
# KPIs
# =========================================================================


@st.cache_data(ttl=3600)
def get_kpis(days: int = 30) -> dict:
    """Main KPIs for the overview page."""
    sql = f"""
    WITH current_period AS (
        SELECT
            COUNT(*) AS total_articles,
            COUNT(DISTINCT agency_key) AS active_agencies,
            COUNT(DISTINCT theme_l1_code) AS themes_covered,
            AVG(sentiment_score) AS avg_sentiment
        FROM `{PROJECT_ID}.{DATASET}.fato_noticias`
        WHERE published_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
    ),
    previous_period AS (
        SELECT
            COUNT(*) AS total_articles,
            COUNT(DISTINCT agency_key) AS active_agencies,
            COUNT(DISTINCT theme_l1_code) AS themes_covered,
            AVG(sentiment_score) AS avg_sentiment
        FROM `{PROJECT_ID}.{DATASET}.fato_noticias`
        WHERE published_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days * 2} DAY)
          AND published_at < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
    )
    SELECT
        c.total_articles,
        c.active_agencies,
        c.themes_covered,
        c.avg_sentiment,
        p.total_articles AS prev_total_articles,
        p.active_agencies AS prev_active_agencies,
        p.themes_covered AS prev_themes_covered,
        p.avg_sentiment AS prev_avg_sentiment
    FROM current_period c, previous_period p
    """
    df = _query(sql)
    if df.empty:
        return {}
    row = df.iloc[0]
    return row.to_dict()


# =========================================================================
# Treemap / Sunburst — Themes hierarchy
# =========================================================================


@st.cache_data(ttl=3600)
def get_theme_hierarchy(days: int = 30) -> pd.DataFrame:
    """Theme hierarchy with volume and sentiment for treemap/sunburst."""
    sql = f"""
    SELECT
        COALESCE(theme_l1_label, 'Sem tema') AS theme_l1,
        COALESCE(theme_l2_label, 'Outros') AS theme_l2,
        COALESCE(most_specific_theme_label, 'Outros') AS theme_l3,
        COUNT(*) AS article_count,
        AVG(sentiment_score) AS avg_sentiment
    FROM `{PROJECT_ID}.{DATASET}.fato_noticias`
    WHERE published_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
    GROUP BY theme_l1, theme_l2, theme_l3
    ORDER BY article_count DESC
    """
    return _query(sql)


# =========================================================================
# Timeline — Volume over time
# =========================================================================


@st.cache_data(ttl=3600)
def get_volume_timeline(days: int = 90, granularity: str = "day") -> pd.DataFrame:
    """Article volume over time, optionally grouped by theme L1."""
    trunc = {"day": "DAY", "week": "WEEK", "month": "MONTH"}[granularity]
    sql = f"""
    SELECT
        TIMESTAMP_TRUNC(published_at, {trunc}) AS period,
        COALESCE(theme_l1_label, 'Sem tema') AS theme_l1,
        COUNT(*) AS article_count
    FROM `{PROJECT_ID}.{DATASET}.fato_noticias`
    WHERE published_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
    GROUP BY period, theme_l1
    ORDER BY period
    """
    return _query(sql)


# =========================================================================
# Trending — Themes with highest growth
# =========================================================================


@st.cache_data(ttl=3600)
def get_trending_themes(top_n: int = 10) -> pd.DataFrame:
    """Themes with highest growth rate (last 7 days vs previous 7 days)."""
    sql = f"""
    WITH recent AS (
        SELECT
            COALESCE(theme_l1_label, 'Sem tema') AS theme,
            COUNT(*) AS recent_count
        FROM `{PROJECT_ID}.{DATASET}.fato_noticias`
        WHERE published_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
        GROUP BY theme
    ),
    previous AS (
        SELECT
            COALESCE(theme_l1_label, 'Sem tema') AS theme,
            COUNT(*) AS prev_count
        FROM `{PROJECT_ID}.{DATASET}.fato_noticias`
        WHERE published_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 14 DAY)
          AND published_at < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
        GROUP BY theme
    )
    SELECT
        r.theme,
        r.recent_count,
        COALESCE(p.prev_count, 0) AS prev_count,
        CASE
            WHEN COALESCE(p.prev_count, 0) = 0 THEN 100.0
            ELSE ROUND((r.recent_count - p.prev_count) * 100.0 / p.prev_count, 1)
        END AS growth_pct
    FROM recent r
    LEFT JOIN previous p ON r.theme = p.theme
    WHERE r.recent_count >= 5
    ORDER BY growth_pct DESC
    LIMIT {top_n}
    """
    return _query(sql)


# =========================================================================
# Agencies
# =========================================================================


@st.cache_data(ttl=3600)
def get_agencies() -> pd.DataFrame:
    """All agencies with metadata."""
    sql = f"""
    SELECT agency_key, agency_name, agency_type, parent_key
    FROM `{PROJECT_ID}.{DATASET}.dim_agencias`
    ORDER BY agency_name
    """
    return _query(sql)


@st.cache_data(ttl=3600)
def get_agency_stats(agency_key: str, days: int = 30) -> pd.DataFrame:
    """Statistics for a single agency."""
    sql = f"""
    SELECT
        COUNT(*) AS total_articles,
        AVG(sentiment_score) AS avg_sentiment,
        AVG(word_count) AS avg_word_count,
        AVG(readability_flesch) AS avg_readability,
        COUNTIF(has_image) / COUNT(*) AS image_rate,
        COUNTIF(has_video) / COUNT(*) AS video_rate
    FROM `{PROJECT_ID}.{DATASET}.fato_noticias`
    WHERE agency_key = @agency_key
      AND published_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("agency_key", "STRING", agency_key)
        ]
    )
    return get_client().query(sql, job_config=job_config).to_dataframe()


@st.cache_data(ttl=3600)
def get_agency_heatmap(agency_key: str, days: int = 90) -> pd.DataFrame:
    """Publication hour x day-of-week heatmap for an agency."""
    sql = f"""
    SELECT
        publication_dow AS dow,
        publication_hour AS hour,
        COUNT(*) AS article_count
    FROM `{PROJECT_ID}.{DATASET}.fato_noticias`
    WHERE agency_key = @agency_key
      AND published_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
    GROUP BY dow, hour
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("agency_key", "STRING", agency_key)
        ]
    )
    return get_client().query(sql, job_config=job_config).to_dataframe()


@st.cache_data(ttl=3600)
def get_agency_sentiment(agency_key: str, days: int = 90) -> pd.DataFrame:
    """Sentiment distribution for an agency."""
    sql = f"""
    SELECT
        sentiment_label,
        COUNT(*) AS count
    FROM `{PROJECT_ID}.{DATASET}.fato_noticias`
    WHERE agency_key = @agency_key
      AND published_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
      AND sentiment_label IS NOT NULL
    GROUP BY sentiment_label
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("agency_key", "STRING", agency_key)
        ]
    )
    return get_client().query(sql, job_config=job_config).to_dataframe()


@st.cache_data(ttl=3600)
def get_agency_themes(agency_key: str, days: int = 90) -> pd.DataFrame:
    """Theme coverage for an agency."""
    sql = f"""
    SELECT
        COALESCE(theme_l1_label, 'Sem tema') AS theme,
        COUNT(*) AS article_count
    FROM `{PROJECT_ID}.{DATASET}.fato_noticias`
    WHERE agency_key = @agency_key
      AND published_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
    GROUP BY theme
    ORDER BY article_count DESC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("agency_key", "STRING", agency_key)
        ]
    )
    return get_client().query(sql, job_config=job_config).to_dataframe()


@st.cache_data(ttl=3600)
def get_benchmarking(agency_type: str, days: int = 30, top_n: int = 15) -> pd.DataFrame:
    """Benchmarking: top agencies of the same type."""
    sql = f"""
    SELECT
        f.agency_key,
        f.agency_name,
        COUNT(*) AS total_articles,
        AVG(f.sentiment_score) AS avg_sentiment,
        AVG(f.readability_flesch) AS avg_readability,
        COUNTIF(f.has_image) / COUNT(*) AS image_rate
    FROM `{PROJECT_ID}.{DATASET}.fato_noticias` f
    JOIN `{PROJECT_ID}.{DATASET}.dim_agencias` a ON f.agency_key = a.agency_key
    WHERE a.agency_type = @agency_type
      AND f.published_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
    GROUP BY f.agency_key, f.agency_name
    ORDER BY total_articles DESC
    LIMIT {top_n}
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("agency_type", "STRING", agency_type)
        ]
    )
    return get_client().query(sql, job_config=job_config).to_dataframe()


# =========================================================================
# Themes page
# =========================================================================


@st.cache_data(ttl=3600)
def get_agency_theme_matrix(days: int = 30) -> pd.DataFrame:
    """Agency x Theme L1 matrix for heatmap."""
    sql = f"""
    SELECT
        agency_name,
        COALESCE(theme_l1_label, 'Sem tema') AS theme_l1,
        COUNT(*) AS article_count
    FROM `{PROJECT_ID}.{DATASET}.fato_noticias`
    WHERE published_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
    GROUP BY agency_name, theme_l1
    HAVING article_count >= 3
    ORDER BY article_count DESC
    """
    return _query(sql)


# =========================================================================
# Quality page
# =========================================================================


@st.cache_data(ttl=3600)
def get_quality_by_agency_type(days: int = 90) -> pd.DataFrame:
    """Readability and quality metrics by agency type."""
    sql = f"""
    SELECT
        a.agency_type,
        f.readability_flesch,
        f.word_count,
        f.has_image,
        f.has_video,
        f.sentiment_score
    FROM `{PROJECT_ID}.{DATASET}.fato_noticias` f
    JOIN `{PROJECT_ID}.{DATASET}.dim_agencias` a ON f.agency_key = a.agency_key
    WHERE f.published_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
      AND f.readability_flesch IS NOT NULL
    """
    return _query(sql)


@st.cache_data(ttl=3600)
def get_agency_quality_scatter(days: int = 90) -> pd.DataFrame:
    """Readability vs volume per agency for scatter plot."""
    sql = f"""
    SELECT
        f.agency_name,
        a.agency_type,
        COUNT(*) AS article_count,
        AVG(f.readability_flesch) AS avg_readability,
        AVG(f.sentiment_score) AS avg_sentiment,
        COUNTIF(f.has_image) / COUNT(*) AS image_rate
    FROM `{PROJECT_ID}.{DATASET}.fato_noticias` f
    JOIN `{PROJECT_ID}.{DATASET}.dim_agencias` a ON f.agency_key = a.agency_key
    WHERE f.published_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
      AND f.readability_flesch IS NOT NULL
    GROUP BY f.agency_name, a.agency_type
    HAVING article_count >= 5
    """
    return _query(sql)
