# streamlit_app1.py
# ------------------------------------------------------------
# Dashboard de Vendas - Streamlit (gráficos empilhados, um abaixo do outro)
# Leitura: vendas_dashboard.csv (delimitador ;)
# Gráficos e KPIs:
#   a) Vendas por cliente (faturamento)
#   b) Vendas por vendedor (faturamento)
#   c) Produtos (categorias) que mais vendem (quantidade)
#   d) Meses do ano x quantidade de vendas
#   e) Top 5 clientes (faturamento) + tabela
#   f) Top 5 vendedores (faturamento) + tabela
#   g) Lojas que mais vendem (faturamento)
#   i) KPIs (faturamento, ticket médio), filtros por estado/município/período,
#      gráficos por categoria (pizza) e por vendedor (barras)
# ------------------------------------------------------------

import os
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="Dashboard de Vendas",
    page_icon="📊",
    layout="wide"
)

# =========================
#  Utilidades
# =========================
@st.cache_data
def load_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, sep=";", encoding="utf-8")
    # Datas
    df["data_venda"] = pd.to_datetime(df["data_venda"], errors="coerce")
    if "data_entrega_prevista" in df.columns:
        df["data_entrega_prevista"] = pd.to_datetime(df["data_entrega_prevista"], errors="coerce")

    # Números (garante ponto decimal)
    for col in ["preco_unitario", "preco_total"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", ".", regex=False)
                .astype(float)
            )

    if "quantidade_vendida" in df.columns:
        df["quantidade_vendida"] = pd.to_numeric(df["quantidade_vendida"], errors="coerce").fillna(0).astype(int)

    # Campos auxiliares
    df["ano"] = df["data_venda"].dt.year
    df["mes"] = df["data_venda"].dt.month
    df["mes_nome"] = df["data_venda"].dt.strftime("%b")  # Jan, Fev, ...
    return df

def kpi_card(label, value, help_text=None):
    st.metric(label, value)
    if help_text:
        st.caption(help_text)

def fmt_currency(x: float) -> str:
    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# =========================
#  Entrada do arquivo
# =========================
st.title("📊 Dashboard de Vendas")
st.write("App: **streamlit_app1.py** — lendo **vendas_dashboard.csv** (delimitador `;`).")

default_path = "vendas_dashboard.csv"
csv_path = st.text_input("Caminho do CSV (use o arquivo padrão se estiver na mesma pasta):", value=default_path)

uploaded = st.file_uploader("Ou envie o arquivo CSV aqui (usa delimitador ;) :", type=["csv"])
if uploaded is not None:
    df_tmp = pd.read_csv(uploaded, sep=";", encoding="utf-8")
    temp_name = "_uploaded_temp.csv"
    df_tmp.to_csv(temp_name, sep=";", index=False, encoding="utf-8")
    csv_path = temp_name

# Verifica existência
if not os.path.exists(csv_path):
    st.error(f"Arquivo não encontrado: **{csv_path}**. Coloque o `vendas_dashboard.csv` na mesma pasta ou selecione um arquivo.")
    st.stop()

# Carrega dados
df = load_data(csv_path)

# =========================
#  Filtros (Estado / Município / Período / Loja / Categoria / Vendedor)
# =========================
with st.expander("🔎 Filtros"):
    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])

    with col_f1:
        estados = ["(Todos)"] + sorted(df["estado"].dropna().unique().tolist()) if "estado" in df.columns else ["(Todos)"]
        estado_sel = st.selectbox("Estado", estados, index=0)

        # Municípios dependem do estado (quando escolhido)
        if estado_sel != "(Todos)" and "estado" in df.columns:
            municipios_opts = ["(Todos)"] + sorted(df.loc[df["estado"] == estado_sel, "municipio"].dropna().unique().tolist())
        else:
            municipios_opts = ["(Todos)"] + sorted(df["municipio"].dropna().unique().tolist())
        municipio_sel = st.selectbox("Município", municipios_opts, index=0)

    with col_f2:
        lojas_opts = ["(Todas)"] + sorted(df["loja"].dropna().unique().tolist())
        loja_sel = st.selectbox("Loja", lojas_opts, index=0)

        categorias_opts = ["(Todas)"] + sorted(df["categoria_produto"].dropna().unique().tolist())
        categoria_sel = st.selectbox("Categoria", categorias_opts, index=0)

    with col_f3:
        vendedores_opts = ["(Todos)"] + sorted(df["nome_vendedor"].dropna().unique().tolist())
        vendedor_sel = st.selectbox("Vendedor", vendedores_opts, index=0)

        # Período
        min_date = df["data_venda"].min()
        max_date = df["data_venda"].max()
        data_ini, data_fim = st.date_input(
            "Período (Data da Venda)",
            value=(min_date.date() if pd.notnull(min_date) else None,
                   max_date.date() if pd.notnull(max_date) else None)
        )

