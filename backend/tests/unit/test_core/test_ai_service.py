import os
import pytest
from pydantic import BaseModel
from unittest.mock import MagicMock, patch

from app.core.ai_service import LangChainService


class DummySchema(BaseModel):
    value: int


@pytest.fixture(autouse=True)
def ensure_env(monkeypatch):
    # Não é necessário GEMINI_API_KEY aqui pois chamado é mockado
    monkeypatch.setenv("PYTHONHASHSEED", "0")


def test_init_invalid_provider():
    with pytest.raises(ValueError):
        LangChainService(provider="invalid", api_key="k", model_name="m")


@patch("app.core.ai_service.ChatGoogleGenerativeAI")
def test_generate_structured_output_success(mock_chat):
    service = LangChainService(provider="google", api_key="k", model_name="gemini-2.5-pro")

    # Mock chain
    structured = MagicMock()
    structured.invoke.return_value = DummySchema(value=42)

    # Mock llm.with_structured_output
    service.llm.with_structured_output.return_value = structured

    out = service.generate_structured_output(
        prompt_template="You are a test. Return {x}",
        prompt_input={"x": 42},
        response_schema=DummySchema,
    )

    assert isinstance(out, DummySchema)
    assert out.value == 42


@patch("app.core.ai_service.ChatGoogleGenerativeAI")
def test_generate_structured_output_error_propagates(mock_chat):
    service = LangChainService(provider="google", api_key="k", model_name="gemini-2.5-pro")

    structured = MagicMock()
    structured.invoke.side_effect = RuntimeError("boom")
    service.llm.with_structured_output.return_value = structured

    with pytest.raises(RuntimeError):
        service.generate_structured_output(
            prompt_template="Return {x}",
            prompt_input={"x": 1},
            response_schema=DummySchema,
        )


@patch("app.core.ai_service.ChatGoogleGenerativeAI")
def test_generate_structured_output_from_content_success(mock_chat):
    service = LangChainService(provider="google", api_key="k", model_name="gemini-2.5-pro")

    chain = MagicMock()
    chain.invoke.return_value = DummySchema(value=7)
    service.llm.with_structured_output.return_value = chain

    out = service.generate_structured_output_from_content(
        content_parts=[{"type": "text", "text": "hello"}],
        response_schema=DummySchema,
    )

    assert isinstance(out, DummySchema)
    assert out.value == 7


@patch("app.core.ai_service.ChatGoogleGenerativeAI")
def test_invoke_with_history_success(mock_chat):
    service = LangChainService(provider="google", api_key="k", model_name="gemini-2.5-pro")

    chain = MagicMock()
    chain.invoke.return_value = DummySchema(value=9)
    service.llm.with_structured_output.return_value = chain

    out = service.invoke_with_history(messages=[{"role": "user", "content": "hi"}], response_schema=DummySchema)
    assert out.value == 9
