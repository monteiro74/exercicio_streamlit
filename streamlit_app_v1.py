# streamlit_app1_light.py
# ------------------------------------------------------------
# Dashboard de Vendas (tema padrão, sem dark)
# Lê: vendas_dashboard.csv (delimitador ;)
# Recursos: KPIs extras, indicadores por categoria do cliente,
# gráficos empilhados (um abaixo do outro), mapas Plotly e Folium (opcional)
# ------------------------------------------------------------

import os
import math
import pandas as pd
import streamlit as st
import plotly.express as px

# Folium é opcional (instale: pip install folium streamlit-folium)
try:
    import folium
    from streamlit_folium import st_folium
    HAS_FOLIUM = True
except Exception:
    HAS_FOLIUM = False

st.set_page_config(page_title="Dashboard de Vendas", page_icon="📊", layout="wide")

# ====== Funções util ======
@st.cache_data
def load_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, sep=";", encoding="utf-8")
    # Ajustes de tipo
    df["data_venda"] = pd.to_datetime(df["data_venda"], errors="coerce")
    if "data_entrega_prevista" in df.columns:
        df["data_entrega_prevista"] = pd.to_datetime(df["data_entrega_prevista"], errors="coerce")

    for col in ["preco_unitario", "preco_total"]:
        if col in df.columns:
            df[col] = (
                df[col].astype(str).str.replace(",", ".", regex=False).astype(float)
            )
    if "quantidade_vendida" in df.columns:
        df["quantidade_vendida"] = pd.to_numeric(df["quantidade_vendida"], errors="coerce").fillna(0).astype(int)

    # Auxiliares
    df["ano"] = df["data_venda"].dt.year
    df["mes"] = df["data_venda"].dt.month
    df["dia"] = df["data_venda"].dt.date
    df["mes_nome"] = df["data_venda"].dt.strftime("%b")
    return df

def fmt_currency(x: float) -> str:
    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def safe_pct(a, b):
    return 0.0 if b == 0 else round(100.0 * a / b, 2)

# Geocódigos aproximados (lat, lon) para cidades usadas no dataset
CITY_LATLON = {
    # SP
    "São Paulo": (-23.5505, -46.6333), "Campinas": (-22.9056, -47.0608),
    "Sorocaba": (-23.5015, -47.4526), "Ribeirão Preto": (-21.1775, -47.8103),
    "São José dos Campos": (-23.2237, -45.9009),
    # RJ
    "Rio de Janeiro": (-22.9068, -43.1729), "Niterói": (-22.8832, -43.1034),
    "Campos dos Goytacazes": (-21.7622, -41.3181), "Volta Redonda": (-22.5200, -44.0996),
    # MG
    "Belo Horizonte": (-19.9167, -43.9345), "Uberlândia": (-18.9113, -48.2622),
    "Contagem": (-19.9317, -44.0533), "Juiz de Fora": (-21.7619, -43.3496),
    # RS
    "Porto Alegre": (-30.0346, -51.2177), "Caxias do Sul": (-29.1678, -51.1794),
    "Pelotas": (-31.7654, -52.3371), "Santa Maria": (-29.6842, -53.8069),
    # SC
    "Florianópolis": (-27.5949, -48.5482), "Joinville": (-26.3045, -48.8487),
    "Blumenau": (-26.9173, -49.0661), "Chapecó": (-27.1004, -52.6152),
    # PR
    "Curitiba": (-25.4284, -49.2733), "Londrina": (-23.3045, -51.1696),
    "Maringá": (-23.4205, -51.9333), "Cascavel": (-24.9555, -53.4552),
    # MT
    "Cuiabá": (-15.6010, -56.0974), "Várzea Grande": (-15.6467, -56.1322),
    "Rondonópolis": (-16.4708, -54.6356), "Sinop": (-11.8642, -55.5030),
    "Tangará da Serra": (-14.6225, -57.4850), "Lucas do Rio Verde": (-13.0559, -55.9199),
    "Sorriso": (-12.5420, -55.7211), "Barra do Garças": (-15.8931, -52.2569),
    # MS
    "Campo Grande": (-20.4697, -54.6201), "Dourados": (-22.2211, -54.8056),
    "Três Lagoas": (-20.7849, -51.7004), "Corumbá": (-19.0077, -57.6510),
    # PA
    "Belém": (-1.4558, -48.4902), "Ananindeua": (-1.3650, -48.3720),
    "Marabá": (-5.3803, -49.1327), "Santarém": (-2.4390, -54.7009),
    # AM
    "Manaus": (-3.1190, -60.0217), "Itacoatiara": (-3.1386, -58.4449),
    "Parintins": (-2.6283, -56.7358),
    # GO
    "Goiânia": (-16.6869, -49.2648), "Anápolis": (-16.3281, -48.9534),
    "Aparecida de Goiânia": (-16.8193, -49.2473),
    # DF
    "Brasília": (-15.7939, -47.8828),
    # ES
    "Vitória": (-20.3155, -40.3128), "Vila Velha": (-20.3361, -40.2939), "Serra": (-20.1286, -40.3074),
    # RO
    "Porto Velho": (-8.7619, -63.9039), "Ji-Paraná": (-10.8777, -61.9321), "Ariquemes": (-9.9134, -63.0405),
    # TO
    "Palmas": (-10.1842, -48.3336), "Araguaína": (-7.1911, -48.2077), "Gurupi": (-11.7292, -49.0689),
    # MA
    "São Luís": (-2.5387, -44.2825), "Imperatriz": (-5.5185, -47.4784), "Caxias": (-4.8650, -43.3617),
    # PI
    "Teresina": (-5.0919, -42.8034), "Parnaíba": (-2.9059, -41.7760), "Picos": (-7.0768, -41.4679),
    # BA
    "Salvador": (-12.9777, -38.5016), "Feira de Santana": (-12.2664, -38.9663),
    "Vitória da Conquista": (-14.8615, -40.8442), "Ilhéus": (-14.7935, -39.0460),
    # PE
    "Recife": (-8.0476, -34.8770), "Olinda": (-7.9993, -34.8450), "Caruaru": (-8.2835, -35.9759), "Petrolina": (-9.3891, -40.5033),
    # CE
    "Fortaleza": (-3.7319, -38.5267), "Caucaia": (-3.7361, -38.6535), "Juazeiro do Norte": (-7.2131, -39.3155),
    "Sobral": (-3.6891, -40.3482),
}

