"""PostgreSQL queries for entities, trending, features and embeddings.

Uses DATABASE_URL environment variable for connection.
Queries target the news_features table (JSONB features column)
and news.content_embedding (pgvector 768-dim).
"""

from __future__ import annotations

import os
from typing import Optional

import streamlit as st
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text


@st.cache_resource
def get_engine():
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return None
    return create_engine(url, pool_size=3, max_overflow=2, pool_pre_ping=True)


def _query(sql: str, params: dict | None = None) -> pd.DataFrame:
    engine = get_engine()
    if engine is None:
        return pd.DataFrame()
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


# =========================================================================
# Entities — from news_features.features->'entities'
# =========================================================================


@st.cache_data(ttl=3600)
def get_top_entities(entity_type: str = "ORG", days: int = 90, top_n: int = 20) -> pd.DataFrame:
    """Top entities of a given type by total mention count."""
    sql = """
    WITH entities AS (
        SELECT
            nf.unique_id,
            n.published_at,
            e->>'text' AS entity_name,
            e->>'type' AS entity_type,
            (e->>'count')::int AS mention_count
        FROM news_features nf
        JOIN news n ON n.unique_id = nf.unique_id
        CROSS JOIN LATERAL jsonb_array_elements(nf.features->'entities') AS e
        WHERE n.published_at >= NOW() - INTERVAL :days_interval
          AND e->>'type' = :entity_type
    )
    SELECT
        entity_name,
        SUM(mention_count) AS total_mentions,
        COUNT(DISTINCT unique_id) AS article_count
    FROM entities
    GROUP BY entity_name
    ORDER BY total_mentions DESC
    LIMIT :top_n
    """
    return _query(sql, {
        "days_interval": f"{days} days",
        "entity_type": entity_type,
        "top_n": top_n,
    })


@st.cache_data(ttl=3600)
def get_entity_timeline(entity_names: list[str], days: int = 90) -> pd.DataFrame:
    """Weekly mention count for selected entities."""
    if not entity_names:
        return pd.DataFrame()
    sql = """
    WITH entities AS (
        SELECT
            n.published_at,
            e->>'text' AS entity_name,
            (e->>'count')::int AS mention_count
        FROM news_features nf
        JOIN news n ON n.unique_id = nf.unique_id
        CROSS JOIN LATERAL jsonb_array_elements(nf.features->'entities') AS e
        WHERE n.published_at >= NOW() - INTERVAL :days_interval
          AND e->>'text' = ANY(:entity_names)
    )
    SELECT
        date_trunc('week', published_at)::date AS week,
        entity_name,
        SUM(mention_count) AS mentions
    FROM entities
    GROUP BY week, entity_name
    ORDER BY week
    """
    return _query(sql, {
        "days_interval": f"{days} days",
        "entity_names": entity_names,
    })


@st.cache_data(ttl=3600)
def get_entity_cooccurrence(days: int = 90, min_cooccurrences: int = 3, top_n: int = 50) -> pd.DataFrame:
    """Entity co-occurrence pairs (appear in the same article).

    Returns edges for a network graph with source, target, and weight.
    Limited to top entities to keep the graph manageable.
    """
    sql = """
    WITH top_entities AS (
        SELECT
            e->>'text' AS entity_name,
            SUM((e->>'count')::int) AS total_mentions
        FROM news_features nf
        JOIN news n ON n.unique_id = nf.unique_id
        CROSS JOIN LATERAL jsonb_array_elements(nf.features->'entities') AS e
        WHERE n.published_at >= NOW() - INTERVAL :days_interval
        GROUP BY entity_name
        ORDER BY total_mentions DESC
        LIMIT :top_n
    ),
    article_entities AS (
        SELECT
            nf.unique_id,
            e->>'text' AS entity_name,
            e->>'type' AS entity_type
        FROM news_features nf
        JOIN news n ON n.unique_id = nf.unique_id
        CROSS JOIN LATERAL jsonb_array_elements(nf.features->'entities') AS e
        WHERE n.published_at >= NOW() - INTERVAL :days_interval
          AND e->>'text' IN (SELECT entity_name FROM top_entities)
    )
    SELECT
        a.entity_name AS source,
        a.entity_type AS source_type,
        b.entity_name AS target,
        b.entity_type AS target_type,
        COUNT(DISTINCT a.unique_id) AS weight
    FROM article_entities a
    JOIN article_entities b ON a.unique_id = b.unique_id AND a.entity_name < b.entity_name
    GROUP BY a.entity_name, a.entity_type, b.entity_name, b.entity_type
    HAVING COUNT(DISTINCT a.unique_id) >= :min_cooccurrences
    ORDER BY weight DESC
    """
    return _query(sql, {
        "days_interval": f"{days} days",
        "min_cooccurrences": min_cooccurrences,
        "top_n": top_n,
    })


