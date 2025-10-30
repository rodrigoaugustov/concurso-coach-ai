import pytest
from unittest.mock import MagicMock, patch
from pydantic import BaseModel
from app.core.ai_service import LangChainService


class DummySchema(BaseModel):
    value: int


@patch("app.core.ai_service.ChatGoogleGenerativeAI")
def test_generate_structured_output_from_content_error_propagates(mock_chat):
    service = LangChainService(provider="google", api_key="k", model_name="gemini-2.5-pro")

    chain = MagicMock()
    chain.invoke.side_effect = RuntimeError("boom-multimodal")
    service.llm.with_structured_output.return_value = chain

    with pytest.raises(RuntimeError):
        service.generate_structured_output_from_content(
            content_parts=[{"type": "text", "text": "hello"}],
            response_schema=DummySchema,
        )


@patch("app.core.ai_service.ChatGoogleGenerativeAI")
def test_invoke_with_history_error_propagates(mock_chat):
    service = LangChainService(provider="google", api_key="k", model_name="gemini-2.5-pro")

    chain = MagicMock()
    chain.invoke.side_effect = RuntimeError("boom-history")
    service.llm.with_structured_output.return_value = chain

    with pytest.raises(RuntimeError):
        service.invoke_with_history(messages=[{"role": "user", "content": "hi"}], response_schema=DummySchema)
