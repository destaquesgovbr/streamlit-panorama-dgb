"""Utility functions: formatting, colors, constants."""

# DGB brand colors
COLORS = {
    "primary": "#1351B4",
    "positive": "#168821",
    "neutral": "#636363",
    "negative": "#E52207",
    "background": "#F0F2F5",
}

SENTIMENT_COLORS = {
    "positive": COLORS["positive"],
    "neutral": COLORS["neutral"],
    "negative": COLORS["negative"],
}

DOW_LABELS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


# ---------------------------------------------------------------------------
# Tooltip help texts — centralized for consistency
# ---------------------------------------------------------------------------

METRIC_HELP = {
    "artigos_publicados": "Total de artigos publicados no período, comparado com o período anterior de mesma duração.",
    "agencias_ativas": "Número de agências que publicaram ao menos um artigo no período.",
    "temas_cobertos": "Quantidade de temas distintos (nível 1 da taxonomia) com publicações no período.",
    "sentimento_medio": "Média do score de sentimento dos artigos (-1 = negativo, 0 = neutro, +1 = positivo). Calculado por modelo de NLP.",
    "trending_theme": "Crescimento percentual de artigos neste tema em relação ao período anterior. Temas em alta têm aumento incomum de publicações.",
    "artigos_agencia": "Total de artigos publicados por esta agência no período selecionado.",
    "sentimento_agencia": "Sentimento médio dos artigos desta agência (-1 a +1). Valores acima de 0 indicam tom predominantemente positivo.",
    "palavras_artigo": "Média de palavras por artigo desta agência. Indica a profundidade típica do conteúdo.",
    "legibilidade": "Índice Flesch de legibilidade (0–100). Quanto maior, mais fácil de ler. Acima de 50 = acessível ao público geral.",
    "taxa_imagem": "Percentual de artigos que contêm ao menos uma imagem.",
    "taxa_video": "Percentual de artigos que contêm ao menos um vídeo embutido.",
    "agora_online": "Visitantes ativos no portal neste momento (tempo real via Umami Analytics).",
    "pageviews": "Total de páginas visualizadas no período. Inclui visualizações repetidas pelo mesmo visitante.",
    "visitantes": "Visitantes únicos no período, identificados por cookies do Umami Analytics.",
    "sessoes": "Total de sessões (visitas) no período. Um visitante pode ter múltiplas sessões.",
    "bounce_rate": "Percentual de sessões em que o visitante saiu sem interagir (apenas 1 pageview).",
}

WIDGET_HELP = {
    "periodo": "Filtra os dados para os últimos N dias. O período anterior (mesma duração) é usado para calcular deltas.",
    "periodo_home": "Filtra os dados da visão geral. Períodos maiores mostram tendências de longo prazo; menores mostram variações recentes.",
    "granularidade": "Agrupa os dados por dia, semana ou mês no gráfico de volume.",
    "busca_agencia": "Digite para filtrar. Mostra todas as agências cadastradas no portal gov.br.",
    "selecao_entidades": "Selecione até 5 entidades para comparar menções ao longo do tempo.",
    "amostra_slider": "Número de artigos amostrados para a projeção UMAP. Amostras maiores são mais representativas, mas mais lentas.",
}


def fmt_number(n: float, decimals: int = 0) -> str:
    """Format number with thousand separators (Brazilian style)."""
    if decimals == 0:
        return f"{int(n):,}".replace(",", ".")
    return f"{n:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(n: float, decimals: int = 1) -> str:
    """Format as percentage."""
    return f"{n:+.{decimals}f}%"


def fmt_delta(current: float, previous: float) -> str:
    """Format delta between two values as percentage."""
    if previous == 0:
        return "N/A"
    delta = (current - previous) / previous * 100
    return fmt_pct(delta)