# ====== Header / Entrada ======
st.title("📊 Dashboard de Vendas")
st.write("Lendo **vendas_dashboard.csv** (delimitador `;`).")

default_path = "vendas_dashboard.csv"
csv_path = st.text_input("Caminho do CSV:", value=default_path)

uploaded = st.file_uploader("Ou envie o arquivo CSV aqui:", type=["csv"])
if uploaded is not None:
    df_tmp = pd.read_csv(uploaded, sep=";", encoding="utf-8")
    tmp_name = "_uploaded_temp_light.csv"
    df_tmp.to_csv(tmp_name, sep=";", index=False, encoding="utf-8")
    csv_path = tmp_name

if not os.path.exists(csv_path):
    st.error(f"Arquivo não encontrado: {csv_path}")
    st.stop()

df = load_data(csv_path)

# ====== Filtros ======
with st.expander("🔎 Filtros"):
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        estados = ["(Todos)"] + sorted(df["estado"].dropna().unique().tolist()) if "estado" in df.columns else ["(Todos)"]
        estado_sel = st.selectbox("Estado", estados, index=0)
        if estado_sel != "(Todos)" and "estado" in df.columns:
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
        min_date = df["data_venda"].min()
        max_date = df["data_venda"].max()
        data_ini, data_fim = st.date_input(
            "Período (Data da Venda)",
            value=(min_date.date() if pd.notnull(min_date) else None,
                   max_date.date() if pd.notnull(max_date) else None)
        )

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
try:
    filtered = filtered.loc[
        (filtered["data_venda"] >= pd.to_datetime(data_ini)) &
        (filtered["data_venda"] <= pd.to_datetime(data_fim))
    ]
except Exception:
    pass

# ====== KPIs ======
st.header("📈 KPIs")

fat = float(filtered["preco_total"].sum()) if not filtered.empty else 0.0
n_vendas = int(filtered.shape[0])
ticket = (fat / n_vendas) if n_vendas > 0 else 0.0
itens = int(filtered["quantidade_vendida"].sum()) if "quantidade_vendida" in filtered.columns else 0

