"""Página 3: Panorama Temático (Gestor Público)"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from data.bigquery import (
    get_theme_hierarchy,
    get_agency_theme_matrix,
    get_sankey_agency_theme,
    get_theme_gaps,
    get_theme_evolution,
)
from utils import COLORS, WIDGET_HELP

st.set_page_config(page_title="Temas — Panorama Gov.BR", page_icon="🏷️", layout="wide")
st.title("🏷️ Panorama Temático")

days = st.sidebar.selectbox("Período", [30, 90, 180, 365], index=1, format_func=lambda d: f"{d} dias", help=WIDGET_HELP["periodo"])

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
    top_agencies = pivot.sum(axis=1).nlargest(20).index
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

st.divider()

# -------------------------------------------------------------------------
# Sankey: Agency → Theme
# -------------------------------------------------------------------------

st.subheader("Fluxo Agência → Tema")
st.caption("Quais agências dominam quais temas (top 10 de cada)")

df_sankey = get_sankey_agency_theme(days)
if not df_sankey.empty:
    sources = df_sankey["source"].unique().tolist()
    targets = df_sankey["target"].unique().tolist()
    all_labels = sources + targets

    source_idx = [sources.index(s) for s in df_sankey["source"]]
    target_idx = [len(sources) + targets.index(t) for t in df_sankey["target"]]

    fig = go.Figure(go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            label=all_labels,
            color=[COLORS["primary"]] * len(sources) + ["#636363"] * len(targets),
        ),
        link=dict(
            source=source_idx,
            target=target_idx,
            value=df_sankey["value"].tolist(),
            color="rgba(19, 81, 180, 0.3)",
        ),
    ))
    fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=500)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# -------------------------------------------------------------------------
# Theme gaps — diverging bar chart
# -------------------------------------------------------------------------

st.subheader("Gaps temáticos")
st.caption("Temas com cobertura acima (verde) ou abaixo (vermelho) da média")

df_gaps = get_theme_gaps(days)
if not df_gaps.empty:
    df_gaps = df_gaps.sort_values("deviation")
    colors = [COLORS["positive"] if d >= 0 else COLORS["negative"] for d in df_gaps["deviation"]]

    fig = go.Figure(go.Bar(
        x=df_gaps["deviation"],
        y=df_gaps["theme"],
        orientation="h",
        marker_color=colors,
        text=df_gaps["deviation_pct"].apply(lambda v: f"{v:+.0f}%"),
        textposition="outside",
    ))
    fig.update_layout(
        margin=dict(t=10, l=10, r=10, b=10),
        height=max(400, len(df_gaps) * 28),
        xaxis_title="Desvio da média (artigos)",
        yaxis_title="",
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# -------------------------------------------------------------------------
# Theme evolution — bump chart (ranking over time)
# -------------------------------------------------------------------------

st.subheader("Evolução temática")
st.caption("Ranking semanal dos temas (top 10)")

df_evo = get_theme_evolution(days)
if not df_evo.empty:
    fig = px.line(
        df_evo,
        x="week",
        y="rank",
        color="theme",
        markers=True,
        labels={"week": "", "rank": "Posição no ranking", "theme": "Tema"},
    )
    fig.update_yaxes(autorange="reversed", dtick=1)
    fig.update_layout(
        margin=dict(t=10, l=10, r=10, b=10),
        height=450,
        legend=dict(orientation="h", yanchor="bottom", y=-0.4),
    )
    st.plotly_chart(fig, use_container_width=True)
