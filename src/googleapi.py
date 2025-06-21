from google import genai
from google.genai.types import EmbedContentConfig

from .config import settings

client = genai.Client(api_key=settings.GOOGLE_AI_STUDIO_API_KEY)


def get_embeddings(content):
    response = client.models.embed_content(
        model="gemini-embedding-exp-03-07",
        contents=content,
        config=EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=3072,
        ),
    )
    return response