# % parceladas
if "venda_parcelada" in filtered.columns:
    parc_sim = int((filtered["venda_parcelada"].astype(str).str.lower() == "sim").sum())
    pct_parc = safe_pct(parc_sim, n_vendas)
else:
    parc_sim, pct_parc = 0, 0.0

# participação por estado (estado líder)
if "estado" in filtered.columns and not filtered.empty:
    por_estado = filtered.groupby("estado", as_index=False)["preco_total"].sum().sort_values("preco_total", ascending=False)
    estado_lider = por_estado.iloc[0]["estado"]
    fat_lider = por_estado.iloc[0]["preco_total"]
    part_lider = safe_pct(fat_lider, fat)
else:
    estado_lider, part_lider = "—", 0.0

# clientes únicos e itens/venda
clientes_unicos = filtered["nome_cliente"].nunique() if "nome_cliente" in filtered.columns else 0
itens_por_venda = (itens / n_vendas) if n_vendas > 0 else 0.0

k1, k2, k3, k4, k5, k6 = st.columns(6)
with k1: st.metric("Faturamento (Filtro)", fmt_currency(fat))
with k2: st.metric("Nº de Vendas", f"{n_vendas}")
with k3: st.metric("Ticket Médio", fmt_currency(ticket))
with k4: st.metric("% Vendas Parceladas", f"{pct_parc:.2f}%")
with k5: st.metric("Estado Líder (part.)", f"{estado_lider} — {part_lider:.2f}%")
with k6: st.metric("Clientes Únicos / Itens/Venda", f"{clientes_unicos} / {itens_por_venda:.2f}")

st.divider()

# ====== Gráficos (um abaixo do outro) ======

# a) Vendas por cliente (faturamento)
st.subheader("a) Faturamento por Cliente")
if filtered.empty:
    st.info("Sem dados.")
else:
    g_clientes = (filtered.groupby("nome_cliente", as_index=False)["preco_total"].sum()
                  .sort_values("preco_total", ascending=False))
    fig_a = px.bar(g_clientes, x="nome_cliente", y="preco_total",
                   title="Faturamento por Cliente",
                   labels={"preco_total": "Faturamento (R$)", "nome_cliente": "Cliente"})
    fig_a.update_layout(xaxis_tickangle=-45, yaxis_tickformat=",")
    st.plotly_chart(fig_a, use_container_width=True, key="light_a_clientes")

# b) Vendas por vendedor (faturamento)
st.subheader("b) Faturamento por Vendedor")
if filtered.empty:
    st.info("Sem dados.")
else:
    g_vend = (filtered.groupby("nome_vendedor", as_index=False)["preco_total"].sum()
              .sort_values("preco_total", ascending=False))
    fig_b = px.bar(g_vend, x="nome_vendedor", y="preco_total",
                   title="Faturamento por Vendedor",
                   labels={"preco_total": "Faturamento (R$)", "nome_vendedor": "Vendedor"})
    fig_b.update_layout(xaxis_tickangle=-45, yaxis_tickformat=",")
    st.plotly_chart(fig_b, use_container_width=True, key="light_b_vendedores")

# c) Categorias que mais vendem (quantidade)
st.subheader("c) Categorias com Maior Quantidade Vendida")
if filtered.empty:
    st.info("Sem dados.")
else:
    g_cat_qtd = (filtered.groupby("categoria_produto", as_index=False)["quantidade_vendida"].sum()
                 .sort_values("quantidade_vendida", ascending=False))
    fig_c = px.bar(g_cat_qtd, x="categoria_produto", y="quantidade_vendida",
                   title="Quantidade Vendida por Categoria",
                   labels={"quantidade_vendida": "Quantidade", "categoria_produto": "Categoria"})
    fig_c.update_layout(xaxis_tickangle=-30)
    st.plotly_chart(fig_c, use_container_width=True, key="light_c_cat_qtd")

# d) Meses x quantidade de vendas (área)
st.subheader("d) Quantidade de Vendas por Mês (Área)")
if filtered.empty:
    st.info("Sem dados.")
