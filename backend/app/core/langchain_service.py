from __future__ import annotations
from typing import Dict, Type, Optional
from pydantic import BaseModel
from langchain_core.runnables import Runnable
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.output_parsers import PydanticOutputParser
from langchain.output_parsers.retry import RetryWithErrorOutputParser

from .settings import settings
from .logging import get_logger

class LangChainService:
    """Factory de chains LangChain-first com cache e helpers async."""
    def __init__(self):
        self.logger = get_logger("langchain_service")
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-pro",
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.2,
        )
        self._chain_cache: Dict[str, Runnable] = {}

    def chain_key(self, template: ChatPromptTemplate, schema: Optional[Type[BaseModel]]) -> str:
        return f"{id(template)}::{getattr(schema, '__name__', 'raw')}"

    def create_chain(self, template: ChatPromptTemplate, schema: Optional[Type[BaseModel]] = None) -> Runnable:
        key = self.chain_key(template, schema)
        if key in self._chain_cache:
            return self._chain_cache[key]

        if schema:
            parser = PydanticOutputParser(pydantic_object=schema)
            chain: Runnable = template | self.llm | parser
        else:
            chain = template | self.llm

        self._chain_cache[key] = chain
        return chain

    def create_self_correcting_chain(self, template: ChatPromptTemplate, schema: Type[BaseModel]) -> Runnable:
        parser = PydanticOutputParser(pydantic_object=schema)
        retrying_parser = RetryWithErrorOutputParser.from_llm(
            parser=parser, llm=self.llm, max_retries=3
        )
        return template | self.llm | retrying_parser
