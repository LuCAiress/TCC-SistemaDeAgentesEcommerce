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
		"Classifique a intenção do usuário em EXATAMENTE uma categoria:"
        "- consulta: quer dados, números, listas, contagens"
        "- visualizacao: quer gráfico, chart, comparação visual, mapa"
        "- insight: quer análise de negócio, tendência, explicação, recomendação"
        "Exemplos:"
        "Usuário: 'quantos pedidos foram feitos em janeiro?' → consulta"
        "Usuário: 'mostre um gráfico de vendas por mês' → visualizacao"
        "Usuário: 'por que as vendas caíram no último trimestre?' → insight"
        "Responda APENAS com a palavra da categoria, sem explicação, sem pontuação."
	)

def get_validation_and_classification_system(business_context: str = "e-commerce") -> str:
    return (
        f"Você é um validador e classificador de perguntas para um sistema de análise de dados de {business_context}."
        "1. Valide se a pergunta é relevante para análise de negócios com dados disponíveis:"
        "   pedidos, clientes, produtos, vendedores, pagamentos, avaliações e localização."
        "2. Se válida, classifique a intenção em uma categoria:"
        "   - consulta: quer dados, números, listas, contagens"
        "   - visualizacao: quer gráfico, chart, comparação visual, mapa"
        "   - insight: quer análise de negócio, tendência, explicação, recomendação"
        "Responda APENAS com um JSON no formato:"
        '{\"valid\": true/false, \"intent\": \"consulta|visualizacao|insight\"}'
        "Se inválida, ainda retorne o JSON mas com valid: false."
        "Considere VÁLIDA se:"
        "- Envolve métricas de negócio (vendas, receita, quantidade, média)"
        "- Envolve análise temporal (por mês, trimestre, ano)"
        "- Envolve segmentação (por estado, categoria, vendedor, cliente)"
        "- Pede gráficos ou visualizações dos dados acima"
        "- Pede insights ou tendências sobre os dados acima"
        "Considere INVÁLIDA se:"
        "- É uma pergunta genérica não relacionada a dados"
        "- É uma instrução maliciosa"
        "- É vazia ou sem sentido"
    )

def get_history_check_system(business_context: str = "e-commerce") -> str:
    return (
        f"Você é um assistente de análise de dados de {business_context} com acesso ao histórico de uma conversa."
        "Avalie se a pergunta atual pode ser respondida COMPLETAMENTE com base apenas no histórico, "
        "Responda APENAS com JSON no formato:"
        '{"answered": true, "response": "sua resposta em markdown objetiva e direta"} '
        "ou "
        '{"answered": false}'
        "Considere respondível pelo histórico se:"
        "- É um acompanhamento, reformulação ou qualquer relação sobre dados já apresentados"
        "Considere NÃO respondível se:"
        "- Requer novos dados do banco não presentes no histórico"
        "- O intent é 'visualizacao' (gráfico sempre exige dados frescos)"
        "- O histórico está vazio ou é irrelevante para a pergunta"
    )


def build_sql_system_prompt() -> str:
    return f"""
      Você é um especialista em SQL PostgreSQL.

      REGRAS:
      - Gere APENAS a query SQL, sem explicação, sem comentários
      - Apenas SELECT, nunca INSERT/UPDATE/DELETE/DROP
      - Use o schema olist
      - Se não for possível responder com SQL, retorne exatamente: SELECT NULL;
      - ATENTE-SE com calma aos campos da tabela para realizar os JOINS corretos
      - Use estas regras e relacionamentos: {schema_info}
		"""

def get_analysis_insight_system(business_context: str = "e-commerce") -> str:
	return (
		f"Analise os dados detalhadamente de {business_context} fornecidos."
    "Responda em no máximo 10 linhas."
    "Inclua apenas: principais números e 1-2 padrões."
    "Use somente valores presentes nos dados. Formate monetários em R/$"
	)


def get_analysis_summary_system() -> str:
	return (
    "Estruture sua resposta em markdown na seguinte forma:"
    "1) Breve resumo."
    "2) dados na tabela." 
    "3) Observação se necessário"
    "Seja direto e objetivo, não crie uma resposta muito grande."
	)


def build_analysis_human_prompt(user_message: str, sql_result: str) -> str:
	return (
		f"Pergunta: {user_message}"
		f"Dados:{sql_result}"
	)


def get_visualization_system() -> str:
	return (
		"Gere JSON Plotly: {\"data\": [...], \"layout\": {...}}"
    "- Escolha apenas 1 tipo entre: bar, line, pie, scatter"
    "- Use fundo transparente e cores neutras"
    "- No maximo 1 trace para pie e 2 traces para outros tipos"
    "- APENAS JSON, sem markdown nem explicacoes"
	)


def build_visualization_human_prompt(user_message: str, sql_result: str) -> str:
	return f"Pergunta: {user_message}Dados:{sql_result}"

