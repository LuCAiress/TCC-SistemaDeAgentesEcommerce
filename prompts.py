schema_info = f"""TABELAS E COLUNAS:

Tabela: olist.customers
- customer_id: identificador único do cliente
- customer_unique_id: identificador único global do cliente
- zip_code_prefix: prefixo do CEP
- city: cidade do cliente
- state: estado do cliente

Tabela: olist.orders
- order_id: identificador do pedido
- customer_id: id do cliente
- status: status do pedido (delivered, shipped, etc)
- purchase_timestamp: data da compra
- approval_timestamp: data de aprovação do pedido
- delivered_carrier_date: data de envio ao transportador
- delivered_customer_date: data de entrega ao cliente
- estimated_delivery_date: data estimada de entrega

Tabela: olist.order_payments
- order_id: id do pedido
- payment_sequential: sequência do pagamento
- payment_type: tipo de pagamento (credit_card, boleto, voucher, etc)
- payment_installments: número de parcelas
- payment_value: valor pago

Tabela: olist.order_items
- order_id: id do pedido
- item_id: número do item no pedido
- product_id: id do produto
- seller_id: id do vendedor
- shipping_limit_date: data limite de envio
- price: preço do produto
- freight_value: valor do frete

Tabela: olist.products
- product_id: id do produto
- product_category: categoria do produto
- name_length: tamanho do nome
- description_length: tamanho da descrição
- photos_quantity: quantidade de fotos
- weight_g: peso em gramas
- length_cm: comprimento
- height_cm: altura
- width_cm: largura

Tabela: olist.sellers
- seller_id: identificador do vendedor
- zip_code_prefix: prefixo do CEP
- city: cidade do vendedor
- state: estado do vendedor

Tabela: olist.order_reviews
- review_id: id da avaliação
- order_id: id do pedido
- rating: nota da avaliação (1 a 5)
- review_title: título da avaliação
- review_content: conteúdo da avaliação
- creation_timestamp: data de criação
- answer_timestamp: data de resposta

Tabela: olist.geolocation
- zip_code_prefix: prefixo do CEP
- latitude: latitude
- longitude: longitude
- city: cidade
- state: estado


RELACIONAMENTOS ENTRE TABELAS:

- olist.orders.customer_id = olist.customers.customer_id
  → pedidos pertencem a clientes

- olist.order_payments.order_id = olist.orders.order_id
  → pagamentos estão ligados a pedidos

- olist.order_reviews.order_id = olist.orders.order_id
  → avaliações estão ligadas a pedidos

- olist.order_items.order_id = olist.orders.order_id
  → itens pertencem a pedidos

- olist.order_items.product_id = olist.products.product_id
  → itens possuem produtos

- olist.order_items.seller_id = olist.sellers.seller_id
  → itens possuem vendedores

- olist.customers.zip_code_prefix = olist.geolocation.zip_code_prefix
  → localização do cliente

- olist.sellers.zip_code_prefix = olist.geolocation.zip_code_prefix
  → localização do vendedor


REGRAS DE NEGÓCIO E USO:

- Para calcular vendas → usar order_payments.payment_value
- Para dados de tempo → usar orders.purchase_timestamp
- Para análise por cliente → usar customers
- Para análise por produto → usar order_items + products
- Para análise por vendedor → usar sellers
- Para localização → usar customers ou sellers + geolocation

- Sempre que envolver tempo (mensal, anual, tendência):
  → usar DATE_TRUNC('month', orders.purchase_timestamp)

- Sempre que a pergunta contiver "por":
  → usar GROUP BY

- Para métricas:
  - total → SUM()
  - média → AVG()
  - quantidade → COUNT()

- Sempre ordenar resultados temporais com ORDER BY"""

def get_intent_classification_system() -> str:
	return (
		"Classifique a intenção do usuário em EXATAMENTE uma categoria:\n"
		"- consulta: quer dados, números, listas, contagens\n"
		"- visualizacao: quer gráfico, chart, comparação visual, mapa\n"
		"- insight: quer análise de negócio, tendência, explicação, recomendação\n\n"
		"Responda APENAS com a palavra da categoria, sem explicação."
	)


def build_sql_system_prompt() -> str:
    return f"""
		Você é um especialista em SQL PostgreSQL.

		Gere APENAS a query SQL correta.

		REGRAS:
		- Apenas SELECT
		- Use o schema olist
		- Use as regras e relacionamentos abaixo

		{schema_info}
"""

def get_analysis_insight_system() -> str:
	return (
		"Você é um analista de negócios sênior de e-commerce. "
		"Com base nos dados reais do banco, forneça:\n"
		"1. **Interpretação** dos números\n"
		"2. **Tendências ou padrões** identificados\n"
		"3. **Possíveis causas** para os resultados\n"
		"4. **Recomendações** de ação para o negócio\n\n"
		"Seja específico e baseie-se nos dados. Não invente informações."
	)


def get_analysis_summary_system() -> str:
	return (
		"Resuma os resultados da consulta SQL de forma clara e objetiva. "
		"Formate dados tabulares como tabela Markdown quando apropriado."
	)


def build_analysis_human_prompt(user_message: str, sql_query: str, sql_result: str) -> str:
	return (
		f"Pergunta do usuário: {user_message}\n\n"
		f"SQL executada:\n```sql\n{sql_query}\n```\n\n"
		f"Resultado:\n{sql_result}"
	)


def get_visualization_system() -> str:
	return (
		"Gere um JSON válido de especificação Plotly para visualizar os dados.\n"
		'O JSON deve ser: {"data": [...], "layout": {...}}\n'
		"Use tipos adequados: bar, line, pie, scatter, etc.\n"
		"Responda APENAS com o JSON, sem texto ao redor."
	)


def build_visualization_human_prompt(user_message: str, sql_result: str) -> str:
	return (
		f"Pergunta: {user_message}\n\n"
		f"Dados:\n{sql_result}"
	)

