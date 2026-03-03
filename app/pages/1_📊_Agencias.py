"""Página 2: Análise por Agência (Assessor de Comunicação)"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from data.bigquery import (
    get_agencies,
    get_agency_stats,
    get_agency_heatmap,
    get_agency_sentiment,
    get_agency_themes,
    get_benchmarking,
)
from utils import DOW_LABELS, METRIC_HELP, SENTIMENT_COLORS, WIDGET_HELP, fmt_number

st.set_page_config(page_title="Agências — Panorama Gov.BR", page_icon="📊", layout="wide")
st.title("📊 Análise por Agência")

# -------------------------------------------------------------------------
# Agency selector with search + quick links
# -------------------------------------------------------------------------

DEFAULT_AGENCY = "gestao"

TOP_MINISTERIOS = [
    ("gestao", "Gestão e Inovação"),
    ("saude", "Saúde"),
    ("mec", "Educação"),
    ("fazenda", "Fazenda"),
    ("defesa", "Defesa"),
    ("mj", "Justiça"),
    ("mds", "Desenv. Social"),
    ("mdic", "Desenv. e Indústria"),
    ("mcti", "Ciência e Tecnologia"),
    ("trabalho-e-emprego", "Trabalho"),
]

df_agencies = get_agencies()
agency_options = df_agencies[["agency_key", "agency_name"]].set_index("agency_key")["agency_name"].to_dict()

# Quick links in 2 rows of 5
st.caption("Acesso rápido — Ministérios:")
for row_start in (0, 5):
    row_items = TOP_MINISTERIOS[row_start:row_start + 5]
    quick_cols = st.columns(5)
    for col, (key, short_name) in zip(quick_cols, row_items):
        if col.button(short_name, key=f"quick_{key}", use_container_width=True):
            st.session_state["selected_agency"] = key

# Initialize default
if "selected_agency" not in st.session_state:
    st.session_state["selected_agency"] = DEFAULT_AGENCY

# Searchable selectbox
all_keys = list(agency_options.keys())
default_idx = all_keys.index(st.session_state["selected_agency"]) if st.session_state["selected_agency"] in all_keys else 0

selected_key = st.selectbox(
    "Ou busque pelo nome",
    options=all_keys,
    index=default_idx,
    format_func=lambda k: agency_options[k],
    key="agency_selectbox",
    help=WIDGET_HELP["busca_agencia"],
)

# Sync: if selectbox changed manually, update session state
if selected_key != st.session_state.get("selected_agency"):
    st.session_state["selected_agency"] = selected_key

agency_row = df_agencies[df_agencies["agency_key"] == selected_key].iloc[0]
agency_name = agency_row["agency_name"]
agency_type = agency_row["agency_type"]

days = st.sidebar.selectbox("Período", [30, 90, 180, 365], index=1, format_func=lambda d: f"{d} dias", help=WIDGET_HELP["periodo"])

st.subheader(f"{agency_name}")
st.caption(f"Tipo: {agency_type or 'N/D'}")

# -------------------------------------------------------------------------
# KPIs
# -------------------------------------------------------------------------

df_stats = get_agency_stats(selected_key, days)
if not df_stats.empty:
    s = df_stats.iloc[0]
    cols = st.columns(6)
    cols[0].metric("Artigos", fmt_number(s["total_articles"]), help=METRIC_HELP["artigos_agencia"])
    cols[1].metric("Sentimento", f"{s['avg_sentiment']:.2f}" if pd.notna(s["avg_sentiment"]) else "N/D", help=METRIC_HELP["sentimento_agencia"])
    cols[2].metric("Palavras/artigo", fmt_number(s["avg_word_count"]) if pd.notna(s["avg_word_count"]) else "N/D", help=METRIC_HELP["palavras_artigo"])
    cols[3].metric("Legibilidade", f"{s['avg_readability']:.1f}" if pd.notna(s["avg_readability"]) else "N/D", help=METRIC_HELP["legibilidade"])
    cols[4].metric("Taxa de imagem", f"{s['image_rate']:.0%}" if pd.notna(s["image_rate"]) else "N/D", help=METRIC_HELP["taxa_imagem"])
    cols[5].metric("Taxa de vídeo", f"{s['video_rate']:.0%}" if pd.notna(s["video_rate"]) else "N/D", help=METRIC_HELP["taxa_video"])

st.divider()

# -------------------------------------------------------------------------
# Heatmap + Sentiment
# -------------------------------------------------------------------------

col_heat, col_sent = st.columns(2)

with col_heat:
    st.subheader("Padrão de publicação")
    df_heat = get_agency_heatmap(selected_key, days)
    if not df_heat.empty:
        # Pivot to hour x dow matrix
        pivot = df_heat.pivot_table(index="hour", columns="dow", values="article_count", fill_value=0)
        pivot = pivot.reindex(index=range(24), columns=range(7), fill_value=0)
        pivot.columns = DOW_LABELS

        fig = px.imshow(
            pivot,
            labels=dict(x="Dia", y="Hora", color="Artigos"),
            color_continuous_scale="Blues",
            aspect="auto",
        )
        fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados de publicação para o período.")

with col_sent:
    st.subheader("Distribuição de sentimento")
    df_sent = get_agency_sentiment(selected_key, days)
    if not df_sent.empty:
        fig = px.pie(
            df_sent,
            values="count",
            names="sentiment_label",
            color="sentiment_label",
            color_discrete_map=SENTIMENT_COLORS,
            hole=0.4,
        )
        fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados de sentimento para o período.")

# -------------------------------------------------------------------------
# Theme coverage
# -------------------------------------------------------------------------

st.subheader("Cobertura temática")
df_themes = get_agency_themes(selected_key, days)
if not df_themes.empty:
    fig = px.bar(
        df_themes.head(15),
        x="article_count",
        y="theme",
        orientation="h",
        labels={"article_count": "Artigos", "theme": ""},
        color_discrete_sequence=[SENTIMENT_COLORS["neutral"]],
    )
    fig.update_layout(
        margin=dict(t=10, l=10, r=10, b=10),
        height=max(300, len(df_themes.head(15)) * 30),
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig, use_container_width=True)

# -------------------------------------------------------------------------
# Benchmarking
# -------------------------------------------------------------------------

if agency_type:
    st.subheader(f"Benchmarking: {agency_type}")
    df_bench = get_benchmarking(agency_type, days)
    if not df_bench.empty:
        # Highlight selected agency
        df_bench["destaque"] = df_bench["agency_key"] == selected_key
        st.dataframe(
            df_bench[["agency_name", "total_articles", "avg_sentiment", "avg_readability", "image_rate"]]
            .rename(columns={
                "agency_name": "Agência",
                "total_articles": "Artigos",
                "avg_sentiment": "Sentimento",
                "avg_readability": "Legibilidade",
                "image_rate": "% Imagem",
            })
            .style.format({"Sentimento": "{:.2f}", "Legibilidade": "{:.1f}", "% Imagem": "{:.0%}"}),
            use_container_width=True,
            hide_index=True,
        )
