/* =====================================================================
   02 - Consultas básicas: filtros, agregações, GROUP BY e HAVING
   ===================================================================== */
USE Olist;
GO

-- B1. Quantos pedidos existem em cada status?
SELECT order_status,
       COUNT(*) AS qtd_pedidos
FROM dbo.orders
GROUP BY order_status
ORDER BY qtd_pedidos DESC;

-- B2. Em quais estados estão os clientes? (apenas estados com mais de 1.000 clientes)
SELECT customer_state,
       COUNT(*) AS qtd_clientes
FROM dbo.customers
GROUP BY customer_state
HAVING COUNT(*) > 1000
ORDER BY qtd_clientes DESC;

-- B3. Como os clientes pagam? Quantidade, valor total e valor médio por forma de pagamento
SELECT payment_type,
       COUNT(*)           AS qtd_pagamentos,
       SUM(payment_value) AS valor_total,
       AVG(payment_value) AS valor_medio
FROM dbo.order_payments
GROUP BY payment_type
ORDER BY valor_total DESC;

-- B4. Distribuição das notas de avaliação (quantidade e percentual)
SELECT review_score,
       COUNT(*) AS qtd_avaliacoes,
       CAST(100.0 * COUNT(*) / SUM(COUNT(*)) OVER () AS DECIMAL(5,2)) AS percentual
FROM dbo.order_reviews
GROUP BY review_score
ORDER BY review_score;
