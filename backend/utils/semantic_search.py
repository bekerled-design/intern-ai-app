import json
import numpy as np
import re

def cosine_similarity(vector_a, vector_b):

    a = np.array(vector_a)
    b = np.array(vector_b)

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0

    return np.dot(a, b) / (norm_a * norm_b)


def search_similar_chunks(
    question,
    question_embedding,
    chunks,
    limit=10
):

    scored_chunks = []

    for file_name, chunk_text, embedding_json in chunks:

        if not embedding_json:
            continue

        chunk_embedding = json.loads(embedding_json)

        semantic_score = cosine_similarity(
            question_embedding,
            chunk_embedding
        )

        keyword_points = keyword_score(
            question,
            chunk_text
        )

        final_score = semantic_score + (keyword_points * 0.05)

        scored_chunks.append(
            (
                final_score,
                semantic_score,
                keyword_points,
                file_name,
                chunk_text
            )
        )

    scored_chunks.sort(
        reverse=True,
        key=lambda item: item[0]
    )

    return scored_chunks[:limit]

def keyword_score(question, text):

    question_words = re.findall(
        r"[а-яА-Яa-zA-Z0-9]+",
        question.lower()
    )

    text_words = re.findall(
        r"[а-яА-Яa-zA-Z0-9]+",
        text.lower()
    )

    text_joined = " ".join(text_words)

    score = 0

    for word in question_words:

        if len(word) <= 3:
            continue

        if word in text_joined:
            score += 1

        root = word[:5]

        if len(root) >= 4 and root in text_joined:
            score += 0.5

    return score