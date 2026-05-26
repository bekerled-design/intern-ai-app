import json
import numpy as np


def cosine_similarity(vector_a, vector_b):

    a = np.array(vector_a)
    b = np.array(vector_b)

    return np.dot(a, b) / (
        np.linalg.norm(a) * np.linalg.norm(b)
    )


def search_similar_chunks(question_embedding, chunks, limit=5):

    scored_chunks = []

    for file_name, chunk_text, embedding_json in chunks:

        if not embedding_json:
            continue

        chunk_embedding = json.loads(embedding_json)

        score = cosine_similarity(
            question_embedding,
            chunk_embedding
        )

        scored_chunks.append(
            (score, file_name, chunk_text)
        )

    scored_chunks.sort(
        reverse=True,
        key=lambda item: item[0]
    )

    return scored_chunks[:limit]