# Aplica filtros
filtered = df.copy()
if estado_sel != "(Todos)" and "estado" in filtered.columns:
    filtered = filtered.loc[filtered["estado"] == estado_sel]
if municipio_sel != "(Todos)":
    filtered = filtered.loc[filtered["municipio"] == municipio_sel]
if loja_sel != "(Todas)":
    filtered = filtered.loc[filtered["loja"] == loja_sel]
if categoria_sel != "(Todas)":
    filtered = filtered.loc[filtered["categoria_produto"] == categoria_sel]
if vendedor_sel != "(Todos)":
    filtered = filtered.loc[filtered["nome_vendedor"] == vendedor_sel]

# Período
try:
    filtered = filtered.loc[
        (filtered["data_venda"] >= pd.to_datetime(data_ini)) &
        (filtered["data_venda"] <= pd.to_datetime(data_fim))
    ]
except Exception:
    pass

# =========================
#  KPIs
# =========================
st.header("📈 KPIs")

col_k1, col_k2, col_k3, col_k4 = st.columns(4)

faturamento = float(filtered["preco_total"].sum()) if not filtered.empty else 0.0
num_vendas = int(filtered.shape[0])
ticket_medio = (faturamento / num_vendas) if num_vendas > 0 else 0.0
qtd_itens = int(filtered["quantidade_vendida"].sum()) if "quantidade_vendida" in filtered.columns else 0

with col_k1:
    kpi_card("Faturamento (Filtro)", fmt_currency(faturamento))
with col_k2:
    kpi_card("Nº de Vendas", f"{num_vendas}")
with col_k3:
    kpi_card("Ticket Médio", fmt_currency(ticket_medio), help_text="Faturamento / nº de vendas")
with col_k4:
    kpi_card("Quantidade de Itens", f"{qtd_itens}")

st.divider()

# ===========================================
#  a) Vendas por Cliente (faturamento)
# ===========================================
st.subheader("a) Vendas por Cliente (Faturamento)")
if filtered.empty:
    st.info("Sem dados para os filtros selecionados.")
else:
    clientes = (
        filtered.groupby("nome_cliente", as_index=False)["preco_total"]
        .sum()
        .sort_values("preco_total", ascending=False)
    )
    fig_a = px.bar(
        clientes, x="nome_cliente", y="preco_total",
        title="Faturamento por Cliente",
        labels={"preco_total": "Faturamento (R$)", "nome_cliente": "Cliente"}
    )
    fig_a.update_layout(xaxis_tickangle=-45, yaxis_tickformat=",")
    st.plotly_chart(fig_a, use_container_width=True, key="chart_a_clientes")

# ===========================================
#  b) Vendas por Vendedor (faturamento)
# ===========================================
st.subheader("b) Vendas por Vendedor (Faturamento)")
if filtered.empty:
    st.info("Sem dados.")
else:
    vend = (
        filtered.groupby("nome_vendedor", as_index=False)["preco_total"]
        .sum()
        .sort_values("preco_total", ascending=False)
    )
    fig_b = px.bar(
        vend, x="nome_vendedor", y="preco_total",
        title="Faturamento por Vendedor",
        labels={"preco_total": "Faturamento (R$)", "nome_vendedor": "Vendedor"}
    )
    fig_b.update_layout(xaxis_tickangle=-45, yaxis_tickformat=",")
    st.plotly_chart(fig_b, use_container_width=True, key="chart_b_vendedores")

# ===========================================
#  c) Produtos (categorias) que mais vendem (quantidade)
# ===========================================
st.subheader("c) Categorias com Maior Quantidade Vendida")
if filtered.empty:
    st.info("Sem dados.")
else:
    cat_qtd = (
        filtered.groupby("categoria_produto", as_index=False)["quantidade_vendida"]
        .sum()
        .sort_values("quantidade_vendida", ascending=False)
    )
    fig_c = px.bar(
        cat_qtd, x="categoria_produto", y="quantidade_vendida",
        title="Quantidade Vendida por Categoria",
        labels={"quantidade_vendida": "Quantidade", "categoria_produto": "Categoria"}
    )
    fig_c.update_layout(xaxis_tickangle=-30)
    st.plotly_chart(fig_c, use_container_width=True, key="chart_c_categorias_qtd")

# ===========================================
#  d) Meses do ano x quantidade de vendas
# ===========================================
st.subheader("d) Quantidade de Vendas por Mês")
if filtered.empty:
    st.info("Sem dados.")
else:
    por_mes = (
        filtered.assign(mes_ord=filtered["data_venda"].dt.month)
                .groupby(["ano", "mes_ord"], as_index=False)
                .agg(qtd_vendas=("id_venda", "count"))
    )
    por_mes["mes_label"] = pd.to_datetime(por_mes["mes_ord"], format="%m").dt.strftime("%b")
    # Ordena por mês
    por_mes = por_mes.sort_values(["ano", "mes_ord"])
    fig_d = px.line(
        por_mes, x="mes_label", y="qtd_vendas", color="ano", markers=True,
        title="Quantidade de Vendas por Mês",
        labels={"mes_label": "Mês", "qtd_vendas": "Qtd. Vendas", "ano": "Ano"}
    )
    st.plotly_chart(fig_d, use_container_width=True, key="chart_d_meses")

