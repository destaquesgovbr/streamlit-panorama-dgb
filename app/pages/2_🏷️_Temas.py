"""Página 3: Panorama Temático (Gestor Público)"""

import streamlit as st
import plotly.express as px

from data.bigquery import get_theme_hierarchy, get_agency_theme_matrix
from utils import COLORS

st.set_page_config(page_title="Temas — Panorama Gov.BR", page_icon="🏷️", layout="wide")
st.title("🏷️ Panorama Temático")

days = st.sidebar.selectbox("Período", [30, 90, 180, 365], index=1, format_func=lambda d: f"{d} dias")

# -------------------------------------------------------------------------
# Sunburst
# -------------------------------------------------------------------------

st.subheader("Taxonomia da comunicação governamental")
df_themes = get_theme_hierarchy(days)
if not df_themes.empty:
    fig = px.sunburst(
        df_themes,
        path=["theme_l1", "theme_l2"],
        values="article_count",
        color="avg_sentiment",
        color_continuous_scale=["#E52207", "#F0F2F5", "#168821"],
        color_continuous_midpoint=0,
    )
    fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=600)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# -------------------------------------------------------------------------
# Agency x Theme heatmap
# -------------------------------------------------------------------------

st.subheader("Agência × Tema")
df_matrix = get_agency_theme_matrix(days)
if not df_matrix.empty:
    pivot = df_matrix.pivot_table(
        index="agency_name", columns="theme_l1", values="article_count", fill_value=0
    )
    # Keep top 20 agencies by total volume
    top_agencies = pivot.sum(axis=1).nlargest(20).index
    # Keep top 15 themes by total volume
    top_themes = pivot.sum(axis=0).nlargest(15).index
    pivot = pivot.loc[top_agencies, top_themes]

    fig = px.imshow(
        pivot,
        labels=dict(x="Tema", y="Agência", color="Artigos"),
        color_continuous_scale="Blues",
        aspect="auto",
    )
    fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=600)
    st.plotly_chart(fig, use_container_width=True)
