# Instruções do Dashboard de Dados

Olá! Este arquivo contém as instruções para usar as funcionalidades do seu dashboard, incluindo a nova ferramenta de conversão de Excel para SQLite.

## Como Converter um Arquivo Excel para um Banco de Dados SQLite

Na aplicação, você encontrará uma nova aba chamada **"Excel para SQLite"**. Siga os passos abaixo para usar a ferramenta:

1.  **Carregue o arquivo Excel:** Clique no botão "Escolha um arquivo .xlsx" e selecione o arquivo Excel que você deseja converter.
2.  **Dê um nome ao banco de dados:** No campo de texto, digite o nome que você quer dar ao novo arquivo de banco de dados. É importante que o nome termine com a extensão `.db` (por exemplo, `meu_novo_banco.db`).
3.  **Clique em "Converter para SQLite":** Após carregar o arquivo e dar um nome ao banco de dados, clique no botão para iniciar a conversão.
4.  **Sucesso!** Se tudo ocorrer bem, uma mensagem de sucesso aparecerá, e o novo arquivo de banco de dados será criado no mesmo diretório da aplicação. Cada planilha do seu arquivo Excel se tornará uma tabela no novo banco de dados.

---

# Aprendendo SQL com seu Banco de Dados

Olá! Este guia vai te ajudar a entender conceitos importantes de SQL e modelagem de dados, usando como exemplo as suas tabelas `clientes` and `produtos`.

## Modelagem de Dados: Relacionamento entre Tabelas

No seu banco de dados, você tem `clientes` e `produtos`. Um cliente pode comprar vários produtos, e um produto pode ser comprado por vários clientes. Este é um relacionamento de **Muitos-para-Muitos (N:N)**.

Para representar isso corretamente, precisaríamos de uma terceira tabela, que podemos chamar de `pedidos`, para registrar as compras. Essa tabela faria a ponte entre `clientes` e `produtos`.

A tabela `pedidos` teria, no mínimo, as seguintes colunas:
*   `id`: um identificador único para cada pedido.
*   `cliente_id`: uma "chave estrangeira" que aponta para o `id` da tabela `clientes`.
*   `produto_id`: uma "chave estrangeira" que aponta para o `id` da tabela `produtos`.
*   `data_pedido`: a data em que o pedido foi feito.
*   `quantidade`: a quantidade de produto comprada.

Com essa estrutura, você pode responder perguntas como "Quais produtos o cliente João Silva comprou?" ou "Qual cliente comprou o produto 'Notebook Gamer'?".

## 5 Consultas SQL Essenciais

Aqui estão 5 tipos de consultas que são muito úteis no dia a dia.

### 1. `SELECT`: Buscando e filtrando dados

A consulta `SELECT` é usada para buscar dados de uma ou mais tabelas. Você pode usar a cláusula `WHERE` para filtrar os resultados e `ORDER BY` para ordená-los.

**Exemplo:** Buscar todos os clientes ativos e ordená-los por nome.

```sql
SELECT name, email
FROM clientes
WHERE status = 'active'
ORDER BY name;
```

### 2. `JOIN`: Combinando dados de duas tabelas

A cláusula `JOIN` é usada para combinar linhas de duas ou mais tabelas, com base em uma coluna relacionada entre elas. (Para este exemplo, vamos imaginar que a tabela `pedidos` existe).

**Exemplo:** Listar os nomes dos clientes e os nomes dos produtos que eles compraram.

```sql
SELECT c.name, p.product_name
FROM pedidos AS ped
JOIN clientes AS c ON ped.cliente_id = c.id
JOIN produtos AS p ON ped.produto_id = p.id;
```

### 3. `GROUP BY`: Agrupando dados

A cláusula `GROUP BY` agrupa linhas que têm os mesmos valores em colunas especificadas em linhas de resumo. É frequentemente usada com funções de agregação como `COUNT()`, `SUM()`, `AVG()`, etc.

**Exemplo:** Contar quantos clientes existem em cada status (`active` e `inactive`).

```sql
SELECT status, COUNT(id) AS total_clientes
FROM clientes
GROUP BY status;
```

### 4. `INSERT INTO`: Inserindo novos dados

A declaração `INSERT INTO` é usada para inserir novas linhas em uma tabela.

**Exemplo:** Adicionar um novo produto à tabela `produtos`.

```sql
INSERT INTO produtos (product_name, price, stock)
VALUES ('Headset Gamer', 299.99, 25);
```

### 5. `UPDATE`: Atualizando dados existentes

A declaração `UPDATE` é usada para modificar os registros existentes em uma tabela.

**Exemplo:** Mudar o status de um cliente de 'inactive' para 'active'.

```sql
UPDATE clientes
SET status = 'active'
WHERE email = 'carlos.p@email.com';
```

Espero que isso ajude você a explorar melhor seus dados!
