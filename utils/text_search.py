def split_text_into_chunks(text, chunk_size=3000, overlap=500):

    chunks = []

    start = 0

    while start < len(text):

        end = start + chunk_size

        chunk = text[start:end]

        if chunk.strip():
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


def search_relevant_chunks(question, chunks, limit=3):
    question_words = set(question.lower().split())

    scored_chunks = []

    for chunk in chunks:
        chunk_words = set(chunk.lower().split())

        score = len(question_words.intersection(chunk_words))

        scored_chunks.append((score, chunk))

    scored_chunks.sort(reverse=True, key=lambda x: x[0])

    best_chunks = [
        chunk for score, chunk in scored_chunks[:limit]
        if score > 0
    ]

    if not best_chunks:
        return chunks[:limit]

    return best_chunks