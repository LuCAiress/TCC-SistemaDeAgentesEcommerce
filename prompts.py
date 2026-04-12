def get_intent_classification_system() -> str:
	return (
		"Classifique a intenção do usuário em EXATAMENTE uma categoria:\n"
		"- consulta: quer dados, números, listas, contagens\n"
		"- visualizacao: quer gráfico, chart, comparação visual, mapa\n"
		"- insight: quer análise de negócio, tendência, explicação, recomendação\n\n"
		"Responda APENAS com a palavra da categoria, sem explicação."
	)


def build_sql_system_prompt(schema_info: str) -> str:
	return (
		"Você é um especialista em SQL PostgreSQL.\n"
		"Gere APENAS a query SQL (sem explicação) para responder à pergunta.\n"
		"Use apenas SELECT (read-only). Nunca use DELETE, UPDATE, INSERT, DROP.\n\n"
  		"O schema das tabelas é o olist. Exemplo: olist.orders, olist.customers, etc.\n"
		f"Schema do banco:\n{schema_info}"
	)


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

