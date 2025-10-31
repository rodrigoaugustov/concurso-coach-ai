from __future__ import annotations
from typing import List
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from app.core.langchain_service import LangChainService
from app.core.prompt_templates import ChatPromptTemplate, TUTOR_SYSTEM_TEMPLATE

class SuggestionsModel(BaseModel):
    suggestions: List[str] = Field(min_length=2, max_length=5)

class SuggestionsService:
    def __init__(self):
        self.lc = LangChainService()
        # Template dedicado para gerar apenas sugestões curtas e acionáveis
        self.template = ChatPromptTemplate.from_messages([
            ("system", """Você é um tutor que gera sugestões de próximas ações para continuar uma aula.\nRetorne de 2 a 4 sugestões curtas, imperativas, em português, adequadas ao último conteúdo do assistente.\nSomente retorne JSON com a chave 'suggestions'."""),
            ("human", """Última mensagem do assistente:\n{assistant_message}\n\nContexto: tópico={topic_name}, proficiência={proficiency_level}/10, banca={banca}.""")
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
