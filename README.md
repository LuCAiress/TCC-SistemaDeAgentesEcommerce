# Sistema de Análise de Dados com Agente Conversacional

> **Projeto Destaque UniCeub 2026 — Categoria Tecnologia**

Sistema de análise de dados de negócios baseado em um agente conversacional capaz de interpretar perguntas em linguagem natural e convertê-las automaticamente em consultas SQL, retornando métricas e visualizações interativas sobre dados de e-commerce.

---

## Reconhecimento

Este projeto foi premiado na categoria **Tecnologia** do **Prêmio Destaque UniCeub 2026**, concedido pelo Centro Universitário de Brasília (CEUB) ao melhor Trabalho de Conclusão de Curso da área.

---

## Funcionalidades

- **Agente de Análise** — interação conversacional em linguagem natural com geração automática de SQL e visualizações via Plotly
- **Console SQL** — execução direta de consultas `SELECT` com visualização do esquema do banco
- **Dashboard** — painéis analíticos pré-configurados com KPIs de Vendas, Pedidos, Logística, Satisfação e Vendedores
- **Autenticação** — controle de acesso com perfis `user` e `admin`, senhas armazenadas com hash `bcrypt`
- **Observabilidade** — rastreamento completo das execuções do agente via MLflow

---

## Pré-requisitos

- [Python 3.10+](https://www.python.org/)
- [PostgreSQL](https://www.postgresql.org/)
- [Ollama](https://ollama.com/) com pelo menos um modelo instalado
- [MLflow](https://mlflow.org/) *(opcional — para visualização dos traces)*

---

## Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/LuCAiress/TCC-SistemaDeAgentesEcommerce.git
cd TCC-SistemaDeAgentesEcommerce
```

### 2. Crie e ative um ambiente virtual

```bash
python -m venv venv

# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

Copie o arquivo de exemplo e preencha com suas configurações:

```bash
cp .env.example .env
```

Edite o arquivo `.env`:

```dotenv
DATABASE_URL=postgresql://usuario:senha@localhost:5432/nome_do_banco
OLLAMA_MODEL=qwen3.5:9b               # ou outro modelo instalado no Ollama
LANGCHAIN_TRACING_V2=false
MLFLOW_TRACKING_URI=file:./mlruns
MLFLOW_EXPERIMENT_NAME=tcc_agente
AUTH_SCHEMA=public                    # schema onde está a tabela de usuários
AUTH_TABLE=users                      # nome da tabela de usuários
AUTH_USER_FIELD=email                 # campo de e-mail
AUTH_PASSWORD_FIELD=password          # campo de senha
AUTH_ROLE_FIELD=role                  # campo de perfil (user/admin)
```

### 5. Configure o banco de dados

Certifique-se de que o PostgreSQL está em execução e que o banco configurado em `DATABASE_URL` existe. Carregue o dataset da Olist nas tabelas correspondentes (`orders`, `customers`, `products`, `order_items`, `order_payments`, `order_reviews`, `sellers`, `geolocation`).

O dataset pode ser obtido em: [Brazilian E-Commerce — Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)

### 6. Crie a tabela de usuários

A tabela de usuários deve ser criada manualmente no banco antes de iniciar o sistema. Execute o comando abaixo no PostgreSQL, ajustando os nomes conforme as variáveis definidas no seu `.env`:

```sql
CREATE TABLE public.users (
    id       SERIAL PRIMARY KEY,
    email    VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role     VARCHAR(50)  NOT NULL DEFAULT 'user'
);
```

Em seguida, insira um usuário administrador inicial. A senha deve ser gerada com hash `bcrypt` — você pode usar o script abaixo em Python:

```python
import bcrypt
senha = bcrypt.hashpw("sua_senha".encode(), bcrypt.gensalt()).decode()
print(senha)
```

Depois insira o usuário no banco:

```sql
INSERT INTO public.users (email, password, role)
VALUES ('admin@email.com', '<hash_gerado>', 'admin');
```

### 7. Inicie o servidor Ollama

```bash
ollama serve
```

Certifique-se de que o modelo configurado em `OLLAMA_MODEL` está disponível:

```bash
ollama pull qwen3.5:9b
```

---

## Executando o sistema

```bash
streamlit run app.py
```

O sistema estará disponível em `http://localhost:8501`.

---

## Estrutura do projeto

```
├── app.py                  # Ponto de entrada da aplicação Streamlit
├── graph.py                # Grafo de estados do agente (LangGraph)
├── prompts.py              # Prompts utilizados nos nós do agente
├── tools.py                # Ferramentas auxiliares do agente
├── utils.py                # Funções utilitárias
├── salvar_grafo.py         # Script para exportar imagem do grafo
├── pages/
│   ├── agente_analise.py   # Página do agente conversacional
│   ├── pagina_consulta.py  # Console SQL
│   ├── dashboard.py        # Dashboard analítico
│   ├── home.py             # Página inicial
│   ├── login.py            # Autenticação
│   └── admin.py            # Administração de usuários
├── data/                   # Diretório para os arquivos do dataset
├── images/                 # Imagens utilizadas na interface
├── requirements.txt
└── .env.example
```

---

## Observabilidade

As execuções do agente são registradas automaticamente no MLflow. Para visualizar os traces:

```bash
mlflow ui
```

O painel estará disponível em `http://localhost:5000`.

---

## Autores

- Lucas Lima Aires — [lucas.l.aires@gmail.com](mailto:lucas.l.aires@gmail.com)
- Pedro Paulo de Avelar Fioresi Gadioli — [pedrogadioli@gmail.com](mailto:pedrogadioli@gmail.com)

Orientador: Prof. Me. Fábio Oliveira Guimarães  
Centro Universitário de Brasília — CEUB, 2026
