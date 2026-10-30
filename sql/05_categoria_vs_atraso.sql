/* =====================================================================
   05 - Hipótese: as piores notas por categoria estão ligadas a atraso na entrega?
   Escopo: pedidos entregues (status 'delivered') que têm avaliação.
   Atrasado = entregue depois da data estimada de entrega.
   ===================================================================== */
USE Olist;
GO

-- A. Visão geral: nota média de pedidos atrasados versus no prazo
SELECT CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
            THEN 'Atrasado' ELSE 'No prazo' END AS situacao_entrega,
       COUNT(*) AS avaliacoes,
       CAST(AVG(r.review_score * 1.0) AS DECIMAL(4,2)) AS nota_media
FROM dbo.orders o
JOIN dbo.order_reviews r ON r.order_id = o.order_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
              THEN 'Atrasado' ELSE 'No prazo' END;

-- B. Por categoria (mínimo de 100 avaliações), das piores notas para as melhores
--    DISTINCT evita contar a mesma avaliação várias vezes em pedidos com vários itens.
WITH pedidos_categoria AS (
    SELECT DISTINCT
           i.order_id,
           COALESCE(t.product_category_name_english, p.product_category_name, 'sem_categoria') AS categoria
    FROM dbo.order_items i
    JOIN dbo.products p ON p.product_id = i.product_id
    LEFT JOIN dbo.category_translation t ON t.product_category_name = p.product_category_name
),
base AS (
    SELECT pc.categoria,
           r.review_score,
           CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
                THEN 1 ELSE 0 END AS atrasado
    FROM pedidos_categoria pc
    JOIN dbo.orders o        ON o.order_id = pc.order_id
    JOIN dbo.order_reviews r ON r.order_id = o.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
)
SELECT TOP 15
       categoria,
       COUNT(*) AS avaliacoes,
       CAST(AVG(review_score * 1.0) AS DECIMAL(4,2)) AS nota_media,
       CAST(100.0 * SUM(atrasado) / COUNT(*) AS DECIMAL(5,2)) AS pct_atrasados,
       CAST(AVG(CASE WHEN atrasado = 1 THEN review_score * 1.0 END) AS DECIMAL(4,2)) AS nota_media_atrasados,
       CAST(AVG(CASE WHEN atrasado = 0 THEN review_score * 1.0 END) AS DECIMAL(4,2)) AS nota_media_no_prazo
FROM base
GROUP BY categoria
HAVING COUNT(*) >= 100
ORDER BY nota_media ASC;
