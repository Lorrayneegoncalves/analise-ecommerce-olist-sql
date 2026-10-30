/* =====================================================================
   04 - Funções de janela (window functions)
   ===================================================================== */
USE Olist;
GO

-- W1. Receita mensal com variação em relação ao mês anterior (LAG) e acumulado
WITH mensal AS (
    SELECT DATEFROMPARTS(YEAR(o.order_purchase_timestamp), MONTH(o.order_purchase_timestamp), 1) AS mes,
           SUM(i.price) AS receita
    FROM dbo.orders o
    JOIN dbo.order_items i ON i.order_id = o.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY DATEFROMPARTS(YEAR(o.order_purchase_timestamp), MONTH(o.order_purchase_timestamp), 1)
)
SELECT mes,
       receita,
       LAG(receita) OVER (ORDER BY mes) AS receita_mes_anterior,
       CAST(100.0 * (receita - LAG(receita) OVER (ORDER BY mes))
            / NULLIF(LAG(receita) OVER (ORDER BY mes), 0) AS DECIMAL(10,2)) AS variacao_pct,
       SUM(receita) OVER (ORDER BY mes ROWS UNBOUNDED PRECEDING) AS receita_acumulada
FROM mensal
WHERE mes >= '2017-01-01'
ORDER BY mes;

-- W2. Top 3 vendedores por faturamento dentro de cada estado (RANK + PARTITION BY)
WITH faturamento AS (
    SELECT s.seller_id,
           s.seller_state,
           SUM(i.price)                AS faturamento,
           COUNT(DISTINCT i.order_id)  AS pedidos
    FROM dbo.order_items i
    JOIN dbo.sellers s ON s.seller_id = i.seller_id
    JOIN dbo.orders o  ON o.order_id = i.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY s.seller_id, s.seller_state
),
ranking AS (
    SELECT *,
           RANK() OVER (PARTITION BY seller_state ORDER BY faturamento DESC) AS posicao
    FROM faturamento
)
SELECT seller_state, posicao, seller_id, faturamento, pedidos
FROM ranking
WHERE posicao <= 3
ORDER BY seller_state, posicao;

-- W3. Categorias com as piores notas médias (mínimo de 100 avaliações)
--     DISTINCT evita contar a mesma avaliação várias vezes em pedidos com vários itens.
WITH categoria_pedido AS (
    SELECT DISTINCT
           i.order_id,
           COALESCE(t.product_category_name_english, p.product_category_name, 'sem_categoria') AS categoria
    FROM dbo.order_items i
    JOIN dbo.products p ON p.product_id = i.product_id
    LEFT JOIN dbo.category_translation t ON t.product_category_name = p.product_category_name
)
SELECT TOP 10
       cp.categoria,
       COUNT(*) AS avaliacoes,
       CAST(AVG(r.review_score * 1.0) AS DECIMAL(4,2)) AS nota_media
FROM categoria_pedido cp
JOIN dbo.order_reviews r ON r.order_id = cp.order_id
GROUP BY cp.categoria
HAVING COUNT(*) >= 100
ORDER BY nota_media ASC;

-- W4. Para cada cliente recorrente, o intervalo em dias entre pedidos consecutivos (LAG)
WITH pedidos_cliente AS (
    SELECT c.customer_unique_id,
           o.order_id,
           o.order_purchase_timestamp,
           LAG(o.order_purchase_timestamp) OVER (
               PARTITION BY c.customer_unique_id
               ORDER BY o.order_purchase_timestamp) AS pedido_anterior
    FROM dbo.orders o
    JOIN dbo.customers c ON c.customer_id = o.customer_id
    WHERE o.order_status <> 'canceled'
)
SELECT TOP 20
       customer_unique_id,
       order_id,
       order_purchase_timestamp,
       DATEDIFF(DAY, pedido_anterior, order_purchase_timestamp) AS dias_desde_pedido_anterior
FROM pedidos_cliente
WHERE pedido_anterior IS NOT NULL
ORDER BY dias_desde_pedido_anterior DESC;
