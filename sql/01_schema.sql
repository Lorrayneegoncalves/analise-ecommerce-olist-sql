/* =====================================================================
   01 - Esquema: chaves primárias e estrangeiras
   As tabelas foram criadas pela importação dos CSVs. Este script define
   as chaves para documentar os relacionamentos e garantir integridade.

   Observações:
   - order_reviews NÃO recebe chave primária: review_id se repete na base.
   - Não há chave estrangeira de products para category_translation,
     porque existem categorias de produtos sem tradução na tabela.
   - Se algum comando falhar por valores duplicados ou órfãos, isso é um
     achado sobre a qualidade dos dados: investigue antes de seguir.
   ===================================================================== */
USE Olist;
GO

-- ----- Chaves primárias -----
ALTER TABLE dbo.customers            ADD CONSTRAINT PK_customers            PRIMARY KEY (customer_id);
ALTER TABLE dbo.orders               ADD CONSTRAINT PK_orders               PRIMARY KEY (order_id);
ALTER TABLE dbo.products             ADD CONSTRAINT PK_products             PRIMARY KEY (product_id);
ALTER TABLE dbo.sellers              ADD CONSTRAINT PK_sellers              PRIMARY KEY (seller_id);
ALTER TABLE dbo.order_items          ADD CONSTRAINT PK_order_items          PRIMARY KEY (order_id, order_item_id);
ALTER TABLE dbo.order_payments       ADD CONSTRAINT PK_order_payments       PRIMARY KEY (order_id, payment_sequential);
ALTER TABLE dbo.category_translation ADD CONSTRAINT PK_category_translation PRIMARY KEY (product_category_name);
GO

-- ----- Chaves estrangeiras -----
ALTER TABLE dbo.orders         ADD CONSTRAINT FK_orders_customers   FOREIGN KEY (customer_id) REFERENCES dbo.customers (customer_id);
ALTER TABLE dbo.order_items    ADD CONSTRAINT FK_items_orders       FOREIGN KEY (order_id)    REFERENCES dbo.orders (order_id);
ALTER TABLE dbo.order_items    ADD CONSTRAINT FK_items_products     FOREIGN KEY (product_id)  REFERENCES dbo.products (product_id);
ALTER TABLE dbo.order_items    ADD CONSTRAINT FK_items_sellers      FOREIGN KEY (seller_id)   REFERENCES dbo.sellers (seller_id);
ALTER TABLE dbo.order_payments ADD CONSTRAINT FK_payments_orders    FOREIGN KEY (order_id)    REFERENCES dbo.orders (order_id);
ALTER TABLE dbo.order_reviews  ADD CONSTRAINT FK_reviews_orders     FOREIGN KEY (order_id)    REFERENCES dbo.orders (order_id);
GO
