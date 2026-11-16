"""Dashboard do e-commerce Olist (Streamlit + Plotly).

Mostra, de forma interativa, as mesmas perguntas respondidas em SQL na pasta sql/.
As definições são as mesmas:
  - receita  = soma do preço dos itens de pedidos entregues (sem frete)
  - atrasado = entregue depois da data estimada
  - prazo    = dias entre a compra e a entrega

Rodar:  streamlit run dashboard/app.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DADOS = Path(__file__).parent / "dados"
COR = "#8A5A62"          # cor única das séries
COR_NEUTRA = "#A3A7AA"   # grupo de comparação
MIN_AVALIACOES = 100     # mínimo para uma categoria entrar no ranking de notas
MIN_PEDIDOS_MES = 50      # meses com menos pedidos ficam fora do gráfico de atrasos
MIN_PEDIDOS_ESTADO = 100  # abaixo disso, a média do estado é pouco confiável

st.set_page_config(page_title="E-commerce Olist", layout="wide")


# ---------------------------------------------------------------- dados

@st.cache_data
def carregar() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (
        pd.read_parquet(DADOS / "pedidos.parquet"),
        pd.read_parquet(DADOS / "itens.parquet"),
        pd.read_parquet(DADOS / "avaliacoes.parquet"),
    )


# ---------------------------------------------------------------- formato brasileiro

def br(valor: float, casas: int = 0) -> str:
    """1234567.8 -> '1.234.568' (ponto no milhar, vírgula no decimal)."""
    if pd.isna(valor):
        return "–"
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def reais(valor: float) -> str:
    if pd.isna(valor):
        return "–"
    if abs(valor) >= 1_000_000:
        return f"R$ {br(valor / 1_000_000, 2)} mi"
    if abs(valor) >= 10_000:
        return f"R$ {br(valor / 1_000, 1)} mil"
    return f"R$ {br(valor, 2)}"


def pct(valor: float, casas: int = 1) -> str:
    return "–" if pd.isna(valor) else f"{br(valor * 100, casas)}%"


# ---------------------------------------------------------------- gráficos

def layout(fig: go.Figure, altura: int = 340) -> go.Figure:
    fig.update_layout(
        height=altura,
        margin=dict(l=0, r=24, t=8, b=0),
        separators=",.",
        showlegend=False,
        hoverlabel=dict(font_size=13),
        bargap=0.35,
    )
    fig.update_xaxes(showgrid=False, title=None)
    fig.update_yaxes(title=None)
    return fig


def barras_horizontais(serie: pd.Series, texto: list[str], dica: str, altura: int = 340) -> go.Figure:
    """Barras deitadas, maior no topo. `serie` já vem ordenada do maior para o menor."""
    serie = serie.iloc[::-1]
    fig = go.Figure(
        go.Bar(
            x=serie.values,
            y=serie.index.astype(str),
            orientation="h",
            marker_color=COR,
            text=texto[::-1],
            textposition="outside",
            cliponaxis=False,
            hovertemplate=dica,
        )
    )
    layout(fig, altura)
    fig.update_xaxes(showticklabels=False, range=[0, serie.max() * 1.18 if len(serie) else 1])
    fig.update_yaxes(showgrid=False)
    return fig


def mostrar(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


# ---------------------------------------------------------------- filtros

pedidos, itens, avaliacoes = carregar()

with st.sidebar:
    st.header("Filtros")
    ano = st.selectbox("Ano da compra", ["Todos", *sorted(pedidos["ano"].unique())])
    estados = st.multiselect(
        "Estado do cliente", sorted(pedidos["estado"].unique()), placeholder="Todos"
    )
    categorias = st.multiselect(
        "Categoria do produto", sorted(itens["categoria"].unique()), placeholder="Todas"
    )
    st.caption(
        "Com filtro de categoria, a receita soma só os itens dessas categorias; "
        "pedidos, entrega e notas consideram os pedidos que têm ao menos um item delas."
    )

ped = pedidos
if ano != "Todos":
    ped = ped[ped["ano"] == ano]
if estados:
    ped = ped[ped["estado"].isin(estados)]
it = itens[itens["pedido"].isin(ped["pedido"])]
if categorias:
    it = it[it["categoria"].isin(categorias)]
    ped = ped[ped["pedido"].isin(it["pedido"])]

entregues = ped[ped["entregue"]]                                   # base das análises de entrega
it_receita = it[it["pedido"].isin(ped.loc[ped["status"] == "delivered", "pedido"])]
notas = avaliacoes.merge(
    entregues[["pedido", "estado", "atrasado"]], on="pedido"
)                                                                  # avaliações de pedidos entregues

# ---------------------------------------------------------------- cabeçalho

st.title("E-commerce Olist")
st.caption(
    "Dataset público *Brazilian E-Commerce Public Dataset by Olist* (Kaggle), "
    "com pedidos de 09/2016 a 10/2018. Dados históricos e anonimizados."
)

if ped.empty:
    st.warning("Nenhum pedido encontrado com esses filtros.")
    st.stop()

aba_geral, aba_entrega, aba_clientes = st.tabs(
    ["Visão geral", "Entrega", "Clientes e categorias"]
)

# ---------------------------------------------------------------- 1. visão geral

with aba_geral:
    receita = it_receita["preco"].sum()
    n_pedidos = it_receita["pedido"].nunique()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Receita", reais(receita), help="Soma do preço dos itens de pedidos entregues. Não inclui frete.")
    c2.metric("Pedidos entregues", br(n_pedidos))
    c3.metric("Ticket médio", reais(receita / n_pedidos if n_pedidos else float("nan")),
              help="Receita dividida pelo número de pedidos entregues.")
    c4.metric("Nota média", br(notas["nota"].mean(), 2),
              help="Média das avaliações (1 a 5) dos pedidos entregues.")

    st.subheader("Receita por mês")
    mensal = (
        it_receita.merge(ped[["pedido", "mes"]], on="pedido")
        .groupby("mes")["preco"].sum()
    )
    fig = go.Figure(
        go.Scatter(
            x=mensal.index,
            y=mensal.values / 1000,
            mode="lines+markers",
            line=dict(color=COR, width=2),
            marker=dict(size=6),
            customdata=[reais(v) for v in mensal.values],
            hovertemplate="%{x|%m/%Y}<br>%{customdata}<extra></extra>",
        )
    )
    layout(fig)
    fig.update_xaxes(tickformat="%m/%Y")
    fig.update_yaxes(tickprefix="R$ ", ticksuffix=" mil", tickformat=",.0f", rangemode="tozero")
    mostrar(fig)
    st.caption(
        "Em 2016 há só três meses com pouquíssimos pedidos, e os pedidos entregues vão até 08/2018; "
        "por isso as pontas da série não servem para comparação."
    )

    st.subheader("Categorias com maior receita")
    por_categoria = it_receita.groupby("categoria")["preco"].agg(["sum", "count"])
    top = por_categoria.sort_values("sum", ascending=False).head(10)
    fig = barras_horizontais(
        top["sum"],
        [reais(v) for v in top["sum"]],
        "%{y}<br>%{text}<br>%{customdata} itens<extra></extra>",
        altura=380,
    )
    fig.update_traces(customdata=[br(v) for v in top["count"]][::-1])
    mostrar(fig)

# ---------------------------------------------------------------- 2. entrega

with aba_entrega:
    if entregues.empty:
        st.info("Nenhum pedido entregue com esses filtros.")
    else:
        nota_situacao = notas.groupby("atrasado")["nota"].agg(["mean", "count"])
        nota_prazo = nota_situacao["mean"].get(False, float("nan"))
        nota_atraso = nota_situacao["mean"].get(True, float("nan"))

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Prazo médio de entrega", f"{br(entregues['dias_entrega'].mean(), 1)} dias",
                  help="Dias entre a compra e a entrega ao cliente.")
        c2.metric("Entregas atrasadas", pct(entregues["atrasado"].mean()),
                  help="Pedidos entregues depois da data estimada.")
        c3.metric("Nota média no prazo", br(nota_prazo, 2))
        c4.metric("Nota média com atraso", br(nota_atraso, 2))

        esquerda, direita = st.columns([3, 2])
        with esquerda:
            st.subheader("Entregas atrasadas por mês da compra")
            atraso_mes = entregues.groupby("mes")["atrasado"].agg(["mean", "count"])
            # Meses com poucos pedidos (ex.: 1 pedido em 09/2016) distorcem o percentual.
            atraso_mes = atraso_mes[atraso_mes["count"] >= MIN_PEDIDOS_MES]
            fig = go.Figure(
                go.Scatter(
                    x=atraso_mes.index,
                    y=atraso_mes["mean"] * 100,
                    mode="lines+markers",
                    line=dict(color=COR, width=2),
                    marker=dict(size=6),
                    customdata=list(zip([pct(v) for v in atraso_mes["mean"]],
                                        [br(v) for v in atraso_mes["count"]])),
                    hovertemplate="%{x|%m/%Y}<br>%{customdata[0]} atrasados"
                                  "<br>%{customdata[1]} pedidos entregues<extra></extra>",
                )
            )
            layout(fig, 300)
            fig.update_xaxes(tickformat="%m/%Y")
            fig.update_yaxes(ticksuffix="%", rangemode="tozero")
            mostrar(fig)
            st.caption(f"Só meses com {MIN_PEDIDOS_MES} pedidos entregues ou mais.")

        with direita:
            st.subheader("Nota média: no prazo e com atraso")
            rotulos = ["No prazo", "Com atraso"]
            valores = [nota_prazo, nota_atraso]
            contagens = [nota_situacao["count"].get(False, 0), nota_situacao["count"].get(True, 0)]
            fig = go.Figure(
                go.Bar(
                    x=rotulos,
                    y=valores,
                    marker_color=[COR_NEUTRA, COR],
                    text=[br(v, 2) for v in valores],
                    textposition="outside",
                    cliponaxis=False,
                    customdata=[br(v) for v in contagens],
                    hovertemplate="%{x}<br>nota média %{text}<br>%{customdata} avaliações<extra></extra>",
                    width=0.45,
                )
            )
            layout(fig, 300)
            fig.update_yaxes(range=[0, 5.6], tickvals=[0, 1, 2, 3, 4, 5])
            mostrar(fig)

        st.subheader("Entrega por estado do cliente")
        por_estado = entregues.groupby("estado").agg(
            pedidos=("pedido", "count"),
            prazo=("dias_entrega", "mean"),
            atraso=("atrasado", "mean"),
        ).sort_values("prazo", ascending=False)
        altura = max(220, 26 * len(por_estado) + 40)
        dica_pedidos = [br(v) for v in por_estado["pedidos"]][::-1]

        esquerda, direita = st.columns(2)
        with esquerda:
            st.markdown("**Prazo médio (dias)**")
            fig = barras_horizontais(
                por_estado["prazo"],
                [br(v, 1) for v in por_estado["prazo"]],
                "%{y}<br>%{text} dias<br>%{customdata} pedidos entregues<extra></extra>",
                altura,
            )
            fig.update_traces(customdata=dica_pedidos)
            mostrar(fig)
        with direita:
            st.markdown("**Entregas atrasadas (%)**")
            fig = barras_horizontais(
                por_estado["atraso"] * 100,
                [pct(v) for v in por_estado["atraso"]],
                "%{y}<br>%{text} atrasados<br>%{customdata} pedidos entregues<extra></extra>",
                altura,
            )
            fig.update_traces(customdata=dica_pedidos)
            mostrar(fig)

        poucos = por_estado.index[por_estado["pedidos"] < MIN_PEDIDOS_ESTADO].tolist()
        nota_rodape = "Os dois gráficos estão na mesma ordem (do maior para o menor prazo médio)."
        if poucos:
            nota_rodape += (
                f" Com menos de {MIN_PEDIDOS_ESTADO} pedidos entregues neste recorte, "
                f"as médias de {', '.join(sorted(poucos))} são pouco confiáveis."
            )
        st.caption(nota_rodape)
        st.caption(
            "Os números mostram associação, não causa: a nota menor nos pedidos atrasados "
            "não prova que o atraso é o motivo."
        )

# ---------------------------------------------------------------- 3. clientes e categorias

with aba_clientes:
    # Recompra: mesma regra da consulta J4 (todos os pedidos, menos os cancelados).
    compras = ped[ped["status"] != "canceled"].groupby("cliente")["pedido"].nunique()
    recorrentes = int((compras > 1).sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("Clientes", br(len(compras)),
              help="Pessoas diferentes (customer_unique_id) com ao menos um pedido não cancelado.")
    c2.metric("Compraram mais de uma vez", br(recorrentes))
    c3.metric("Taxa de recompra", pct(recorrentes / len(compras) if len(compras) else float("nan"), 2))

    st.subheader("Receita por estado do cliente")
    receita_estado = (
        it_receita.merge(ped[["pedido", "estado"]], on="pedido")
        .groupby("estado")["preco"].sum()
        .sort_values(ascending=False)
    )
    total = receita_estado.sum()
    top = receita_estado.head(10)
    fig = barras_horizontais(
        top,
        [f"{reais(v)} · {pct(v / total)}" for v in top],
        "%{y}<br>%{text}<extra></extra>",
        altura=max(220, 30 * len(top) + 40),
    )
    fig.update_xaxes(range=[0, top.max() * 1.3])
    mostrar(fig)
    if len(receita_estado) > 10:
        st.caption("Os 10 estados com maior receita. O percentual é a parte de cada um na receita do recorte.")

    st.subheader("Categorias com menor nota média")
    # Cada avaliação conta uma vez por categoria do pedido (como o DISTINCT da consulta 05).
    categoria_pedido = it[["pedido", "categoria"]].drop_duplicates()
    base = categoria_pedido.merge(notas[["pedido", "nota", "atrasado"]], on="pedido")
    tabela = base.groupby("categoria").agg(
        avaliacoes=("nota", "count"),
        nota=("nota", "mean"),
        atrasados=("atrasado", "mean"),
    )
    tabela["nota_no_prazo"] = base[~base["atrasado"]].groupby("categoria")["nota"].mean()
    tabela = tabela[tabela["avaliacoes"] >= MIN_AVALIACOES].sort_values("nota").head(15)
    tabela["atrasados"] *= 100

    if tabela.empty:
        st.info(f"Nenhuma categoria tem {MIN_AVALIACOES} avaliações ou mais com esses filtros.")
    else:
        # Números já formatados no padrão brasileiro (vírgula decimal).
        exibir = pd.DataFrame(
            {
                "Categoria": tabela.index,
                "Avaliações": [br(v) for v in tabela["avaliacoes"]],
                "Nota média": [br(v, 2) for v in tabela["nota"]],
                "Atrasados": [f"{br(v, 1)}%" for v in tabela["atrasados"]],
                "Nota média no prazo": [br(v, 2) for v in tabela["nota_no_prazo"]],
            }
        )
        st.dataframe(
            exibir.style.set_properties(
                subset=exibir.columns[1:].tolist(), **{"text-align": "right"}
            ),
            hide_index=True,
            width="stretch",
            height=35 * (len(exibir) + 1) + 3,
        )
        st.caption(
            f"Pedidos entregues e avaliados, categorias com {MIN_AVALIACOES} avaliações ou mais. "
            "A coluna da nota no prazo ajuda a ver se o atraso, sozinho, explica a nota baixa."
        )
