from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama

from app.config.settings import Settings, get_settings


def create_chat_model(settings: Settings | None = None) -> BaseChatModel:
    resolved = settings or get_settings()
    return ChatOllama(
        model=resolved.ollama_model,
        base_url=resolved.ollama_base_url,
        temperature=0,
    )