else:
    por_mes = (filtered.assign(mes_ord=filtered["data_venda"].dt.month)
               .groupby(["ano", "mes_ord"], as_index=False)
               .agg(qtd_vendas=("id_venda", "count")))
    por_mes["mes_label"] = pd.to_datetime(por_mes["mes_ord"], format="%m").dt.strftime("%b")
    por_mes = por_mes.sort_values(["ano", "mes_ord"])
    fig_d = px.area(por_mes, x="mes_label", y="qtd_vendas", color="ano",
                    title="Quantidade de Vendas por Mês (Área)",
                    labels={"mes_label": "Mês", "qtd_vendas": "Qtd. Vendas", "ano": "Ano"})
    st.plotly_chart(fig_d, use_container_width=True, key="light_d_area_meses")

# e) Top 5 clientes
st.subheader("e) Top 5 Clientes por Faturamento")
if filtered.empty:
    st.info("Sem dados.")
else:
    top_cli = (filtered.groupby("nome_cliente", as_index=False)["preco_total"].sum()
               .sort_values("preco_total", ascending=False).head(5))
    fig_e = px.bar(top_cli, x="nome_cliente", y="preco_total",
                   title="Top 5 Clientes por Faturamento",
                   labels={"preco_total": "Faturamento (R$)", "nome_cliente": "Cliente"})
    fig_e.update_layout(xaxis_tickangle=-45, yaxis_tickformat=",")
    st.plotly_chart(fig_e, use_container_width=True, key="light_e_top_clientes")
    st.dataframe(top_cli.rename(columns={"preco_total": "Faturamento (R$)"}), use_container_width=True)

# f) Top 5 vendedores
st.subheader("f) Top 5 Vendedores por Faturamento")
if filtered.empty:
    st.info("Sem dados.")
else:
    top_v = (filtered.groupby("nome_vendedor", as_index=False)["preco_total"].sum()
             .sort_values("preco_total", ascending=False).head(5))
    fig_f = px.bar(top_v, x="nome_vendedor", y="preco_total",
                   title="Top 5 Vendedores por Faturamento",
                   labels={"preco_total": "Faturamento (R$)", "nome_vendedor": "Vendedor"})
    fig_f.update_layout(xaxis_tickangle=-45, yaxis_tickformat=",")
    st.plotly_chart(fig_f, use_container_width=True, key="light_f_top_vendedores")
    st.dataframe(top_v.rename(columns={"preco_total": "Faturamento (R$)"}), use_container_width=True)

# g) Lojas que mais vendem (faturamento)
st.subheader("g) Faturamento por Loja")
if filtered.empty:
    st.info("Sem dados.")
else:
    g_loja = (filtered.groupby("loja", as_index=False)["preco_total"].sum()
              .sort_values("preco_total", ascending=False))
    fig_g = px.bar(g_loja, x="loja", y="preco_total",
                   title="Faturamento por Loja",
                   labels={"preco_total": "Faturamento (R$)", "loja": "Loja"})
    fig_g.update_layout(yaxis_tickformat=",")
    st.plotly_chart(fig_g, use_container_width=True, key="light_g_lojas")

st.divider()

# ====== Indicadores por Categoria do Cliente ======
st.header("👥 Indicadores por Categoria do Cliente (Bronze / Prata / Ouro)")
if filtered.empty or "categoria_cliente" not in filtered.columns:
    st.info("Sem dados ou coluna 'categoria_cliente' ausente.")
else:
    g_cat_cli = (filtered.groupby("categoria_cliente", as_index=False)
                 .agg(vendas=("id_venda", "count"),
                      itens=("quantidade_vendida", "sum"),
                      faturamento=("preco_total", "sum")))
    g_cat_cli["ticket_medio"] = g_cat_cli.apply(
        lambda r: (r["faturamento"] / r["vendas"]) if r["vendas"] > 0 else 0.0, axis=1
    )
    st.dataframe(g_cat_cli, use_container_width=True)
    fig_cat_cli = px.bar(g_cat_cli.sort_values("faturamento", ascending=False),
                         x="categoria_cliente", y="faturamento",
                         title="Faturamento por Categoria do Cliente",
                         labels={"faturamento": "Faturamento (R$)", "categoria_cliente": "Categoria"})
    st.plotly_chart(fig_cat_cli, use_container_width=True, key="light_cat_cliente_bar")

st.divider()

# ====== Série temporal (Área) - Faturamento por dia ======
st.subheader("📆 Faturamento Diário (Área)")
if filtered.empty:
    st.info("Sem dados.")
