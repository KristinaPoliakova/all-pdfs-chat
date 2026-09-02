from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from pydantic import SecretStr

from app.config.settings import Settings, get_settings


def create_chat_model(settings: Settings | None = None) -> BaseChatModel:
    return _build_chat_model(settings or get_settings())


async def close_chat_model(model: BaseChatModel) -> None:
    # BaseChatModel has no public close API; reach into each provider's async
    # client to release its underlying HTTP connection pool.
    if isinstance(model, ChatGroq):
        await model.async_client._client.close()
    elif isinstance(model, ChatOllama):
        await model._async_client.close()


def _build_chat_model(cfg: Settings) -> BaseChatModel:
    if cfg.uses_groq:
        return _build_groq_model(cfg)

    return _build_ollama_model(cfg)


def _build_ollama_model(cfg: Settings) -> BaseChatModel:
    return ChatOllama(
        model=cfg.ollama_model,
        base_url=cfg.ollama_base_url,
        temperature=0,
    )


def _build_groq_model(cfg: Settings) -> BaseChatModel:
    api_key = (cfg.groq_api_key or "").strip()
    if not api_key:
        raise ValueError("GROQ_API_KEY is required when LLM_PROVIDER=groq")

    return ChatGroq(
        model=cfg.groq_model,
        api_key=SecretStr(api_key),
        temperature=0,
        max_retries=cfg.groq_max_retries,
    )
