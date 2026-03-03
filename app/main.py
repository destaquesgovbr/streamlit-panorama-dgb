"""Panorama Gov.BR — Visão Geral

Dashboard analítico da comunicação governamental brasileira.
"""

import streamlit as st
import plotly.express as px

from data.bigquery import get_kpis, get_theme_hierarchy, get_volume_timeline, get_trending_themes
from utils import COLORS, METRIC_HELP, WIDGET_HELP, fmt_number

st.set_page_config(
    page_title="Panorama Gov.BR",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Panorama Gov.BR")
st.caption("Visão geral da comunicação governamental brasileira — volume, temas e sentimento")

# -------------------------------------------------------------------------
# Sidebar — Period selector
# -------------------------------------------------------------------------

days = st.sidebar.selectbox(
    "Período",
    options=[7, 30, 90, 180, 365],
    index=1,
    format_func=lambda d: {7: "7 dias", 30: "30 dias", 90: "3 meses", 180: "6 meses", 365: "1 ano"}[d],
    help=WIDGET_HELP["periodo_home"],
)

# -------------------------------------------------------------------------
# KPIs
# -------------------------------------------------------------------------

kpis = get_kpis(days)

if kpis:
    cols = st.columns(4)
    cols[0].metric(
        "Artigos publicados",
        fmt_number(kpis["total_articles"]),
        delta=f"{kpis['total_articles'] - kpis['prev_total_articles']:+,}".replace(",", "."),
        help=METRIC_HELP["artigos_publicados"],
    )
    cols[1].metric(
        "Agências ativas",
        fmt_number(kpis["active_agencies"]),
        delta=int(kpis["active_agencies"] - kpis["prev_active_agencies"]),
        help=METRIC_HELP["agencias_ativas"],
    )
    cols[2].metric(
        "Temas cobertos",
        fmt_number(kpis["themes_covered"]),
        delta=int(kpis["themes_covered"] - kpis["prev_themes_covered"]),
        help=METRIC_HELP["temas_cobertos"],
    )
    avg_sent = kpis.get("avg_sentiment") or 0
    prev_sent = kpis.get("prev_avg_sentiment") or 0
    cols[3].metric(
        "Sentimento médio",
        f"{avg_sent:.2f}",
        delta=f"{avg_sent - prev_sent:+.2f}",
        help=METRIC_HELP["sentimento_medio"],
    )

st.divider()

# -------------------------------------------------------------------------
# Treemap — Theme hierarchy
# -------------------------------------------------------------------------

col_tree, col_trending = st.columns([3, 1])

with col_tree:
    st.subheader("Distribuição temática")
    df_themes = get_theme_hierarchy(days)
    if not df_themes.empty:
        fig = px.treemap(
            df_themes,
            path=["theme_l1", "theme_l2"],
            values="article_count",
            color="avg_sentiment",
            color_continuous_scale=["#E52207", "#F0F2F5", "#168821"],
            color_continuous_midpoint=0,
        )
        fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=500)
        st.plotly_chart(fig, use_container_width=True)

# -------------------------------------------------------------------------
# Trending themes
# -------------------------------------------------------------------------

with col_trending:
    st.subheader("Temas em alta")
    df_trending = get_trending_themes()
    if not df_trending.empty:
        for _, row in df_trending.head(8).iterrows():
            delta_str = f"+{row['growth_pct']:.0f}%" if row["growth_pct"] > 0 else f"{row['growth_pct']:.0f}%"
            st.metric(
                row["theme"],
                f"{int(row['recent_count'])} artigos",
                delta=delta_str,
                help=METRIC_HELP["trending_theme"],
            )

st.divider()

# -------------------------------------------------------------------------
# Timeline — Volume over time
# -------------------------------------------------------------------------

st.subheader("Volume de publicações")

granularity = st.radio(
    "Granularidade",
    ["day", "week", "month"],
    format_func=lambda g: {"day": "Dia", "week": "Semana", "month": "Mês"}[g],
    horizontal=True,
    help=WIDGET_HELP["granularidade"],
)

df_timeline = get_volume_timeline(days, granularity)
if not df_timeline.empty:
    # Top 10 themes for stacked area
    top_themes = df_timeline.groupby("theme_l1")["article_count"].sum().nlargest(10).index
    df_plot = df_timeline[df_timeline["theme_l1"].isin(top_themes)]

    fig = px.area(
        df_plot,
        x="period",
        y="article_count",
        color="theme_l1",
        labels={"period": "", "article_count": "Artigos", "theme_l1": "Tema"},
    )
    fig.update_layout(
        margin=dict(t=10, l=10, r=10, b=10),
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3),
    )
    st.plotly_chart(fig, use_container_width=True)
