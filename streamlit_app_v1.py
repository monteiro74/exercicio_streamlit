# streamlit_app1_light_fix.py
# ------------------------------------------------------------
# Dashboard de Vendas (dataset fixo vendas_dashboard.csv)
# Usuário não pode trocar o arquivo CSV.
# ------------------------------------------------------------

import os
import math
import pandas as pd
import streamlit as st
import plotly.express as px

# Folium é opcional
try:
    import folium
    from streamlit_folium import st_folium
    HAS_FOLIUM = True
except Exception:
    HAS_FOLIUM = False

st.set_page_config(page_title="Dashboard de Vendas", page_icon="📊", layout="wide")

# ====== Funções util ======
@st.cache_data
def load_data() -> pd.DataFrame:
    csv_path = "vendas_dashboard.csv"
    if not os.path.exists(csv_path):
        st.error("⚠️ Arquivo vendas_dashboard.csv não encontrado na pasta do aplicativo.")
        st.stop()

    df = pd.read_csv(csv_path, sep=";", encoding="utf-8")
    df["data_venda"] = pd.to_datetime(df["data_venda"], errors="coerce")
    if "data_entrega_prevista" in df.columns:
        df["data_entrega_prevista"] = pd.to_datetime(df["data_entrega_prevista"], errors="coerce")

    for col in ["preco_unitario", "preco_total"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(",", ".", regex=False).astype(float)
    if "quantidade_vendida" in df.columns:
        df["quantidade_vendida"] = pd.to_numeric(df["quantidade_vendida"], errors="coerce").fillna(0).astype(int)

    df["ano"] = df["data_venda"].dt.year
    df["mes"] = df["data_venda"].dt.month
    df["dia"] = df["data_venda"].dt.date
    df["mes_nome"] = df["data_venda"].dt.strftime("%b")
    return df

def fmt_currency(x: float) -> str:
    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def safe_pct(a, b):
    return 0.0 if b == 0 else round(100.0 * a / b, 2)

# Coordenadas aproximadas
CITY_LATLON = {
    "São Paulo": (-23.5505, -46.6333), "Campinas": (-22.9056, -47.0608),
    "Rio de Janeiro": (-22.9068, -43.1729), "Belo Horizonte": (-19.9167, -43.9345),
    "Cuiabá": (-15.6010, -56.0974), "Curitiba": (-25.4284, -49.2733),
    "Porto Alegre": (-30.0346, -51.2177), "Brasília": (-15.7939, -47.8828),
    "Salvador": (-12.9777, -38.5016), "Fortaleza": (-3.7319, -38.5267),
}

# ====== Título ======
st.title("📊 Dashboard de Vendas — Dataset Fixo")
st.caption("Base de dados: **vendas_dashboard.csv** (não editável)")

df = load_data()

# ====== Filtros ======
with st.expander("🔎 Filtros"):
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        estados = ["(Todos)"] + sorted(df["estado"].dropna().unique().tolist())
        estado_sel = st.selectbox("Estado", estados, index=0)
        if estado_sel != "(Todos)":
            municipios_opts = ["(Todos)"] + sorted(df.loc[df["estado"] == estado_sel, "municipio"].dropna().unique().tolist())
        else:
            municipios_opts = ["(Todos)"] + sorted(df["municipio"].dropna().unique().tolist())
        municipio_sel = st.selectbox("Município", municipios_opts, index=0)
    with c2:
        lojas_opts = ["(Todas)"] + sorted(df["loja"].dropna().unique().tolist())
        loja_sel = st.selectbox("Loja", lojas_opts, index=0)
        categorias_opts = ["(Todas)"] + sorted(df["categoria_produto"].dropna().unique().tolist())
        categoria_sel = st.selectbox("Categoria", categorias_opts, index=0)
    with c3:
        vendedores_opts = ["(Todos)"] + sorted(df["nome_vendedor"].dropna().unique().tolist())
        vendedor_sel = st.selectbox("Vendedor", vendedores_opts, index=0)
        min_date, max_date = df["data_venda"].min(), df["data_venda"].max()
        data_ini, data_fim = st.date_input("Período (Data da Venda)", (min_date.date(), max_date.date()))

filtered = df.copy()
if estado_sel != "(Todos)": filtered = filtered[filtered["estado"] == estado_sel]
if municipio_sel != "(Todos)": filtered = filtered[filtered["municipio"] == municipio_sel]
if loja_sel != "(Todas)": filtered = filtered[filtered["loja"] == loja_sel]
if categoria_sel != "(Todas)": filtered = filtered[filtered["categoria_produto"] == categoria_sel]
if vendedor_sel != "(Todos)": filtered = filtered[filtered["nome_vendedor"] == vendedor_sel]
filtered = filtered[
    (filtered["data_venda"] >= pd.to_datetime(data_ini)) &
    (filtered["data_venda"] <= pd.to_datetime(data_fim))
]

# ====== KPIs ======
st.header("📈 KPIs")

fat = filtered["preco_total"].sum() if not filtered.empty else 0.0
n_vendas = len(filtered)
ticket = fat / n_vendas if n_vendas > 0 else 0
parc_sim = (filtered["venda_parcelada"].str.lower() == "sim").sum() if "venda_parcelada" in filtered.columns else 0
pct_parc = safe_pct(parc_sim, n_vendas)
clientes_unicos = filtered["nome_cliente"].nunique()
itens = filtered["quantidade_vendida"].sum()
itens_por_venda = itens / n_vendas if n_vendas > 0 else 0

if "estado" in filtered.columns and not filtered.empty:
    por_estado = filtered.groupby("estado", as_index=False)["preco_total"].sum().sort_values("preco_total", ascending=False)
    estado_lider = por_estado.iloc[0]["estado"]
    part_lider = safe_pct(por_estado.iloc[0]["preco_total"], fat)
else:
    estado_lider, part_lider = "—", 0.0

k1, k2, k3, k4, k5, k6 = st.columns(6)
with k1: st.metric("Faturamento", fmt_currency(fat))
with k2: st.metric("Nº de Vendas", f"{n_vendas}")
with k3: st.metric("Ticket Médio", fmt_currency(ticket))
with k4: st.metric("% Parceladas", f"{pct_parc:.2f}%")
with k5: st.metric("Estado Líder", f"{estado_lider} — {part_lider:.2f}%")
with k6: st.metric("Clientes Únicos", f"{clientes_unicos}")

st.divider()

# ====== Gráficos ======
st.subheader("Vendas por Cliente")
if not filtered.empty:
    fig1 = px.bar(filtered.groupby("nome_cliente", as_index=False)["preco_total"].sum().sort_values("preco_total", ascending=False),
                  x="nome_cliente", y="preco_total", labels={"preco_total": "Faturamento (R$)"})
    st.plotly_chart(fig1, use_container_width=True, key="fix_clientes")

st.subheader("Vendas por Vendedor")
if not filtered.empty:
    fig2 = px.bar(filtered.groupby("nome_vendedor", as_index=False)["preco_total"].sum().sort_values("preco_total", ascending=False),
                  x="nome_vendedor", y="preco_total", labels={"preco_total": "Faturamento (R$)"})
    st.plotly_chart(fig2, use_container_width=True, key="fix_vendedores")

st.subheader("Top 5 Clientes")
if not filtered.empty:
    top5 = filtered.groupby("nome_cliente", as_index=False)["preco_total"].sum().sort_values("preco_total", ascending=False).head(5)
    fig3 = px.bar(top5, x="nome_cliente", y="preco_total", labels={"preco_total": "Faturamento (R$)"})
    st.plotly_chart(fig3, use_container_width=True, key="fix_top5")

st.subheader("Faturamento por Loja")
if not filtered.empty:
    fig4 = px.bar(filtered.groupby("loja", as_index=False)["preco_total"].sum(),
                  x="loja", y="preco_total", labels={"preco_total": "Faturamento (R$)"})
    st.plotly_chart(fig4, use_container_width=True, key="fix_lojas")

# ====== Indicadores Categoria Cliente ======
if "categoria_cliente" in filtered.columns:
    st.subheader("👥 Indicadores por Categoria de Cliente")
    df_cat = filtered.groupby("categoria_cliente", as_index=False).agg(
        vendas=("id_venda", "count"),
        faturamento=("preco_total", "sum")
    )
    fig5 = px.bar(df_cat, x="categoria_cliente", y="faturamento", text_auto=True)
    st.plotly_chart(fig5, use_container_width=True, key="fix_categoria")

# ====== Mapa (Plotly) ======
st.subheader("🗺️ Mapa (Plotly) — Faturamento por Cidade")
agg_city = filtered.groupby(["estado", "municipio"], as_index=False)["preco_total"].sum()
agg_city["lat"] = agg_city["municipio"].map(lambda m: CITY_LATLON.get(m, (None, None))[0])
agg_city["lon"] = agg_city["municipio"].map(lambda m: CITY_LATLON.get(m, (None, None))[1])
agg_city = agg_city.dropna(subset=["lat", "lon"])

if not agg_city.empty:
    fig6 = px.scatter_mapbox(
        agg_city, lat="lat", lon="lon", size="preco_total",
        color="estado", hover_name="municipio",
        hover_data={"preco_total": ":.2f"}, zoom=3.5,
        title="Faturamento por Cidade"
    )
    fig6.update_layout(mapbox_style="open-street-map", margin=dict(l=0, r=0, t=50, b=0))
    st.plotly_chart(fig6, use_container_width=True, key="fix_map")

st.divider()
st.caption("Dataset fixo: vendas_dashboard.csv | Comando: streamlit run streamlit_app1_light_fix.py")
