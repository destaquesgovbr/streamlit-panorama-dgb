"""Página 4: Entidades e Atores (Gestor Público / Assessor)

Dados vêm do PostgreSQL: news_features.features->'entities' (JSONB).
"""

import streamlit as st
import plotly.express as px
from streamlit_agraph import agraph, Node, Edge, Config

from data.postgres import get_top_entities, get_entity_timeline, get_entity_cooccurrence, get_entity_nodes
from utils import COLORS, WIDGET_HELP

st.set_page_config(page_title="Entidades — Panorama Gov.BR", page_icon="👤", layout="wide")
st.title("👤 Entidades e Atores")

days = st.sidebar.selectbox("Período", [30, 90, 180, 365], index=1, format_func=lambda d: f"{d} dias", help=WIDGET_HELP["periodo"])

ENTITY_TYPE_LABELS = {
    "ORG": "Organizações",
    "PER": "Pessoas",
    "LOC": "Locais",
    "MISC": "Outros",
}

ENTITY_TYPE_COLORS = {
    "ORG": COLORS["primary"],
    "PER": "#168821",
    "LOC": "#E52207",
    "MISC": "#636363",
}

# -------------------------------------------------------------------------
# Top entities by type — 4 panels
# -------------------------------------------------------------------------

st.subheader("Top entidades por tipo")
st.caption("Extraídas automaticamente dos textos por modelo de NER (reconhecimento de entidades nomeadas).")

tabs = st.tabs(list(ENTITY_TYPE_LABELS.values()))

for tab, (etype, label) in zip(tabs, ENTITY_TYPE_LABELS.items()):
    with tab:
        top_n = 10 if etype == "MISC" else 20
        df = get_top_entities(etype, days, top_n)
        if df.empty:
            st.info(f"Sem dados de {label.lower()} para o período selecionado.")
            continue

        fig = px.bar(
            df.sort_values("total_mentions"),
            x="total_mentions",
            y="entity_name",
            orientation="h",
            color_discrete_sequence=[ENTITY_TYPE_COLORS[etype]],
            labels={"total_mentions": "Menções", "entity_name": ""},
            hover_data={"article_count": True},
        )
        fig.update_layout(
            margin=dict(t=10, l=10, r=10, b=10),
            height=max(350, len(df) * 25),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# -------------------------------------------------------------------------
# Entity timeline — compare selected entities
# -------------------------------------------------------------------------

st.subheader("Entidades ao longo do tempo")
st.caption("Selecione entidades para comparar menções semanais")

df_org = get_top_entities("ORG", days, 20)
df_per = get_top_entities("PER", days, 20)
available = []
if not df_org.empty:
    available.extend(df_org["entity_name"].tolist())
if not df_per.empty:
    available.extend(df_per["entity_name"].tolist())

selected_entities = st.multiselect(
    "Entidades",
    options=available[:40],
    default=available[:3] if len(available) >= 3 else available,
    max_selections=5,
    help=WIDGET_HELP["selecao_entidades"],
)

if selected_entities:
    df_timeline = get_entity_timeline(selected_entities, days)
    if not df_timeline.empty:
        fig = px.line(
            df_timeline,
            x="week",
            y="mentions",
            color="entity_name",
            markers=True,
            labels={"week": "", "mentions": "Menções", "entity_name": "Entidade"},
        )
        fig.update_layout(
            margin=dict(t=10, l=10, r=10, b=10),
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=-0.3),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados de timeline para as entidades selecionadas.")

st.divider()

# -------------------------------------------------------------------------
# Co-occurrence network graph
# -------------------------------------------------------------------------

st.subheader("Rede de co-ocorrência")
st.caption("Entidades que aparecem juntas nos mesmos artigos — tamanho = frequência, cor = tipo")

df_nodes = get_entity_nodes(days, top_n=40)
df_edges = get_entity_cooccurrence(days, min_cooccurrences=3, top_n=40)

if not df_nodes.empty and not df_edges.empty:
    # Deduplicate: same entity name can appear with different types
    df_nodes = df_nodes.sort_values("total_mentions", ascending=False).drop_duplicates(subset="entity_name", keep="first")
    max_mentions = df_nodes["total_mentions"].max()

    nodes = []
    for _, row in df_nodes.iterrows():
        size = max(15, int(row["total_mentions"] / max_mentions * 50))
        nodes.append(Node(
            id=row["entity_name"],
            label=row["entity_name"],
            size=size,
            color=ENTITY_TYPE_COLORS.get(row["entity_type"], "#636363"),
            title=f"{row['entity_name']} ({row['entity_type']})\n{int(row['total_mentions'])} menções em {int(row['article_count'])} artigos",
        ))

    node_ids = {n.id for n in nodes}
    edges = []
    for _, row in df_edges.iterrows():
        if row["source"] in node_ids and row["target"] in node_ids:
            edges.append(Edge(
                source=row["source"],
                target=row["target"],
                width=max(1, int(row["weight"] / 5)),
                title=f"{int(row['weight'])} artigos em comum",
            ))

    config = Config(
        width=900,
        height=600,
        directed=False,
        physics=True,
        hierarchical=False,
        nodeHighlightBehavior=True,
        highlightColor="#1351B4",
        collapsible=False,
    )

    agraph(nodes=nodes, edges=edges, config=config)

    # Legend
    legend_cols = st.columns(4)
    for col, (etype, label) in zip(legend_cols, ENTITY_TYPE_LABELS.items()):
        col.markdown(
            f'<span style="color:{ENTITY_TYPE_COLORS[etype]}">●</span> {label}',
            unsafe_allow_html=True,
        )
else:
    st.info("Sem dados de entidades suficientes para gerar a rede de co-ocorrência.")
