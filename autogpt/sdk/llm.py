import openai

"""
from openai.api_resources import (
    Audio,
    ChatCompletion,
    Completion,
    Embedding,
    Image,
    Moderation,
)

"""

def set_openai_defaults(key: str, base: str):
    openai.api_key = key
    openai.api_base = base