# ===========================================
#  e) Top 5 clientes (faturamento)
# ===========================================
st.subheader("e) Top 5 Clientes por Faturamento")
if filtered.empty:
    st.info("Sem dados.")
else:
    top_clientes = (
        filtered.groupby("nome_cliente", as_index=False)["preco_total"]
        .sum()
        .sort_values("preco_total", ascending=False)
        .head(5)
    )
    fig_e = px.bar(
        top_clientes, x="nome_cliente", y="preco_total",
        title="Top 5 Clientes por Faturamento",
        labels={"preco_total": "Faturamento (R$)", "nome_cliente": "Cliente"}
    )
    fig_e.update_layout(xaxis_tickangle=-45, yaxis_tickformat=",")
    st.plotly_chart(fig_e, use_container_width=True, key="chart_e_top_clientes")
    st.dataframe(top_clientes.rename(columns={"preco_total": "Faturamento (R$)"}), use_container_width=True)

# ===========================================
#  f) Top 5 vendedores (faturamento)
# ===========================================
st.subheader("f) Top 5 Vendedores por Faturamento")
if filtered.empty:
    st.info("Sem dados.")
else:
    top_vendedores = (
        filtered.groupby("nome_vendedor", as_index=False)["preco_total"]
        .sum()
        .sort_values("preco_total", ascending=False)
        .head(5)
    )
    fig_f = px.bar(
        top_vendedores, x="nome_vendedor", y="preco_total",
        title="Top 5 Vendedores por Faturamento",
        labels={"preco_total": "Faturamento (R$)", "nome_vendedor": "Vendedor"}
    )
    fig_f.update_layout(xaxis_tickangle=-45, yaxis_tickformat=",")
    st.plotly_chart(fig_f, use_container_width=True, key="chart_f_top_vendedores")
    st.dataframe(top_vendedores.rename(columns={"preco_total": "Faturamento (R$)"}), use_container_width=True)

# ===========================================
#  g) Lojas que mais vendem (faturamento)
# ===========================================
st.subheader("g) Faturamento por Loja")
if filtered.empty:
    st.info("Sem dados.")
else:
    lojas_fat = (
        filtered.groupby("loja", as_index=False)["preco_total"]
        .sum()
        .sort_values("preco_total", ascending=False)
    )
    fig_g = px.bar(
        lojas_fat, x="loja", y="preco_total",
        title="Faturamento por Loja",
        labels={"preco_total": "Faturamento (R$)", "loja": "Loja"}
    )
    fig_g.update_layout(yaxis_tickformat=",")
    st.plotly_chart(fig_g, use_container_width=True, key="chart_g_lojas")

# ===========================================
#  i) Extras: Por Categoria (pizza) e Por Vendedor (barras)
# ===========================================
st.subheader("i) Faturamento por Categoria (Pizza) e por Vendedor (Barras)")
if filtered.empty:
    st.info("Sem dados.")
else:
    # Pizza por categoria
    por_cat = (
        filtered.groupby("categoria_produto", as_index=False)["preco_total"]
        .sum()
        .sort_values("preco_total", ascending=False)
    )
    fig_i1 = px.pie(
        por_cat, names="categoria_produto", values="preco_total",
        title="Faturamento por Categoria"
    )
    st.plotly_chart(fig_i1, use_container_width=True, key="chart_i1_categoria_pie")

    # Barras por vendedor
    por_vend = (
        filtered.groupby("nome_vendedor", as_index=False)["preco_total"]
        .sum()
        .sort_values("preco_total", ascending=False)
    )
    fig_i2 = px.bar(
        por_vend, x="nome_vendedor", y="preco_total",
        title="Faturamento por Vendedor",
        labels={"preco_total": "Faturamento (R$)", "nome_vendedor": "Vendedor"}
    )
    fig_i2.update_layout(xaxis_tickangle=-45, yaxis_tickformat=",")
    st.plotly_chart(fig_i2, use_container_width=True, key="chart_i2_vendedor_bar")

st.divider()

# =========================
#  Tabela de dados / Download
# =========================
st.subheader("📋 Dados Filtrados")
st.dataframe(
    filtered.sort_values("data_venda", ascending=False),
    use_container_width=True,
    height=420
)

csv_dl = filtered.to_csv(index=False, sep=";").encode("utf-8")
st.download_button(
    label="⬇️ Baixar CSV (dados filtrados)",
    data=csv_dl,
    file_name="vendas_filtrado.csv",
    mime="text/csv"
)

st.caption("Execute com:  streamlit run streamlit_app1.py")
