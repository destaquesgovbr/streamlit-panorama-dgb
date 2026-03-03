"""Página 5: Qualidade da Comunicação (Gestor Público)"""

import streamlit as st
import plotly.express as px

from data.bigquery import get_quality_by_agency_type, get_agency_quality_scatter

st.set_page_config(page_title="Qualidade — Panorama Gov.BR", page_icon="📝", layout="wide")
st.title("📝 Qualidade da Comunicação")

days = st.sidebar.selectbox("Período", [30, 90, 180, 365], index=1, format_func=lambda d: f"{d} dias")

# -------------------------------------------------------------------------
# Readability by agency type
# -------------------------------------------------------------------------

st.subheader("Legibilidade por tipo de agência")
df_quality = get_quality_by_agency_type(days)
if not df_quality.empty:
    fig = px.violin(
        df_quality,
        x="agency_type",
        y="readability_flesch",
        box=True,
        labels={"agency_type": "Tipo de agência", "readability_flesch": "Índice Flesch"},
    )
    fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=400)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# -------------------------------------------------------------------------
# Scatter: readability vs volume
# -------------------------------------------------------------------------

st.subheader("Legibilidade × Volume")
st.caption("Cada ponto é uma agência. Quadrante ideal: alta legibilidade + alto volume.")
df_scatter = get_agency_quality_scatter(days)
if not df_scatter.empty:
    fig = px.scatter(
        df_scatter,
        x="avg_readability",
        y="article_count",
        color="agency_type",
        size="image_rate",
        hover_name="agency_name",
        labels={
            "avg_readability": "Legibilidade (Flesch)",
            "article_count": "Artigos publicados",
            "agency_type": "Tipo",
            "image_rate": "Taxa de imagem",
        },
    )
    fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=500)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# -------------------------------------------------------------------------
# Media usage
# -------------------------------------------------------------------------

if not df_quality.empty:
    st.subheader("Uso de mídia visual")
    media = df_quality.groupby("agency_type").agg(
        image_rate=("has_image", "mean"),
        video_rate=("has_video", "mean"),
    ).reset_index()
    media = media.melt(id_vars="agency_type", var_name="tipo", value_name="taxa")
    media["tipo"] = media["tipo"].map({"image_rate": "Imagem", "video_rate": "Vídeo"})

    fig = px.bar(
        media,
        x="agency_type",
        y="taxa",
        color="tipo",
        barmode="group",
        labels={"agency_type": "Tipo de agência", "taxa": "Taxa", "tipo": "Mídia"},
    )
    fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=350, yaxis_tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)