@st.cache_data(ttl=3600)
def get_entity_nodes(days: int = 90, top_n: int = 50) -> pd.DataFrame:
    """Top entities with type and frequency, for network graph nodes."""
    sql = """
    SELECT
        e->>'text' AS entity_name,
        e->>'type' AS entity_type,
        SUM((e->>'count')::int) AS total_mentions,
        COUNT(DISTINCT nf.unique_id) AS article_count
    FROM news_features nf
    JOIN news n ON n.unique_id = nf.unique_id
    CROSS JOIN LATERAL jsonb_array_elements(nf.features->'entities') AS e
    WHERE n.published_at >= NOW() - INTERVAL :days_interval
    GROUP BY entity_name, entity_type
    ORDER BY total_mentions DESC
    LIMIT :top_n
    """
    return _query(sql, {
        "days_interval": f"{days} days",
        "top_n": top_n,
    })


# =========================================================================
# Embeddings — from news.content_embedding (pgvector 768-dim)
# =========================================================================


@st.cache_data(ttl=3600)
def get_embeddings_sample(days: int = 90, sample_size: int = 5000) -> tuple[np.ndarray, pd.DataFrame]:
    """Sample of article embeddings with metadata for UMAP projection.

    Returns:
        embeddings: numpy array of shape (n, 768)
        metadata: DataFrame with unique_id, title, agency_name, theme_l1, published_at
    """
    sql = """
    SELECT
        n.unique_id,
        n.title,
        n.agency_name,
        COALESCE(t.label, 'Sem tema') AS theme_l1,
        n.published_at,
        n.content_embedding::text AS embedding_text
    FROM news n
    LEFT JOIN themes t ON t.id = n.theme_l1_id
    WHERE n.content_embedding IS NOT NULL
      AND n.published_at >= NOW() - INTERVAL :days_interval
    ORDER BY RANDOM()
    LIMIT :sample_size
    """
    df = _query(sql, {
        "days_interval": f"{days} days",
        "sample_size": sample_size,
    })
    if df.empty:
        return np.array([]), pd.DataFrame()

    # Parse pgvector text format "[0.1,0.2,...]" → numpy array
    embeddings = np.array([
        np.fromstring(s.strip("[]"), sep=",")
        for s in df["embedding_text"]
    ])
    metadata = df.drop(columns=["embedding_text"])
    return embeddings, metadata


@st.cache_data(ttl=3600)
def get_similarity_clusters(days: int = 90, min_similar: int = 5, limit: int = 20) -> pd.DataFrame:
    """Articles with the most similar articles (highest cluster density).

    Identifies events with coordinated coverage across agencies.
    """
    sql = """
    SELECT
        n.unique_id,
        n.title,
        n.agency_name,
        COALESCE(t.label, 'Sem tema') AS theme_l1,
        n.published_at,
        jsonb_array_length(nf.features->'similar_articles') AS similar_count
    FROM news_features nf
    JOIN news n ON n.unique_id = nf.unique_id
    LEFT JOIN themes t ON t.id = n.theme_l1_id
    WHERE nf.features ? 'similar_articles'
      AND jsonb_array_length(nf.features->'similar_articles') >= :min_similar
      AND n.published_at >= NOW() - INTERVAL :days_interval
    ORDER BY similar_count DESC
    LIMIT :limit
    """
    return _query(sql, {
        "days_interval": f"{days} days",
        "min_similar": min_similar,
        "limit": limit,
    })
