# import chromadb
# import hashlib
# import json
# import time
# from chromadb.utils import embedding_functions

# client = chromadb.PersistentClient(path="./chroma")

# # Embedding function padrão (all-MiniLM-L6-v2 embutido)
# emb_fn = embedding_functions.DefaultEmbeddingFunction()

# sql_cache = client.get_or_create_collection(
#     name="sql_cache",
#     embedding_function=emb_fn,
#     metadata={"hnsw:space": "cosine"},  # distância coseno
# )

# sql_results = client.get_or_create_collection(
#     name="sql_results",
#     embedding_function=emb_fn,
# )

# SIMILARITY_THRESHOLD = 0.08   # distância coseno (0 = idêntico, < 0.1 = muito similar)
# RESULT_TTL_SECONDS   = 900    # 15 min para resultados do banco
# SQL_TTL_SECONDS      = 3600   # 1h para o SQL gerado


# def _hash(text: str) -> str:
#     return hashlib.sha256(text.strip().lower().encode()).hexdigest()


# # ── Cache semântico: pergunta → sql_query ─────────────────────

# def semantic_get(question: str) -> tuple[str | None, str | None]:
#     """
#     Busca perguntas similares. Retorna (sql_query, cached_result) se hit.
#     cached_result pode ser None se só o SQL foi cacheado.
#     """
#     results = sql_cache.query(
#         query_texts=[question],
#         n_results=1,
#         include=["metadatas", "distances"],
#     )

#     if not results["ids"][0]:
#         return None, None

#     distance = results["distances"][0][0]
#     if distance > SIMILARITY_THRESHOLD:
#         return None, None  # miss semântico

#     meta = results["metadatas"][0][0]

#     # Verifica TTL manualmente (ChromaDB não tem TTL nativo)
#     if time.time() - meta.get("created_at", 0) > SQL_TTL_SECONDS:
#         sql_cache.delete(ids=[results["ids"][0][0]])
#         return None, None

#     sql_query = meta.get("sql_query")

#     # Tenta buscar resultado cacheado para esse SQL
#     cached_result = result_get(sql_query) if sql_query else None

#     return sql_query, cached_result


# def semantic_set(question: str, sql_query: str, tables: list[str] = None):
#     """Salva pergunta + SQL gerado na collection semântica."""
#     doc_id = _hash(question)
#     sql_cache.upsert(
#         ids=[doc_id],
#         documents=[question],
#         metadatas=[{
#             "sql_query":  sql_query,
#             "tables":     json.dumps(tables or []),
#             "created_at": time.time(),
#         }],
#     )


# # ── Cache de resultado: sql_query → rows ──────────────────────

# def result_get(sql_query: str) -> list | None:
#     """Busca resultado de uma query SQL exata (lookup por id)."""
#     try:
#         res = sql_results.get(
#             ids=[_hash(sql_query)],
#             include=["metadatas"],
#         )
#     except Exception:
#         return None

#     if not res["ids"]:
#         return None

#     meta = res["metadatas"][0]
#     if time.time() - meta.get("created_at", 0) > RESULT_TTL_SECONDS:
#         sql_results.delete(ids=[_hash(sql_query)])
#         return None

#     return json.loads(meta.get("result", "null"))


# def result_set(sql_query: str, result: list):
#     """Salva resultado de uma query SQL."""
#     sql_results.upsert(
#         ids=[_hash(sql_query)],
#         documents=[sql_query],
#         metadatas=[{
#             "result":     json.dumps(result),
#             "created_at": time.time(),
#         }],
#     )


# # ── Invalidação por tabela ─────────────────────────────────────

# def invalidate_table(table_name: str):
#     """
#     Remove do cache todas as queries que tocam em 'table_name'.
#     Útil quando dados da tabela mudam (ex: novo insert em pedidos).
#     """
#     results = sql_cache.get(include=["metadatas", "ids"])
#     ids_to_delete = []

#     for doc_id, meta in zip(results["ids"], results["metadatas"]):
#         tables = json.loads(meta.get("tables", "[]"))
#         if table_name in tables:
#             ids_to_delete.append(doc_id)
#             # Tenta remover resultado associado
#             try:
#                 sql_results.delete(ids=[_hash(meta["sql_query"])])
#             except Exception:
#                 pass

#     if ids_to_delete:
#         sql_cache.delete(ids=ids_to_delete)
#         print(f"[cache] {len(ids_to_delete)} entradas invalidadas para tabela '{table_name}'")