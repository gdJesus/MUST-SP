

# 🔄 Fluxo de Tarefas para Modelar os Dados ONS

## 1. **Mapear as Fontes**

* **must template** → dados brutos (instalações, valores, solicitações, aprovações).
* **TABELAS** → dicionário de apoio (status de aprovação, empresas).
* **PROBLEMAS** → relação entre problema ↔ solução.

---

## 2. **Definir Entidades Principais (Tabelas)**

Sugiro o seguinte modelo relacional:

### 📌 Tabela **Empresa**

* `id_empresa` (PK)
* `nome_empresa`

---

### 📌 Tabela **Instalação**

* `cod_ons` (PK)
* `instalacao`
* `tensao_kv`
* `sub_area_1`
* `sub_area_2`
* `id_empresa` (FK → Empresa)

---

### 📌 Tabela **Medidas\_MUST**

* `id_medida` (PK)
* `cod_ons` (FK → Instalação)
* `ano` (2025, 2026, 2027, 2028)
* `tipo` (PONTA | FORA PONTA)
* `valor_mw`
* `anotacao` (FK → Tabela\_Aprovacao)

---

### 📌 Tabela **Solicitacao**

* `id_solicitacao` (PK)
* `cod_ons` (FK → Instalação)
* `ano`
* `valor_ponta`
* `valor_foraponta`
* `aprovacao` (FK → Tabela\_Aprovacao)
* `problema` (FK → Problemas)
* `solucao` (FK → Problemas)

---

### 📌 Tabela **Tabela\_Aprovacao** (já existe no Excel)

* `id_aprovacao` (PK) → APROVADO, RESSALVAS, LIMITADO, REPROVADO
* `descricao`

---

### 📌 Tabela **Problemas** (já existe no Excel)

* `id_problema` (PK)
* `id_problema_detalhe`
* `id_cenario`
* `id_solucao`
* `id_solucao_detalhe`

---

## 3. **Relacionamentos**

* **Empresa 1—N Instalações**
* **Instalação 1—N Medidas\_MUST**
* **Instalação 1—N Solicitações**
* **Solicitação N—1 Problema**
* **Solicitação N—1 Aprovação**

---

## 4. **Pipeline de ETL (Tarefas Técnicas)**

1. **Extrair** do Excel (pandas).
2. **Limpar/Transformar**:

   * Converter colunas dinâmicas (`MUST 2026 PONTA/FORA PONTA`) em formato tidy (`ano`, `tipo`, `valor`).
   * Mapear `anotacao` para `id_aprovacao`.
   * Mapear `empresa` para `id_empresa`.
3. **Carregar** em um banco relacional (PostgreSQL / MySQL / SQLite).
4. **Testar consultas**:

   * Total MW por empresa/ano.
   * Quantidade de solicitações aprovadas.
   * Lista de ressalvas por instalação.

---

## 5. **Exemplo de Query Útil**

🔹 Total MW por empresa em 2026:

```sql
SELECT e.nome_empresa, SUM(m.valor_mw) AS total_mw
FROM Medidas_MUST m
JOIN Instalação i ON m.cod_ons = i.cod_ons
JOIN Empresa e ON i.id_empresa = e.id_empresa
WHERE m.ano = 2026
GROUP BY e.nome_empresa;
```

---

⚡ Resumindo, mestre:

* `Empresa` → Quem pede.
* `Instalação` → Onde está a rede.
* `Medidas_MUST` → Quanto foi alocado.
* `Solicitação` → O que foi pedido + aprovação/problema.
* `Tabelas` → Dicionários (status e empresas).
* `Problemas` → Justificativas técnicas.

---

Quer que eu já monte um **diagrama entidade-relacionamento (DER)** com essas tabelas para você visualizar melhor?
