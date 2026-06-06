import json

from utils.usage_tracker import record_embedding_usage


def create_embedding(client, text, user_id=None):

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )

    if user_id is not None:
        record_embedding_usage(user_id, "text-embedding-3-small", response)

    embedding = response.data[0].embedding

    return json.dumps(embedding)