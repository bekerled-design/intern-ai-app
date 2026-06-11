import json

from utils.usage_tracker import record_embedding_usage
from config import EMBEDDING_MODEL


def create_embedding(client, text, user_id=None, company_id=None):

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )

    if user_id is not None:
        record_embedding_usage(user_id, EMBEDDING_MODEL, response,
                               company_id=company_id)

    embedding = response.data[0].embedding

    return json.dumps(embedding)