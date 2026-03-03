"""Umami Analytics API client for portal engagement data.

Uses UMAMI_API_URL and UMAMI_API_TOKEN environment variables.
All responses are cached for 1 hour via @st.cache_data.

API Reference:
- GET /api/websites/:id/stats → pageviews, visitors, visits, bounces, totaltime
- GET /api/websites/:id/pageviews → time series by unit (hour/day/week)
- GET /api/websites/:id/metrics → aggregations by type (path, referrer, browser, etc.)
- GET /api/websites/:id/events/series → custom events over time
- GET /api/websites/:id/active → active visitors (last 5 min)
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import requests


def _get_config() -> tuple[str, str, str]:
    """Return (base_url, website_id, token)."""
    base_url = os.environ.get("UMAMI_API_URL", "")
    website_id = os.environ.get("UMAMI_WEBSITE_ID", "")
    token = os.environ.get("UMAMI_API_TOKEN", "")
    return base_url, website_id, token


def _is_configured() -> bool:
    base_url, website_id, token = _get_config()
    return bool(base_url and website_id and token)


def _request(endpoint: str, params: dict | None = None) -> dict | list | None:
    base_url, website_id, token = _get_config()
    if not all([base_url, website_id, token]):
        return None
    url = f"{base_url.rstrip('/')}/api/websites/{website_id}/{endpoint}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    try:
        resp = requests.get(url, headers=headers, params=params or {}, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


def _date_range(days: int) -> dict:
    """Return startAt/endAt params in milliseconds for Umami API."""
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    return {
        "startAt": int(start.timestamp() * 1000),
        "endAt": int(end.timestamp() * 1000),
    }


# =========================================================================
# Stats — overview KPIs
# =========================================================================


@st.cache_data(ttl=3600)
def get_stats(days: int = 30) -> dict:
    """Overall stats: pageviews, visitors, visits, bounces, totaltime."""
    data = _request("stats", _date_range(days))
    return data if isinstance(data, dict) else {}


@st.cache_data(ttl=3600)
def get_stats_comparison(days: int = 30) -> tuple[dict, dict]:
    """Current period stats and previous period stats for delta comparison."""
    current = get_stats(days)

    end = datetime.utcnow() - timedelta(days=days)
    start = end - timedelta(days=days)
    prev_params = {
        "startAt": int(start.timestamp() * 1000),
        "endAt": int(end.timestamp() * 1000),
    }
    prev = _request("stats", prev_params)
    prev = prev if isinstance(prev, dict) else {}
    return current, prev


# =========================================================================
# Pageviews — time series
# =========================================================================


@st.cache_data(ttl=3600)
def get_pageviews_series(days: int = 30, unit: str = "day") -> pd.DataFrame:
    """Pageviews and sessions time series."""
    params = {**_date_range(days), "unit": unit}
    data = _request("pageviews", params)
    if not data:
        return pd.DataFrame()
    pageviews = data.get("pageviews", [])
    sessions = data.get("sessions", [])

    rows = []
    for pv, sess in zip(pageviews, sessions):
        rows.append({
            "date": pv.get("x") or pv.get("date"),
            "pageviews": pv.get("y", 0),
            "sessions": sess.get("y", 0),
        })
    return pd.DataFrame(rows)


# =========================================================================
# Metrics — aggregations by dimension
# =========================================================================


@st.cache_data(ttl=3600)
def get_metrics(metric_type: str, days: int = 30, limit: int = 20) -> pd.DataFrame:
    """Aggregated metrics by type: url, referrer, browser, os, device, country.

    Returns DataFrame with columns: name, visitors, (and possibly pageviews, bounces, etc.)
    """
    params = {**_date_range(days), "type": metric_type, "limit": limit}
    data = _request("metrics", params)
    if not data or not isinstance(data, list):
        return pd.DataFrame()
    return pd.DataFrame(data)


# =========================================================================
# Events — custom events (article_click, search, filter_changed)
# =========================================================================


@st.cache_data(ttl=3600)
def get_events_series(event_name: str, days: int = 30, unit: str = "day") -> pd.DataFrame:
    """Time series for a specific custom event."""
    params = {
        **_date_range(days),
        "unit": unit,
        "eventName": event_name,
    }
    data = _request("events/series", params)
    if not data or not isinstance(data, list):
        return pd.DataFrame()

    rows = []
    for item in data:
        rows.append({
            "date": item.get("x") or item.get("date"),
            "count": item.get("y", 0),
        })
    return pd.DataFrame(rows)


# =========================================================================
# Active visitors
# =========================================================================


@st.cache_data(ttl=60)
def get_active_visitors() -> int:
    """Active visitors in the last 5 minutes."""
    data = _request("active")
    if isinstance(data, dict):
        return data.get("x", 0)
    if isinstance(data, (int, float)):
        return int(data)
    return 0


# =========================================================================
# Top pages (for cross-referencing with BigQuery article data)
# =========================================================================


@st.cache_data(ttl=3600)
def get_top_pages(days: int = 30, limit: int = 50) -> pd.DataFrame:
    """Top pages by visitors. Can be cross-referenced with article data."""
    return get_metrics("url", days, limit)


@st.cache_data(ttl=3600)
def get_search_events(days: int = 30) -> pd.DataFrame:
    """Search event time series."""
    return get_events_series("search", days)
