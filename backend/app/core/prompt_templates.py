# LangChain-first prompt templates centralizados
from langchain.prompts import ChatPromptTemplate

# Study: análise de tópicos
TOPIC_ANALYSIS_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", """Você é um coach de estudos especialista. Analise cada tópico e retorne JSON estruturado conforme o schema solicitado."""),
    ("human", """Lista de tópicos (JSON):\n{topics_json}\n\nContexto: proficiência média {avg_proficiency}, sessões totais {total_sessions}.""")
])

# Study: organização do plano
PLAN_ORGANIZATION_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", """Você é um planejador de estudos. Construa um roadmap sequencial respeitando pré-requisitos, intercalando matérias e limitando-se a {total_sessions} sessões."""),
    ("human", """Tópicos analisados (JSON):\n{analyzed_topics_json}""")
])

# Study: tutor (aprendizagem guiada)
TUTOR_SYSTEM_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", """Você é o Concurso Coach AI, um tutor especialista em concursos.\nTópico: {topic_name}\nProficiência: {proficiency_level}/10\nBanca: {banca}\nInstruções: adapte o nível, explique claramente e sempre gere exatamente 3 sugestões de próximas ações."""),
    ("placeholder", "{chat_history}"),
    ("human", "{input}")
])

# Contests: extração de edital
EDICT_EXTRACTION_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", """Você é especialista em analisar editais. Extraia JSON estruturado de módulos, matérias (subjects) e tópicos (topics)."""),
    ("human", """Analise o conteúdo a seguir (texto extraído do PDF):\n{pdf_text}""")
])

# Contests: refinamento de subject
SUBJECT_REFINEMENT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", """Revise o JSON e corrija 'subject' genéricos para matérias específicas, mantendo estrutura idêntica."""),
    ("human", """JSON extraído:\n{extracted_json}""")
])
