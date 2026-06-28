from __future__ import annotations

import pytest
from app.infrastructure.factories.chat_model import create_chat_model
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama

from tests.settings_helpers import make_test_settings


def test_defaults_to_ollama_provider() -> None:
    model = create_chat_model(make_test_settings())

    assert isinstance(model, ChatOllama)
    assert model.model == "llama3.1"


def test_builds_groq_model_when_provider_is_groq() -> None:
    settings = make_test_settings(
        llm_provider="groq",
        groq_api_key="gsk-test",
        groq_model="llama-3.3-70b-versatile",
    )

    model = create_chat_model(settings)

    assert isinstance(model, ChatGroq)
    assert model.model_name == "llama-3.3-70b-versatile"


def test_groq_without_api_key_raises_clear_error() -> None:
    settings = make_test_settings(llm_provider="groq")

    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        create_chat_model(settings)
