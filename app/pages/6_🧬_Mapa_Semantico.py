"""Página 6: Mapa Semântico (exploratório, avançado)

Projeção UMAP dos embeddings 768-dim para visualização 2D.
Dados vêm do PostgreSQL: news.content_embedding (pgvector).
"""

import streamlit as st
import plotly.express as px

from data.postgres import get_embeddings_sample, get_similarity_clusters
from utils import COLORS, WIDGET_HELP, fmt_number

st.set_page_config(page_title="Mapa Semântico — Panorama Gov.BR", page_icon="🧬", layout="wide")
st.title("🧬 Mapa Semântico")
st.caption("Topografia da comunicação governamental — artigos similares ficam próximos")

# -------------------------------------------------------------------------
# Parameters
# -------------------------------------------------------------------------

col_params = st.sidebar.container()
days = col_params.selectbox("Período", [30, 90, 180, 365], index=1, format_func=lambda d: f"{d} dias", help=WIDGET_HELP["periodo"])
sample_size = col_params.slider("Amostra de artigos", 1000, 10000, 5000, step=1000, help=WIDGET_HELP["amostra_slider"])

# -------------------------------------------------------------------------
# Load embeddings
# -------------------------------------------------------------------------

with st.spinner("Carregando embeddings do banco de dados..."):
    embeddings, metadata = get_embeddings_sample(days, sample_size)

if len(embeddings) == 0:
    st.warning(
        "Sem embeddings disponíveis para o período selecionado. "
        "Verifique se o DATABASE_URL está configurado e se os embeddings foram gerados."
    )
    st.stop()

st.info(f"{fmt_number(len(embeddings))} artigos carregados. Projetando em 2D com UMAP...")

# -------------------------------------------------------------------------
# UMAP projection
# -------------------------------------------------------------------------


@st.cache_data(ttl=3600)
def compute_umap(_embeddings, n_neighbors: int = 15, min_dist: float = 0.1):
    """Compute UMAP 2D projection. Underscore prefix excludes from hashing."""
    from umap import UMAP
    reducer = UMAP(n_components=2, n_neighbors=n_neighbors, min_dist=min_dist, random_state=42, metric="cosine")
    return reducer.fit_transform(_embeddings)


with st.spinner("Calculando projeção UMAP (pode levar alguns segundos)..."):
    coords = compute_umap(embeddings)

metadata = metadata.copy()
metadata["x"] = coords[:, 0]
metadata["y"] = coords[:, 1]

# -------------------------------------------------------------------------
# Scatter plot
# -------------------------------------------------------------------------

st.subheader("Projeção UMAP dos artigos")

fig = px.scatter(
    metadata,
    x="x",
    y="y",
    color="theme_l1",
    hover_data={"title": True, "agency_name": True, "theme_l1": True, "x": False, "y": False},
    labels={"theme_l1": "Tema L1"},
    opacity=0.6,
)
fig.update_traces(marker=dict(size=4))
fig.update_layout(
    margin=dict(t=10, l=10, r=10, b=10),
    height=700,
    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=""),
    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=""),
    legend=dict(orientation="h", yanchor="bottom", y=-0.15),
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("""
**Como ler este gráfico**: Cada ponto é um artigo. Artigos com conteúdo semanticamente similar
ficam próximos. As cores representam o tema principal (L1). Clusters densos indicam temas
com cobertura uniforme; artigos isolados são outliers temáticos.
""")

st.divider()

# -------------------------------------------------------------------------
# Similarity clusters — articles with most similar articles
# -------------------------------------------------------------------------

st.subheader("Clusters de alta similaridade")
st.caption("Artigos com maior número de artigos similares — indica eventos de grande repercussão")

df_clusters = get_similarity_clusters(days)
if not df_clusters.empty:
    df_clusters["published_at"] = df_clusters["published_at"].dt.strftime("%d/%m/%Y")
    st.dataframe(
        df_clusters.rename(columns={
            "title": "Título",
            "agency_name": "Agência",
            "theme_l1": "Tema",
            "published_at": "Publicação",
            "similar_count": "Artigos similares",
        })[["Título", "Agência", "Tema", "Publicação", "Artigos similares"]],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("Sem dados de clusters de similaridade para o período selecionado.")
