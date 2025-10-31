"""
Centralized ChatPromptTemplate system for all AI prompts.
Migrates hardcoded prompts to reusable, parameterized templates.
"""
  
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Dict, Any


class PromptTemplateFactory:
    """
    Factory for creating and managing ChatPromptTemplate instances.
    Provides centralized access to all prompt templates with caching.
    """
    
    def __init__(self):
        self._templates: Dict[str, ChatPromptTemplate] = {}
        self._initialize_templates()
    
    def _initialize_templates(self):
        """Initialize all prompt templates."""
        
        # Study Templates
        self._templates["topic_analysis"] = ChatPromptTemplate.from_template(
            """
# MISSÃO
Você é um coach de estudos especialista. Sua missão é analisar CADA tópico de uma lista e retornar uma análise estruturada.

# DADOS DE ENTRADA
A seguir, você receberá uma lista de tópicos em formato JSON. Cada objeto na lista representa um tópico e contém:
- `topic_id`: O identificador numérico único, cada topic_name terá um topic_id único.
- `exam_module`: Nome do módulo da prova (ex: 'Conhecimentos Básicos').
- `subject`: Nome da matéria ou disciplina (ex: 'Língua Portuguesa').
- `topic_name`: Nome do tópico específico (ex: 'Concordância Verbal').
- `proficiency`: A proficiência atual do aluno no assunto (de 0.0 a 1.0).
- `subject_weight`: Peso que a matéria ou módulo representa na nota final da prova. (Quantidade de questões x peso por questão).

## LISTA DE TÓPICOS:
{topics_json}

# SUA TAREFA
Para CADA tópico na lista de entrada, forneça as seguintes análises:
1.  **priority_level:** Classifique o tópico em "Alta Prioridade", "Média Prioridade", ou "Baixa Prioridade", baseado na 'proficiency' e 'subject_weight'.
2.  **estimated_sessions:** Estime o número de sessões de 30 min necessárias. Cada Sessão de Foco tem 30 minutos de duração, sendo que cada sessão é um período de estudo otimizado para concentração total, utilizando recursos como mapas mentais, flashcards, e técnicas de revisão espaçada.
No fim de cada sessão é realizada uma breve avaliação para reforçar o aprendizado.
3.  **prerequisite_topic_ids:** Liste os 'topic_id's dos tópicos que são pré-requisitos diretos. Se não houver, retorne uma lista vazia. Por exemplo, 'Juros Simples' pode ser um pré-requisito para 'Juros Compostos'.

# FORMATO DA SAÍDA
Retorne SOMENTE um objeto JSON válido com uma chave "analyzed_topics", contendo uma lista de objetos, um para CADA tópico original.
            """
        )
        
        self._templates["plan_organization"] = ChatPromptTemplate.from_template(
            """
# MISSÃO
Você é um planejador de estudos especialista. Sua missão é criar um roadmap de estudo sequencial e otimizado a partir de uma lista de tópicos já analisados.

# DADOS DE ENTRADA
- Número total de "Sessões de Foco" disponíveis até a prova: {total_sessions}
- Lista de tópicos analisados (com prioridade, sessões estimadas e pré-requisitos). Não há uma ordem específica nesta lista:
{analyzed_topics_json}

# SUA TAREFA
Crie um roadmap sequencial de sessões de estudo. Ou seja, uma lista ordenada de sessões, onde cada sessão contém:
1.  **Ordenação:** A sequência DEVE respeitar os 'prerequisite_topic_ids'. Essa ordem vai representar a ordem ideal de estudo.
2.  **Intercalação:** Evite sequências seguidas longas da mesma matéria. Intercale o estudo de diferentes matérias. Defina no máximo 3 sessões consecutivas da mesma matéria, mesmo que isso signifique flexibilizar a prioridade.
3.  **Distribuição:** Distribua os tópicos ao longo do número de sessões disponíveis.
4.  **Agrupamento:** Se o número total de sessões necessárias exceder as {total_sessions} disponíveis, agrupe tópicos correlatos de "Baixa Prioridade" em uma única sessão. Para sessões agrupadas, a lista 'topic_ids' conterá múltiplos IDs. Também agrupe tópicos que sejam muito similares ou curtos demais para uma sessão completa. Mas sempre agrupe tópicos que façam sentido juntos.
5.  **Divisão:** Para os topicos que necessitam de mais de 1 sessão, se atente em criar a quantidade de sessões necessárias com aquele tópico.

# FORMATO DA SAÍDA
Retorne SOMENTE um objeto JSON válido com uma chave "roadmap", contendo a lista ordenada de sessões.
            """
        )
        
        self._templates["json_correction"] = ChatPromptTemplate.from_template(
            """
# CONTEXTO
Sua tarefa anterior resultou em um erro porque a sua resposta não foi um objeto JSON válido ou não correspondeu ao schema solicitado.

# ERRO ENCONTRADO
{error_message}

# RESPOSTA INVÁLIDA QUE VOCÊ GEROU
{invalid_response}

# SUA TAREFA
Por favor, corrija a sua resposta anterior. Você DEVE retornar SOMENTE o objeto JSON corrigido, sem nenhum outro texto ou explicação, e garantindo que ele corresponda perfeitamente ao schema solicitado na mensagem anterior.
            """
        )
        
        self._templates["procedural_layout"] = ChatPromptTemplate.from_template(
            """
# MISSÃO
Você é um designer instrucional... Sua missão é criar uma experiência de aprendizado...

# CONTEÚDO A SER ABORDADO
- {topics_list_str}

# SUA TAREFA
Projete a melhor sequência didática...
Sua resposta DEVE ser um objeto JSON com uma chave "layout".
"layout" é uma LISTA de objetos "LayoutItem".

Para CADA item na lista "layout", você deve:
1.  Definir o campo 'component_type' com o nome do componente que você está usando (ex: "TextBlock", "FlipCard", "Carousel", "Quiz").
2.  Preencher o campo correspondente a esse tipo (ex: 'text_block', 'flip_card', etc.) com os dados do componente.
3.  DEIXAR TODOS OS OUTROS campos de componente como nulos (null).

EXEMPLO DE UM 'LayoutItem' para um TextBlock:
{{
  "component_type": "TextBlock",
  "text_block": {{ "content_md": "Bem-vindo à sua Sessão de Foco!" }},
  "flip_card": null,
  "carousel": null,
  "quiz": null
}}

Comece com um 'TextBlock' de introdução e termine com um 'Quiz'. Varie os componentes no meio.
            """
        )
        
        # Guided Learning Templates - Multi-Agent System
        self._templates["teacher_supervisor"] = ChatPromptTemplate.from_messages([
            ("system", """
Você é o Professor Supervisor de um sistema de ensino especializado em concursos públicos.

Seu papel é:
1. Analisar mensagens do estudante e decidir qual agente especializado deve responder
2. Rotear para os agentes: 'explanation', 'example', 'quiz'
3. Garantir fluxo pedagógico coerente

Contexto da sessão:
- Tópico: {topic_name}
- Matéria: {subject}
- Proficiência do aluno: {proficiency}
- Banca: {banca}

Histórico de mensagens:
{history}

Mensagem atual do estudante: {message}

Decida qual agente deve responder e forneça instruções específicas.
            """),
            MessagesPlaceholder(variable_name="messages")
        ])
        
        self._templates["explanation_agent"] = ChatPromptTemplate.from_messages([
            ("system", """
Você é o Agente de Explicação, especialista em explicar conceitos de forma didática.

Seu papel:
- Explicar conceitos de forma clara e estruturada
- Usar linguagem apropriada ao nível do estudante
- Fornecer contexto e aplicações práticas
- Conectar com conhecimentos prévios

Contexto:
- Tópico: {topic_name}
- Matéria: {subject}
- Proficiência: {proficiency}/10
- Banca: {banca}

Instruções específicas do supervisor: {supervisor_instructions}
            """),
            MessagesPlaceholder(variable_name="messages")
        ])
        
        self._templates["example_agent"] = ChatPromptTemplate.from_messages([
            ("system", """
Você é o Agente de Exemplos, especialista em criar exemplos práticos e exercícios.

Seu papel:
- Criar exemplos claros e relevantes
- Mostrar aplicações práticas dos conceitos
- Usar casos reais de concursos da banca específica
- Variar níveis de dificuldade conforme a proficiência

Contexto:
- Tópico: {topic_name}
- Matéria: {subject}
- Proficiência: {proficiency}/10
- Banca: {banca}

Instruções específicas do supervisor: {supervisor_instructions}
            """),
            MessagesPlaceholder(variable_name="messages")
        ])
        
        self._templates["quiz_agent"] = ChatPromptTemplate.from_messages([
            ("system", """
Você é o Agente de Quiz, especialista em criar avaliações e exercícios.

Seu papel:
- Criar questões no estilo da banca específica
- Adaptar dificuldade à proficiência do estudante
- Fornecer feedback detalhado sobre respostas
- Identificar pontos que precisam ser reforçados

Contexto:
- Tópico: {topic_name}
- Matéria: {subject}
- Proficiência: {proficiency}/10
- Banca: {banca}

Instruções específicas do supervisor: {supervisor_instructions}
            """),
            MessagesPlaceholder(variable_name="messages")
        ])
        
        # Session Management Templates
        self._templates["session_intro"] = ChatPromptTemplate.from_template(
            """
Você é um Professor de Concursos especializado.

Inicie uma sessão de Aprendizagem Guiada sobre:
- Tópico: {topic_name}
- Matéria: {subject}
- Proficiência atual do aluno: {proficiency}/10
- Banca: {banca}

Crie uma introdução acolhedora e uma pergunta diagnóstica para entender o nível de conhecimento atual do estudante sobre este tópico específico.

Formate sua resposta como um objeto JSON com:
- "content": sua mensagem em markdown
- "ui_kind": "explanation"
- "agent": "teacher"
- "suggestions": array com 2-3 sugestões de resposta para o estudante
            """
        )
        
        # Contest Templates
        self._templates["edict_analysis"] = ChatPromptTemplate.from_template(
            """
# MISSÃO
Você é um especialista em análise de editais de concursos públicos.
Analise o conteúdo do edital fornecido e extraia informações estruturadas.

# CONTEÚDO DO EDITAL
{edict_content}

# SUA TAREFA
Extraia as seguintes informações do edital:
1. Informações gerais do concurso
2. Estrutura das provas e módulos
3. Matérias e tópicos detalhados
4. Pesos e pontuações
5. Datas importantes

# FORMATO DA SAÍDA
Retorne um objeto JSON estruturado com todas as informações extraídas.
            """
        )
    
    def get_template(self, template_name: str) -> ChatPromptTemplate:
        """Get a template by name."""
        if template_name not in self._templates:
            raise ValueError(f"Template '{template_name}' not found")
        return self._templates[template_name]
    
    def get_partial_template(self, template_name: str, **partial_vars) -> ChatPromptTemplate:
        """Get a template with some variables pre-filled."""
        template = self.get_template(template_name)
        return template.partial(**partial_vars)
    
    def list_templates(self) -> list[str]:
        """List all available template names."""
        return list(self._templates.keys())


# Global instance
prompt_factory = PromptTemplateFactory()
