-- Query 1: Contagem de Equipamentos por Empresa
-- Objetivo: Descobrir quantas instalações (Cód ONS) cada empresa possui no seu dataset.

SELECT
    e.cod_ons,
    e.tensao_kv,
    emp.nome_empresa
FROM
    anotacao e
JOIN
    empresas emp ON e.id_conexao = emp.id_empresa
LIMIT 20;


-- Query 2: Análise de Dados - Média de Valor de Ponta em 2025 por Empresa
--Objetivo: Calcular a média do valor MUST de ponta para o ano de 2025, agrupado por empresa. Esta query usa as 3 tabelas e mostra o poder da normalização.

SELECT
    emp.nome_empresa,
    COUNT(vm.valor) AS media_valor_ponta_2025
FROM
    valores_must vm
JOIN
    anotacao eq ON vm.id_conexao = eq.id_empresa
JOIN
    empresas emp ON eq.id_empresa = emp.id_empresa
WHERE
    vm.ano = 2025 AND vm.periodo = 'ponta'
GROUP BY
    emp.nome_empresa
ORDER BY
    media_valor_ponta_2025 DESC;

-- Query 3: Encontrar Anotações Gerais para um Equipamento Específico
-- Objetivo: Buscar rapidamente a anotação geral associada a um Cód ONS.

SELECT
    cod_ons,
    anotacao_geral
FROM
    anotacao
WHERE
    cod_ons = 'SPBRP-138'; -- Substitua pelo código que quer pesquisar


-- Query 4: Histórico (O que aconteceu?)
-- Pergunta: "Como o valor MUST do equipamento 'SPBRP-138' evoluiu nos últimos anos?"
-- Componente do Dashboard: Um gráfico de linhas que o usuário pode filtrar por cod_ons, mostrando a evolução dos valores ao longo dos anos.

SELECT ano, periodo, valor FROM valores_must
WHERE id_conexao = (SELECT id_conexao FROM anotacao WHERE cod_ons = 'SPBRP-138');

-- Query 5: Planejamento (O que vai acontecer?)
-- Pergunta: "Quais são os 10 anotacoes com o maior custo projetado (MUST) para 2025, e quem são seus donos?"
-- Componente do Dashboard: Uma tabela de "Top 10" mostrando nome_empresa, cod_ons e valor, filtrada para o ano de 2025 ate 2028.

SELECT
    emp.nome_empresa,
    eq.cod_ons,
    vm.valor
FROM
    valores_must AS vm
JOIN
    anotacao AS eq ON vm.id_conexao = eq.id_conexao
JOIN
    empresas AS emp ON eq.id_empresa = emp.id_empresa
WHERE
    vm.ano = 2025 AND vm.periodo = 'ponta'
ORDER BY
    vm.valor DESC
LIMIT 10; 


-- Query 6: Controle (O que precisamos saber agora?)
-- Pergunta: "Preciso ver todas as informações e a anotação geral sobre o equipamento 'SPBRP-138'. Onde encontro isso?"
-- Componente do Dashboard: Uma caixa de busca principal. O usuário digita o cod_ons e o dashboard exibe um "cartão de detalhes" com as informações da tabela equipamentos (incluindo a anotacao_geral) e uma tabela com todos os seus valores_must.

SELECT * FROM anotacao WHERE cod_ons = 'SPBRP-138';