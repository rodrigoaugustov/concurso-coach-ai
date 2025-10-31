from __future__ import annotations
from typing import List
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from app.core.langchain_service import LangChainService
from app.core.prompt_templates import ChatPromptTemplate

class SuggestionsModel(BaseModel):
    suggestions: List[str] = Field(min_length=2, max_length=5)

class SuggestionsService:
    """Serviço exclusivo do chat para gerar sugestões com IA. Não afeta outros fluxos."""
    def __init__(self):
        self.lc = LangChainService()
        self.template = ChatPromptTemplate.from_messages([
            ("system", "Retorne de 2 a 4 sugestões curtas, imperativas, em português, em JSON na chave 'suggestions'."),
            ("human", "Última mensagem do assistente:\n{assistant_message}\n\nContexto: tópico={topic_name}, proficiência={proficiency_level}/10, banca={banca}.")
        ])
        self.chain = self.lc.create_chain(self.template, SuggestionsModel)

    async def generate(self, assistant_message: str, topic_name: str, proficiency_level: int, banca: str | None) -> List[str]:
        result: SuggestionsModel = await self.chain.ainvoke({
            "assistant_message": assistant_message,
            "topic_name": topic_name,
            "proficiency_level": proficiency_level,
            "banca": banca or "Genérica",
        })
        return result.suggestions
