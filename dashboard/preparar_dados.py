"""Prepara os dados do dashboard a partir dos CSVs do Olist.

Lê os CSVs originais (baixados do Kaggle) e grava três arquivos pequenos em
dashboard/dados/, só com as colunas que o dashboard usa:

  pedidos.parquet     1 linha por pedido
  itens.parquet       1 linha por item de pedido
  avaliacoes.parquet  1 linha por avaliação

As definições são as mesmas dos scripts da pasta sql/:
  - receita  = soma de price dos itens de pedidos com status 'delivered' (sem frete)
  - atrasado = entregue depois da data estimada
  - prazo    = dias entre a compra e a entrega (como DATEDIFF(DAY, ...))

Uso:
    python dashboard/preparar_dados.py --entrada caminho/para/os/csvs
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

SAIDA = Path(__file__).parent / "dados"


def preparar(entrada: Path) -> dict[str, pd.DataFrame]:
    pedidos = pd.read_csv(
        entrada / "olist_orders_dataset.csv",
        parse_dates=[
            "order_purchase_timestamp",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
    )
    clientes = pd.read_csv(entrada / "olist_customers_dataset.csv")
    itens = pd.read_csv(entrada / "olist_order_items_dataset.csv")
    produtos = pd.read_csv(entrada / "olist_products_dataset.csv")
    traducao = pd.read_csv(entrada / "product_category_name_translation.csv")
    avaliacoes = pd.read_csv(entrada / "olist_order_reviews_dataset.csv")

    # Troca os identificadores longos (texto) por números, para o arquivo ficar pequeno.
    pedidos["pedido"] = range(len(pedidos))
    id_pedido = pedidos.set_index("order_id")["pedido"]

    pedidos = pedidos.merge(clientes, on="customer_id", how="left", validate="one_to_one")
    pedidos["cliente"] = pd.factorize(pedidos["customer_unique_id"])[0]

    compra = pedidos["order_purchase_timestamp"]
    entrega = pedidos["order_delivered_customer_date"]
    estimada = pedidos["order_estimated_delivery_date"]

    # Mesmo filtro das consultas de entrega: status 'delivered' e data de entrega preenchida.
    pedidos["entregue"] = (pedidos["order_status"] == "delivered") & entrega.notna()
    pedidos["dias_entrega"] = (entrega.dt.normalize() - compra.dt.normalize()).dt.days
    pedidos["atrasado"] = entrega > estimada

    tabela_pedidos = pedidos.rename(
        columns={"order_status": "status", "customer_state": "estado"}
    ).assign(mes=compra.dt.to_period("M").dt.to_timestamp(), ano=compra.dt.year)[
        ["pedido", "status", "mes", "ano", "estado", "cliente", "entregue", "dias_entrega", "atrasado"]
    ]

    # Categoria em inglês quando há tradução; senão o nome original; senão 'sem_categoria'.
    produtos = produtos.merge(traducao, on="product_category_name", how="left")
    produtos["categoria"] = (
        produtos["product_category_name_english"]
        .fillna(produtos["product_category_name"])
        .fillna("sem_categoria")
    )
    itens = itens.merge(produtos[["product_id", "categoria"]], on="product_id", how="left")
    tabela_itens = pd.DataFrame(
        {
            "pedido": itens["order_id"].map(id_pedido),
            "categoria": itens["categoria"],
            "preco": itens["price"],
            "frete": itens["freight_value"],
        }
    )

    tabela_avaliacoes = pd.DataFrame(
        {
            "pedido": avaliacoes["order_id"].map(id_pedido),
            "nota": avaliacoes["review_score"],
        }
    )

    return {"pedidos": tabela_pedidos, "itens": tabela_itens, "avaliacoes": tabela_avaliacoes}


def conferir(tabelas: dict[str, pd.DataFrame]) -> None:
    """Mostra os totais de conferência, os mesmos citados no README."""
    pedidos, itens = tabelas["pedidos"], tabelas["itens"]
    entregues = pedidos.loc[pedidos["status"] == "delivered", "pedido"]
    receita = itens.loc[itens["pedido"].isin(entregues), "preco"].sum()
    print(f"Pedidos:                 {len(pedidos):>12,}")
    print(f"Pedidos entregues:       {len(entregues):>12,}")
    print(f"Itens:                   {len(itens):>12,}")
    print(f"Soma de price (todos):   {itens['preco'].sum():>15,.2f}")
    print(f"Receita (entregues):     {receita:>15,.2f}")
    print(f"Período das compras:     {pedidos['mes'].min():%m/%Y} a {pedidos['mes'].max():%m/%Y}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--entrada", required=True, type=Path, help="pasta com os CSVs do Olist")
    args = parser.parse_args()

    tabelas = preparar(args.entrada)
    conferir(tabelas)

    SAIDA.mkdir(exist_ok=True)
    for nome, tabela in tabelas.items():
        destino = SAIDA / f"{nome}.parquet"
        tabela.to_parquet(destino, index=False)
        print(f"Gravado {destino.name}: {destino.stat().st_size / 1024:,.0f} KB")


if __name__ == "__main__":
    main()