else:
    diario = filtered.groupby("dia", as_index=False)["preco_total"].sum()
    fig_area = px.area(diario, x="dia", y="preco_total",
                       title="Faturamento por Dia",
                       labels={"preco_total": "Faturamento (R$)", "dia": "Data"})
    st.plotly_chart(fig_area, use_container_width=True, key="light_area_diaria")

# ====== Mapa (Plotly Mapbox) - faturamento por cidade ======
st.subheader("🗺️ Mapa (Plotly) — Faturamento por Cidade")
if filtered.empty:
    st.info("Sem dados.")
else:
    agg_city = (filtered.groupby(["estado", "municipio"], as_index=False)
                .agg(faturamento=("preco_total", "sum"),
                     vendas=("id_venda", "count")))
    # Anexa lat/lon
    agg_city["lat"] = agg_city["municipio"].map(lambda m: CITY_LATLON.get(str(m), (None, None))[0])
    agg_city["lon"] = agg_city["municipio"].map(lambda m: CITY_LATLON.get(str(m), (None, None))[1])
    agg_city = agg_city.dropna(subset=["lat", "lon"])
    if agg_city.empty:
        st.warning("Não há geocódigos disponíveis para as cidades filtradas.")
    else:
        fig_map = px.scatter_mapbox(
            agg_city,
            lat="lat", lon="lon",
            size="faturamento",
            color="estado",
            hover_name="municipio",
            hover_data={"faturamento": ":.2f", "vendas": True, "lat": False, "lon": False},
            zoom=3.2,
            height=520,
            title="Faturamento por Cidade (Tamanho do ponto = Faturamento)",
        )
        fig_map.update_layout(mapbox_style="open-street-map", margin=dict(l=0, r=0, t=50, b=0))
        st.plotly_chart(fig_map, use_container_width=True, key="light_map_plotly")

# ====== Mapa (Folium) — cluster de cidades ======
st.subheader("🧭 Mapa (Folium) — Cidades com Compras")
if not HAS_FOLIUM:
    st.info("Instale `folium` e `streamlit-folium` para visualizar este mapa:  pip install folium streamlit-folium")
else:
    if filtered.empty:
        st.info("Sem dados.")
    else:
        agg_city2 = (filtered.groupby(["estado", "municipio"], as_index=False)
                     .agg(faturamento=("preco_total", "sum"),
                          vendas=("id_venda", "count")))
        agg_city2["lat"] = agg_city2["municipio"].map(lambda m: CITY_LATLON.get(str(m), (None, None))[0])
        agg_city2["lon"] = agg_city2["municipio"].map(lambda m: CITY_LATLON.get(str(m), (None, None))[1])
        agg_city2 = agg_city2.dropna(subset=["lat", "lon"])

        if agg_city2.empty:
            st.warning("Não há geocódigos disponíveis para as cidades filtradas.")
        else:
            # Centro aproximado do Brasil
            m = folium.Map(location=[-14.2350, -51.9253], zoom_start=4, tiles="CartoDB positron")
            for _, row in agg_city2.iterrows():
                valor = row["faturamento"]
                radius = max(4, min(30, math.sqrt(valor) / 8))  # escala suave
                folium.CircleMarker(
                    location=[row["lat"], row["lon"]],
                    radius=radius,
                    popup=folium.Popup(
                        f"<b>{row['municipio']}/{row['estado']}</b><br/>"
                        f"Vendas: {int(row['vendas'])}<br/>"
                        f"Faturamento: {fmt_currency(float(valor))}",
                        max_width=250
                    ),
                    color="#2a7ae2",
                    fill=True,
                    fill_opacity=0.45
                ).add_to(m)

            st_folium(m, width=None, height=540, returned_objects=[])

st.divider()

# ====== Dados filtrados / Download ======
st.subheader("📋 Dados Filtrados")
st.dataframe(filtered.sort_values("data_venda", ascending=False), use_container_width=True, height=420)

csv_dl = filtered.to_csv(index=False, sep=";").encode("utf-8")
st.download_button(
    label="⬇️ Baixar CSV (dados filtrados)",
    data=csv_dl,
    file_name="vendas_filtrado.csv",
    mime="text/csv"
)

st.caption("Execute:  streamlit run streamlit_app1_light.py")
