"""Página 7: Engajamento do Portal (Assessor / Gestor)

Dados vêm da Umami Analytics API (portal destaquesgovbr).
Quando a API não está configurada, exibe placeholders informativos.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from data.umami import (
    _is_configured,
    get_stats_comparison,
    get_pageviews_series,
    get_metrics,
    get_events_series,
    get_active_visitors,
    get_top_pages,
)
from utils import COLORS, fmt_number

st.set_page_config(page_title="Engajamento — Panorama Gov.BR", page_icon="📈", layout="wide")
st.title("📈 Engajamento do Portal")

if not _is_configured():
    st.warning(
        "Umami Analytics não configurado. "
        "Defina as variáveis `UMAMI_API_URL`, `UMAMI_WEBSITE_ID` e `UMAMI_API_TOKEN` para ativar esta página."
    )
    st.stop()

days = st.sidebar.selectbox("Período", [7, 30, 90, 180], index=1, format_func=lambda d: f"{d} dias")

# -------------------------------------------------------------------------
# KPIs de tráfego
# -------------------------------------------------------------------------

current, prev = get_stats_comparison(days)

if current:
    cols = st.columns(5)

    active = get_active_visitors()
    cols[0].metric("Agora online", fmt_number(active))

    def _stat(data, key):
        v = data.get(key, 0)
        return v.get("value", 0) if isinstance(v, dict) else (v or 0)

    pv = _stat(current, "pageviews")
    pv_prev = _stat(prev, "pageviews")
    cols[1].metric("Pageviews", fmt_number(pv), delta=fmt_number(pv - pv_prev) if pv_prev else None)

    visitors = _stat(current, "visitors")
    vis_prev = _stat(prev, "visitors")
    cols[2].metric("Visitantes", fmt_number(visitors), delta=fmt_number(visitors - vis_prev) if vis_prev else None)

    visits = _stat(current, "visits")
    vis2_prev = _stat(prev, "visits")
    cols[3].metric("Sessões", fmt_number(visits), delta=fmt_number(visits - vis2_prev) if vis2_prev else None)

    bounces = _stat(current, "bounces")
    bounce_rate = round(bounces / visits * 100, 1) if visits > 0 else 0
    cols[4].metric("Bounce rate", f"{bounce_rate}%")

st.divider()

# -------------------------------------------------------------------------
# Pageviews e sessões ao longo do tempo
# -------------------------------------------------------------------------

st.subheader("Tráfego ao longo do tempo")

unit = "day" if days <= 90 else "week"
df_pv = get_pageviews_series(days, unit)

if not df_pv.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_pv["date"], y=df_pv["pageviews"],
        name="Pageviews", mode="lines+markers",
        line=dict(color=COLORS["primary"], width=2),
    ))
    fig.add_trace(go.Scatter(
        x=df_pv["date"], y=df_pv["sessions"],
        name="Sessões", mode="lines+markers",
        line=dict(color="#636363", width=2, dash="dot"),
    ))
    fig.update_layout(
        margin=dict(t=10, l=10, r=10, b=10),
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2),
        xaxis_title="", yaxis_title="",
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# -------------------------------------------------------------------------
# Artigos mais acessados
# -------------------------------------------------------------------------

st.subheader("Páginas mais acessadas")

df_pages = get_top_pages(days, limit=30)
if not df_pages.empty:
    # Filter article pages (typically /artigo/ or /noticia/ paths)
    df_articles = df_pages[df_pages["x"].str.contains("/artigo/|/noticia/", na=False)].copy()

    if not df_articles.empty:
        df_articles = df_articles.rename(columns={"x": "Página", "y": "Visitantes"}).head(20)
        st.dataframe(df_articles[["Página", "Visitantes"]], use_container_width=True, hide_index=True)
    else:
        # Show all pages if no article pattern detected
        df_show = df_pages.rename(columns={"x": "Página", "y": "Visitantes"}).head(20)
        st.dataframe(df_show[["Página", "Visitantes"]], use_container_width=True, hide_index=True)

st.divider()

# -------------------------------------------------------------------------
# Análise de busca
# -------------------------------------------------------------------------

st.subheader("Volume de buscas no portal")
st.caption("Eventos de busca rastreados pelo portal")

df_search = get_events_series("search", days)
if not df_search.empty and df_search["count"].sum() > 0:
    fig = px.bar(
        df_search,
        x="date", y="count",
        labels={"date": "", "count": "Buscas"},
        color_discrete_sequence=[COLORS["primary"]],
    )
    fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=300)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sem dados de busca para o período selecionado.")

st.divider()

# -------------------------------------------------------------------------
# Origens de tráfego
# -------------------------------------------------------------------------

col_ref, col_device = st.columns(2)

with col_ref:
    st.subheader("Origens de tráfego")
    df_ref = get_metrics("referrer", days, limit=10)
    if not df_ref.empty:
        df_ref = df_ref.rename(columns={"x": "Referrer", "y": "Visitantes"})
        df_ref.loc[df_ref["Referrer"] == "", "Referrer"] = "(direto)"

        fig = px.pie(
            df_ref, names="Referrer", values="Visitantes",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=350)
        st.plotly_chart(fig, use_container_width=True)

with col_device:
    st.subheader("Dispositivos")
    df_device = get_metrics("device", days)
    if not df_device.empty:
        df_device = df_device.rename(columns={"x": "Dispositivo", "y": "Visitantes"})

        fig = px.pie(
            df_device, names="Dispositivo", values="Visitantes",
            color_discrete_sequence=[COLORS["primary"], "#636363", "#E52207"],
        )
        fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=350)
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# -------------------------------------------------------------------------
# Browsers e OS
# -------------------------------------------------------------------------

col_browser, col_os = st.columns(2)

with col_browser:
    st.subheader("Navegadores")
    df_browser = get_metrics("browser", days, limit=8)
    if not df_browser.empty:
        df_browser = df_browser.rename(columns={"x": "Navegador", "y": "Visitantes"})
        fig = px.bar(
            df_browser, x="Visitantes", y="Navegador", orientation="h",
            color_discrete_sequence=[COLORS["primary"]],
        )
        fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=300, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

with col_os:
    st.subheader("Sistemas Operacionais")
    df_os = get_metrics("os", days, limit=8)
    if not df_os.empty:
        df_os = df_os.rename(columns={"x": "SO", "y": "Visitantes"})
        fig = px.bar(
            df_os, x="Visitantes", y="SO", orientation="h",
            color_discrete_sequence=["#636363"],
        )
        fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=300, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# -------------------------------------------------------------------------
# Funil de engajamento
# -------------------------------------------------------------------------

st.subheader("Funil de engajamento")
st.caption("Visitantes → Buscas → Cliques em artigo")

if current:
    total_visitors = current.get("visitors", {}).get("value", 0)

    df_search_total = get_events_series("search", days)
    search_total = int(df_search_total["count"].sum()) if not df_search_total.empty else 0

    df_clicks = get_events_series("article_click", days)
    click_total = int(df_clicks["count"].sum()) if not df_clicks.empty else 0

    funnel_data = {
        "stage": ["Visitantes", "Buscas", "Cliques em artigo"],
        "value": [total_visitors, search_total, click_total],
    }

    if total_visitors > 0:
        fig = go.Figure(go.Funnel(
            y=funnel_data["stage"],
            x=funnel_data["value"],
            textinfo="value+percent initial",
            marker=dict(color=[COLORS["primary"], "#636363", COLORS["positive"]]),
        ))
        fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados suficientes para o funil de engajamento.")

# -------------------------------------------------------------------------
# Geografia
# -------------------------------------------------------------------------

st.divider()
st.subheader("Distribuição geográfica")

df_country = get_metrics("country", days, limit=15)
if not df_country.empty:
    df_country = df_country.rename(columns={"x": "País", "y": "Visitantes"})
    fig = px.bar(
        df_country, x="Visitantes", y="País", orientation="h",
        color_discrete_sequence=[COLORS["primary"]],
    )
    fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=max(300, len(df_country) * 28), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
