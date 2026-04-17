import os

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# ── Conexão & helpers ────────────────────────────────────────────

@st.cache_resource
def _get_engine():
    url = os.getenv("DATABASE_URL")
    if not url:
        st.error("DATABASE_URL não definida no arquivo .env")
        return None
    return create_engine(url)


@st.cache_data(ttl=600, show_spinner=False)
def run_query(query: str) -> pd.DataFrame:
    engine = _get_engine()
    if engine is None:
        return pd.DataFrame()
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)


def _template():
    return "plotly_dark" if st.session_state.get("theme") == "dark" else "plotly_white"


# ── Sidebar ──────────────────────────────────────────────────────

with st.sidebar:
    if st.session_state.get("auth"):
        if st.button("Sair", type="secondary", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    category_filter = st.selectbox(
        "Filtrar por Categoria",
        options=[
            "📊 Vendas & Receita",
            "🛒 Pedidos",
            "🚚 Logística & Entregas",
            "⭐ Satisfação do Cliente",
            "🏪 Vendedores",
        ],
    )


# ═════════════════════════════════════════════════════════════════
# 1. VENDAS & RECEITA
# ═════════════════════════════════════════════════════════════════
def render_vendas_receita():
    st.title("📊 Dashboard de Vendas & Receita")

    # ── KPIs ─────────────────────────────────────────────────────
    df_kpis = run_query("""
        SELECT
            SUM(oi.price)                     AS receita_total,
            COUNT(DISTINCT o.order_id)        AS num_vendas
        FROM olist.order_items oi
        JOIN olist.orders o ON oi.order_id = o.order_id
        WHERE o.status = 'delivered'
    """)

    df_ticket = run_query("""
        SELECT AVG(total_pedido) AS ticket_medio
        FROM (
            SELECT o.order_id, SUM(oi.price) AS total_pedido
            FROM olist.order_items oi
            JOIN olist.orders o ON oi.order_id = o.order_id
            WHERE o.status = 'delivered'
            GROUP BY o.order_id
        ) sub
    """)

    df_meses = run_query("""
        SELECT COUNT(DISTINCT DATE_TRUNC('month', purchase_timestamp)) AS num_meses
        FROM olist.orders
        WHERE status = 'delivered'
    """)

    receita_total = float(df_kpis["receita_total"].iloc[0] or 0)
    ticket_medio  = float(df_ticket["ticket_medio"].iloc[0] or 0)
    num_vendas    = int(df_kpis["num_vendas"].iloc[0] or 0)
    num_meses     = int(df_meses["num_meses"].iloc[0] or 1)
    receita_mes   = receita_total / num_meses

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Receita Total", f"R$ {receita_total:,.2f}")
    with c2:
        st.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}")
    with c3:
        st.metric("Nº de Vendas", f"{num_vendas:,}")
    with c4:
        st.metric("Receita Média / Mês", f"R$ {receita_mes:,.2f}")

    st.divider()

    # ── Receita mensal (linha) ───────────────────────────────────
    df_mensal = run_query("""
        SELECT DATE_TRUNC('month', o.purchase_timestamp) AS mes,
               SUM(oi.price) AS receita
        FROM olist.order_items oi
        JOIN olist.orders o ON oi.order_id = o.order_id
        WHERE o.status = 'delivered'
        GROUP BY mes
        ORDER BY mes
    """)
    if not df_mensal.empty:
        df_mensal["mes"] = pd.to_datetime(df_mensal["mes"])
        fig = px.line(
            df_mensal, x="mes", y="receita",
            title="Receita Mensal",
            labels={"mes": "Mês", "receita": "Receita (R$)"},
            template=_template(),
        )
        fig.update_traces(line=dict(width=2.5))
        st.plotly_chart(fig, use_container_width=True)

    # ── Top 10 categorias + Tipo de pagamento ────────────────────
    col1, col2 = st.columns(2)

    with col1:
        df_top_cat = run_query("""
            SELECT p.product_category AS categoria,
                   SUM(oi.price)      AS receita
            FROM olist.order_items oi
            JOIN olist.products p ON oi.product_id = p.product_id
            WHERE p.product_category IS NOT NULL
            GROUP BY p.product_category
            ORDER BY receita DESC
            LIMIT 10
        """)
        if not df_top_cat.empty:
            fig = px.bar(
                df_top_cat, x="receita", y="categoria",
                orientation="h",
                title="Top 10 Categorias por Receita",
                labels={"receita": "Receita (R$)", "categoria": "Categoria"},
                template=_template(),
            )
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        df_pag = run_query("""
            SELECT payment_type    AS tipo,
                   SUM(payment_value) AS total
            FROM olist.order_payments
            GROUP BY payment_type
        """)
        if not df_pag.empty:
            fig = px.pie(
                df_pag, values="total", names="tipo",
                title="Distribuição por Tipo de Pagamento",
                hole=0.4,
                template=_template(),
            )
            st.plotly_chart(fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════════
# 2. PEDIDOS
# ═════════════════════════════════════════════════════════════════
def render_pedidos():
    st.title("🛒 Dashboard de Pedidos")

    # ── KPIs ─────────────────────────────────────────────────────
    df_kpis = run_query("""
        SELECT
            COUNT(*)                                        AS total_pedidos,
            COUNT(*) FILTER (WHERE status = 'delivered')    AS entregues,
            COUNT(*) FILTER (WHERE status = 'canceled')     AS cancelados
        FROM olist.orders
    """)

    total      = int(df_kpis["total_pedidos"].iloc[0] or 0)
    entregues  = int(df_kpis["entregues"].iloc[0] or 0)
    cancelados = int(df_kpis["cancelados"].iloc[0] or 0)
    taxa_cancel = (cancelados / total * 100) if total > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total de Pedidos", f"{total:,}")
    with c2:
        st.metric("Entregues", f"{entregues:,}")
    with c3:
        st.metric("Cancelados", f"{cancelados:,}")
    with c4:
        st.metric("Taxa de Cancelamento", f"{taxa_cancel:.1f}%")

    st.divider()

    # ── Volume mensal (linha) ────────────────────────────────────
    df_vol = run_query("""
        SELECT DATE_TRUNC('month', purchase_timestamp) AS mes,
               COUNT(*) AS total
        FROM olist.orders
        GROUP BY mes
        ORDER BY mes
    """)
    if not df_vol.empty:
        df_vol["mes"] = pd.to_datetime(df_vol["mes"])
        fig = px.line(
            df_vol, x="mes", y="total",
            title="Volume de Pedidos por Mês",
            labels={"mes": "Mês", "total": "Pedidos"},
            template=_template(),
        )
        fig.update_traces(line=dict(width=2.5))
        st.plotly_chart(fig, use_container_width=True)

    # ── Status + Top categorias ──────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        df_status = run_query("""
            SELECT status, COUNT(*) AS total
            FROM olist.orders
            GROUP BY status
            ORDER BY total DESC
        """)
        if not df_status.empty:
            fig = px.bar(
                df_status, x="total", y="status",
                orientation="h",
                title="Distribuição por Status",
                labels={"total": "Quantidade", "status": "Status"},
                template=_template(),
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        df_top_cat = run_query("""
            SELECT p.product_category AS categoria,
                   COUNT(*)           AS total
            FROM olist.order_items oi
            JOIN olist.products p ON oi.product_id = p.product_id
            WHERE p.product_category IS NOT NULL
            GROUP BY p.product_category
            ORDER BY total DESC
            LIMIT 10
        """)
        if not df_top_cat.empty:
            fig = px.bar(
                df_top_cat, x="total", y="categoria",
                orientation="h",
                title="Top 10 Categorias Mais Pedidas",
                labels={"total": "Quantidade", "categoria": "Categoria"},
                template=_template(),
            )
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

    # ── Itens por pedido ─────────────────────────────────────────
    df_itens = run_query("""
        SELECT item_count AS itens, COUNT(*) AS frequencia
        FROM (
            SELECT order_id, COUNT(*) AS item_count
            FROM olist.order_items
            GROUP BY order_id
        ) sub
        GROUP BY item_count
        ORDER BY item_count
    """)
    if not df_itens.empty:
        fig = px.bar(
            df_itens, x="itens", y="frequencia",
            title="Distribuição de Itens por Pedido",
            labels={"itens": "Nº de Itens", "frequencia": "Frequência"},
            template=_template(),
        )
        st.plotly_chart(fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════════
# 3. LOGÍSTICA & ENTREGAS
# ═════════════════════════════════════════════════════════════════
def render_logistica():
    st.title("🚚 Dashboard de Logística & Entregas")

    # ── KPIs ─────────────────────────────────────────────────────
    df_kpis = run_query("""
        SELECT
            AVG(EXTRACT(EPOCH FROM (delivered_customer_date - purchase_timestamp)) / 86400)
                AS tempo_medio,
            COUNT(*) FILTER (WHERE delivered_customer_date <= estimated_delivery_date)
                * 100.0 / COUNT(*) AS pct_no_prazo,
            COUNT(*) FILTER (WHERE delivered_customer_date > estimated_delivery_date)
                * 100.0 / COUNT(*) AS pct_atrasadas
        FROM olist.orders
        WHERE status = 'delivered'
          AND delivered_customer_date IS NOT NULL
          AND estimated_delivery_date IS NOT NULL
    """)

    df_frete = run_query(
        "SELECT AVG(freight_value) AS frete_medio FROM olist.order_items"
    )

    tempo_medio   = float(df_kpis["tempo_medio"].iloc[0] or 0)
    pct_prazo     = float(df_kpis["pct_no_prazo"].iloc[0] or 0)
    pct_atrasadas = float(df_kpis["pct_atrasadas"].iloc[0] or 0)
    frete_medio   = float(df_frete["frete_medio"].iloc[0] or 0)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Tempo Médio de Entrega", f"{tempo_medio:.1f} dias")
    with c2:
        st.metric("Entregas no Prazo", f"{pct_prazo:.1f}%")
    with c3:
        st.metric("Entregas Atrasadas", f"{pct_atrasadas:.1f}%")
    with c4:
        st.metric("Frete Médio", f"R$ {frete_medio:,.2f}")

    st.divider()

    # ── Histograma tempo de entrega ──────────────────────────────
    df_tempo = run_query("""
        SELECT EXTRACT(EPOCH FROM (delivered_customer_date - purchase_timestamp))
               / 86400 AS dias
        FROM olist.orders
        WHERE status = 'delivered'
          AND delivered_customer_date IS NOT NULL
    """)
    if not df_tempo.empty:
        fig = px.histogram(
            df_tempo, x="dias", nbins=50,
            title="Distribuição do Tempo de Entrega",
            labels={"dias": "Dias", "count": "Frequência"},
            template=_template(),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Atrasos por estado + Frete por estado ────────────────────
    col1, col2 = st.columns(2)

    with col1:
        df_atrasos = run_query("""
            SELECT c.state AS estado, COUNT(*) AS total_atrasos
            FROM olist.orders o
            JOIN olist.customers c ON o.customer_id = c.customer_id
            WHERE o.status = 'delivered'
              AND o.delivered_customer_date > o.estimated_delivery_date
              AND o.delivered_customer_date IS NOT NULL
              AND o.estimated_delivery_date IS NOT NULL
            GROUP BY c.state
            ORDER BY total_atrasos DESC
            LIMIT 10
        """)
        if not df_atrasos.empty:
            fig = px.bar(
                df_atrasos, x="total_atrasos", y="estado",
                orientation="h",
                title="Top 10 Estados — Mais Atrasos",
                labels={"total_atrasos": "Atrasos", "estado": "Estado"},
                template=_template(),
            )
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        df_frete_uf = run_query("""
            SELECT c.state AS estado, AVG(oi.freight_value) AS frete_medio
            FROM olist.order_items oi
            JOIN olist.orders o   ON oi.order_id   = o.order_id
            JOIN olist.customers c ON o.customer_id = c.customer_id
            GROUP BY c.state
            ORDER BY frete_medio DESC
        """)
        if not df_frete_uf.empty:
            fig = px.bar(
                df_frete_uf, x="frete_medio", y="estado",
                orientation="h",
                title="Frete Médio por Estado",
                labels={"frete_medio": "Frete Médio (R$)", "estado": "Estado"},
                template=_template(),
            )
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════════
# 4. SATISFAÇÃO DO CLIENTE
# ═════════════════════════════════════════════════════════════════
def render_satisfacao():
    st.title("⭐ Dashboard de Satisfação do Cliente")

    # ── KPIs ─────────────────────────────────────────────────────
    df_kpis = run_query("""
        SELECT
            AVG(rating)  AS nota_media,
            COUNT(*)     AS total_avaliacoes,
            COUNT(*) FILTER (WHERE rating = 5) * 100.0 / COUNT(*) AS pct_5,
            COUNT(*) FILTER (WHERE rating = 1) * 100.0 / COUNT(*) AS pct_1
        FROM olist.order_reviews
    """)

    nota   = float(df_kpis["nota_media"].iloc[0] or 0)
    total  = int(df_kpis["total_avaliacoes"].iloc[0] or 0)
    pct5   = float(df_kpis["pct_5"].iloc[0] or 0)
    pct1   = float(df_kpis["pct_1"].iloc[0] or 0)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Nota Média", f"{nota:.2f} ⭐")
    with c2:
        st.metric("Total de Avaliações", f"{total:,}")
    with c3:
        st.metric("5 Estrelas", f"{pct5:.1f}%")
    with c4:
        st.metric("1 Estrela", f"{pct1:.1f}%")

    st.divider()

    # ── Distribuição ratings + Evolução nota média ───────────────
    col1, col2 = st.columns(2)

    with col1:
        df_rating = run_query("""
            SELECT rating, COUNT(*) AS total
            FROM olist.order_reviews
            GROUP BY rating
            ORDER BY rating
        """)
        if not df_rating.empty:
            fig = px.bar(
                df_rating, x="rating", y="total",
                title="Distribuição de Avaliações",
                labels={"rating": "Nota", "total": "Quantidade"},
                template=_template(),
                color="rating",
                color_continuous_scale="RdYlGn",
            )
            fig.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        df_evo = run_query("""
            SELECT DATE_TRUNC('month', creation_timestamp) AS mes,
                   AVG(rating) AS nota_media
            FROM olist.order_reviews
            GROUP BY mes
            ORDER BY mes
        """)
        if not df_evo.empty:
            df_evo["mes"] = pd.to_datetime(df_evo["mes"])
            fig = px.line(
                df_evo, x="mes", y="nota_media",
                title="Evolução da Nota Média",
                labels={"mes": "Mês", "nota_media": "Nota Média"},
                template=_template(),
            )
            fig.update_traces(line=dict(width=2.5))
            fig.update_yaxes(range=[1, 5])
            st.plotly_chart(fig, use_container_width=True)

    # ── Nota média por categoria ─────────────────────────────────
    df_cat_nota = run_query("""
        SELECT p.product_category AS categoria,
               AVG(r.rating)      AS nota_media
        FROM olist.order_reviews r
        JOIN olist.orders o      ON r.order_id  = o.order_id
        JOIN olist.order_items oi ON o.order_id  = oi.order_id
        JOIN olist.products p    ON oi.product_id = p.product_id
        WHERE p.product_category IS NOT NULL
        GROUP BY p.product_category
        HAVING COUNT(*) >= 50
        ORDER BY nota_media DESC
        LIMIT 15
    """)
    if not df_cat_nota.empty:
        fig = px.bar(
            df_cat_nota, x="nota_media", y="categoria",
            orientation="h",
            title="Nota Média por Categoria (mín. 50 avaliações)",
            labels={"nota_media": "Nota Média", "categoria": "Categoria"},
            template=_template(),
        )
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    # ── Tempo de entrega × nota ──────────────────────────────────
    df_tn = run_query("""
        SELECT
            CASE
                WHEN EXTRACT(EPOCH FROM (o.delivered_customer_date - o.purchase_timestamp)) / 86400 <= 7  THEN '0-7 dias'
                WHEN EXTRACT(EPOCH FROM (o.delivered_customer_date - o.purchase_timestamp)) / 86400 <= 14 THEN '8-14 dias'
                WHEN EXTRACT(EPOCH FROM (o.delivered_customer_date - o.purchase_timestamp)) / 86400 <= 21 THEN '15-21 dias'
                WHEN EXTRACT(EPOCH FROM (o.delivered_customer_date - o.purchase_timestamp)) / 86400 <= 30 THEN '22-30 dias'
                ELSE '30+ dias'
            END AS faixa_entrega,
            AVG(r.rating) AS nota_media
        FROM olist.order_reviews r
        JOIN olist.orders o ON r.order_id = o.order_id
        WHERE o.status = 'delivered'
          AND o.delivered_customer_date IS NOT NULL
        GROUP BY faixa_entrega
        ORDER BY MIN(EXTRACT(EPOCH FROM (o.delivered_customer_date - o.purchase_timestamp)) / 86400)
    """)
    if not df_tn.empty:
        fig = px.bar(
            df_tn, x="faixa_entrega", y="nota_media",
            title="Nota Média por Faixa de Tempo de Entrega",
            labels={"faixa_entrega": "Tempo de Entrega", "nota_media": "Nota Média"},
            template=_template(),
            text="nota_media",
        )
        fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig.update_yaxes(range=[0, 5])
        st.plotly_chart(fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════════
# 5. VENDEDORES
# ═════════════════════════════════════════════════════════════════
def render_vendedores():
    st.title("🏪 Dashboard de Vendedores")

    # ── KPIs ─────────────────────────────────────────────────────
    df_total = run_query(
        "SELECT COUNT(DISTINCT seller_id) AS total FROM olist.sellers"
    )
    df_receita = run_query("""
        SELECT seller_id, SUM(price) AS receita, COUNT(*) AS vendas
        FROM olist.order_items
        GROUP BY seller_id
    """)
    df_top_uf = run_query("""
        SELECT state, COUNT(*) AS total
        FROM olist.sellers
        GROUP BY state
        ORDER BY total DESC
        LIMIT 1
    """)

    total_vendedores = int(df_total["total"].iloc[0] or 0)
    receita_media = float(df_receita["receita"].mean()) if not df_receita.empty else 0
    vendas_media  = float(df_receita["vendas"].mean()) if not df_receita.empty else 0
    top_estado    = df_top_uf["state"].iloc[0] if not df_top_uf.empty else "N/A"

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total de Vendedores", f"{total_vendedores:,}")
    with c2:
        st.metric("Receita Média / Vendedor", f"R$ {receita_media:,.2f}")
    with c3:
        st.metric("Vendas Médias / Vendedor", f"{vendas_media:,.1f}")
    with c4:
        st.metric("Top Estado", top_estado)

    st.divider()

    # ── Top 10 vendedores por receita ────────────────────────────
    df_top = run_query("""
        SELECT seller_id, SUM(price) AS receita
        FROM olist.order_items
        GROUP BY seller_id
        ORDER BY receita DESC
        LIMIT 10
    """)
    if not df_top.empty:
        df_top["seller_short"] = df_top["seller_id"].str[:8] + "…"
        fig = px.bar(
            df_top, x="receita", y="seller_short",
            orientation="h",
            title="Top 10 Vendedores por Receita",
            labels={"receita": "Receita (R$)", "seller_short": "Vendedor"},
            template=_template(),
        )
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    # ── Top 10 / Bottom 10 por nota ──────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        df_best = run_query("""
            SELECT oi.seller_id,
                   AVG(r.rating) AS nota_media
            FROM olist.order_reviews r
            JOIN olist.orders o      ON r.order_id  = o.order_id
            JOIN olist.order_items oi ON o.order_id  = oi.order_id
            GROUP BY oi.seller_id
            HAVING COUNT(*) >= 30
            ORDER BY nota_media DESC
            LIMIT 10
        """)
        if not df_best.empty:
            df_best["seller_short"] = df_best["seller_id"].str[:8] + "…"
            fig = px.bar(
                df_best, x="nota_media", y="seller_short",
                orientation="h",
                title="Top 10 Vendedores por Nota (mín. 30 avaliações)",
                labels={"nota_media": "Nota Média", "seller_short": "Vendedor"},
                template=_template(),
                color="nota_media",
                color_continuous_scale="Greens",
            )
            fig.update_layout(yaxis=dict(autorange="reversed"), coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        df_worst = run_query("""
            SELECT oi.seller_id,
                   AVG(r.rating) AS nota_media
            FROM olist.order_reviews r
            JOIN olist.orders o      ON r.order_id  = o.order_id
            JOIN olist.order_items oi ON o.order_id  = oi.order_id
            GROUP BY oi.seller_id
            HAVING COUNT(*) >= 30
            ORDER BY nota_media ASC
            LIMIT 10
        """)
        if not df_worst.empty:
            df_worst["seller_short"] = df_worst["seller_id"].str[:8] + "…"
            fig = px.bar(
                df_worst, x="nota_media", y="seller_short",
                orientation="h",
                title="Bottom 10 Vendedores por Nota (mín. 30 avaliações)",
                labels={"nota_media": "Nota Média", "seller_short": "Vendedor"},
                template=_template(),
                color="nota_media",
                color_continuous_scale="Reds_r",
            )
            fig.update_layout(yaxis=dict(autorange="reversed"), coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)


# ── Roteamento ───────────────────────────────────────────────────
match category_filter:
    case "📊 Vendas & Receita":
        render_vendas_receita()
    case "🛒 Pedidos":
        render_pedidos()
    case "🚚 Logística & Entregas":
        render_logistica()
    case "⭐ Satisfação do Cliente":
        render_satisfacao()
    case "🏪 Vendedores":
        render_vendedores()
