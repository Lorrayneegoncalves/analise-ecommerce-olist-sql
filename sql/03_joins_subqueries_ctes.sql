/* =====================================================================
   03 - JOINs, subqueries e CTEs
   Convenção: receita = soma do preço dos itens (price) de pedidos
   com status 'delivered'. O frete (freight_value) não entra na receita.
   ===================================================================== */
USE Olist;
GO

-- J1. Receita mensal (pedidos entregues)
SELECT DATEFROMPARTS(YEAR(o.order_purchase_timestamp), MONTH(o.order_purchase_timestamp), 1) AS mes,
       COUNT(DISTINCT o.order_id) AS pedidos,
       SUM(i.price)               AS receita
FROM dbo.orders o
JOIN dbo.order_items i ON i.order_id = o.order_id
WHERE o.order_status = 'delivered'
GROUP BY DATEFROMPARTS(YEAR(o.order_purchase_timestamp), MONTH(o.order_purchase_timestamp), 1)
ORDER BY mes;

-- J2. Top 10 categorias por receita (com nome em inglês quando houver tradução)
SELECT TOP 10
       COALESCE(t.product_category_name_english, p.product_category_name, 'sem_categoria') AS categoria,
       COUNT(*)     AS itens_vendidos,
       SUM(i.price) AS receita
FROM dbo.order_items i
JOIN dbo.orders o   ON o.order_id = i.order_id
JOIN dbo.products p ON p.product_id = i.product_id
LEFT JOIN dbo.category_translation t ON t.product_category_name = p.product_category_name
WHERE o.order_status = 'delivered'
GROUP BY COALESCE(t.product_category_name_english, p.product_category_name, 'sem_categoria')
ORDER BY receita DESC;

-- J3. Tempo médio de entrega e % de pedidos atrasados, por estado do cliente
SELECT c.customer_state,
       COUNT(*) AS pedidos_entregues,
       CAST(AVG(DATEDIFF(DAY, o.order_purchase_timestamp, o.order_delivered_customer_date) * 1.0) AS DECIMAL(6,1)) AS dias_medios_entrega,
       CAST(100.0 * SUM(CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1 ELSE 0 END)
            / COUNT(*) AS DECIMAL(5,2)) AS pct_atrasados
FROM dbo.orders o
JOIN dbo.customers c ON c.customer_id = o.customer_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY c.customer_state
ORDER BY dias_medios_entrega DESC;

-- J4. (CTE) Clientes de uma compra versus clientes recorrentes
--     customer_unique_id identifica a pessoa; customer_id muda a cada pedido.
WITH compras AS (
    SELECT c.customer_unique_id,
           COUNT(DISTINCT o.order_id) AS qtd_pedidos
    FROM dbo.orders o
    JOIN dbo.customers c ON c.customer_id = o.customer_id
    WHERE o.order_status <> 'canceled'
    GROUP BY c.customer_unique_id
),
classificados AS (
    SELECT CASE WHEN qtd_pedidos = 1 THEN 'Uma compra' ELSE 'Recorrente (2+ pedidos)' END AS perfil
    FROM compras
)
SELECT perfil,
       COUNT(*) AS clientes,
       CAST(100.0 * COUNT(*) / SUM(COUNT(*)) OVER () AS DECIMAL(5,2)) AS percentual
FROM classificados
GROUP BY perfil;

-- J5. (Subquery) Pedidos cujo valor está acima da média de todos os pedidos
SELECT TOP 10
       order_id,
       SUM(price) AS valor_pedido
FROM dbo.order_items
GROUP BY order_id
HAVING SUM(price) > (
    SELECT AVG(valor)
    FROM (SELECT SUM(price) AS valor FROM dbo.order_items GROUP BY order_id) AS t
)
ORDER BY valor_pedido DESC;
