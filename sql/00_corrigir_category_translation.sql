/* =====================================================================
   00 - Correção da tabela category_translation após a importação
   Motivo: o assistente "Importar Arquivo Simples" do SSMS não reconheceu
   o cabeçalho do CSV, então a linha de cabeçalho entrou como dado e as
   colunas ficaram com os nomes column1 e column2.
   O script é seguro para rodar mais de uma vez.
   ===================================================================== */
USE Olist;
GO

IF COL_LENGTH('dbo.category_translation', 'column1') IS NOT NULL
BEGIN
    DELETE FROM dbo.category_translation
    WHERE column1 = 'product_category_name';

    EXEC sp_rename 'dbo.category_translation.column1', 'product_category_name', 'COLUMN';
    EXEC sp_rename 'dbo.category_translation.column2', 'product_category_name_english', 'COLUMN';
END
GO

-- Conferência: deve retornar 71 linhas
SELECT COUNT(*) AS linhas FROM dbo.category_translation;
