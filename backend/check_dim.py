from app.rag.embedding import get_embedding_model, encode_text, encode_query

model = get_embedding_model()
print(f'Model: {model.model_name}')
print(f'Dimension: {model.dimension}')

text_emb = encode_text(['test text'])
query_emb = encode_query('test query')
print(f'encode_text dim: {len(text_emb[0])}')
print(f'encode_query dim: {len(query_emb)}')
