from __future__ import annotations
from typing import Any
from langchain.prompts import ChatPromptTemplate

# Mantém prompts centralizados sem remover prompts existentes em outros módulos.
# Adição segura e reutilizável.

TOPIC_ANALYSIS_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", "Você é um coach de estudos especialista. Analise cada tópico e retorne JSON estruturado conforme o schema solicitado."),
    ("human", "Lista de tópicos (JSON):\n{topics_json}\n\nContexto: proficiência média {avg_proficiency}, sessões totais {total_sessions}.")
])

PLAN_ORGANIZATION_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", "Você é um planejador de estudos. Construa um roadmap sequencial respeitando pré-requisitos, intercalando matérias e limitando-se a {total_sessions} sessões."),
    ("human", "Tópicos analisados (JSON):\n{analyzed_topics_json}")
])

TUTOR_SYSTEM_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", "Você é o Concurso Coach AI, um tutor especialista em concursos.\nTópico: {topic_name}\nProficiência: {proficiency_level}/10\nBanca: {banca}\nInstruções: adapte o nível, explique claramente e sempre gere exatamente 3 sugestões de próximas ações."),
    ("placeholder", "{chat_history}"),
    ("human", "{input}")
])

EDICT_EXTRACTION_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", "Você é especialista em analisar editais. Extraia JSON estruturado de módulos, matérias e tópicos."),
    ("human", "Analise o conteúdo a seguir (texto extraído do PDF):\n{pdf_text}")
])

SUBJECT_REFINEMENT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", "Revise o JSON e corrija 'subject' genéricos para matérias específicas, mantendo estrutura idêntica."),
    ("human", "JSON extraído:\n{extracted_json}")
])
