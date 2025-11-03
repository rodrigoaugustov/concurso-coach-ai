import contextlib
import json
from dataclasses import dataclass
# LANGCHAIN
from langchain.agents import create_agent
from langchain.tools import tool, ToolRuntime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents.middleware import dynamic_prompt, ModelRequest
from app.core.settings import settings
from langgraph.checkpoint.postgres import PostgresSaver

from app.study.schemas import StudySession


# ToDo: Criar módulo de middleware, tools e context_schema reutilizáveis
# ToDo: Criar módulo com os system_prompts para os agentes

DATABASE_URL = settings.DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")

# Crie o checkpointer globalmente (ele gerencia seu próprio pool de conexões)
# Remova o 'with' statement aqui, pois queremos que ele fique aberto
context_manager = PostgresSaver.from_conn_string(DATABASE_URL)

# Configure as tabelas uma única vez
stack = contextlib.ExitStack()
GLOBAL_CHECKPOINTER = stack.enter_context(context_manager)
GLOBAL_CHECKPOINTER.setup()

@dataclass
class LessonSessionContext:
    session_id: int
    user_id: int
    topics: StudySession

# Agente Professor de Concursos
class ProfessorAgent:
    def __init__(self, model):
        """
        Agente responsável por fornecer explicações e exemplos durante a sessão de estudo.
        Args:
            model: Modelo de linguagem a ser utilizado pelo agente.
        """
        self.model = model

        @dynamic_prompt
        def gerar_prompt(request: ModelRequest) -> str:

            prompt_base = """Você é um professor especializado em aulas guiadas para concursos públicos.
            Forneça explicações claras, exemplos práticos e sempre que possível faça o link de como a banca costuma cobrar esse tópico nas provas, para ajudar os alunos a entenderem os tópicos.
            Apresente o conteúdo de forma gradual, e interaja com o aluno para garantir que ele está acompanhando o raciocínio.
            Quando você entender que o conteúdo da aula foi concluído, pergunte ao usuário se ele quer iniciar o quiz.
            """

            topicos = ", ".join(f"{t.subject}: {t.topic}" for t in request.runtime.context.topics)

            prompt_sessao = f"- Essa sessão de estudo é sobre: {topicos}. Inicie a aula contextualizando o aluno sobre o que será abordado nessa sessão de estudo guiada."

            prompt_final = f"{prompt_base}\n{prompt_sessao}"

            return prompt_final
        
        self.middleware = [gerar_prompt]

    def start_agent(self):

        agent = create_agent(
            name='agente-professor-aula-guiada-para-concursos',
            model=self.model,
            middleware=self.middleware,
            tools=[],
            context_schema=LessonSessionContext,
            checkpointer=GLOBAL_CHECKPOINTER
        )

        return agent

# Agente Responsável pela aplicação do quiz
class QuizAgent:
    """
    Agente responsável por elaborar e aplicar quizzes durante a sessão de estudo.
    Args:
        model: Modelo de linguagem a ser utilizado pelo agente.
    """
    def __init__(self, model):
        self.model = model

    def start_agent(self):

        prompt = """Você é um especialista em elaboração de quizzes para concursos públicos.
        Elabore o seu quiz no estilo CAT.
        Se o aluno acertar aumente o grau de dificuldade da próxima pergunta; se errar, diminua a dificuldade.
        Apresente uma pergunta por vez, aguarde a resposta do aluno, e forneça feedback imediato sobre a resposta, e já apresente a próxima pergunta.
        Crie perguntas desafiadoras e relevantes para testar o conhecimento do aluno sobre o(s) tópico(s) estudado(s) nessa sessão.
        """

        agent = create_agent(
            name="agente-elaborador-de-quiz-para-concursos",
            model=self.model,
            system_prompt=prompt,
            middleware=[],
            tools=[],
            context_schema=LessonSessionContext,
            checkpointer=GLOBAL_CHECKPOINTER
        )

        return agent


# Agente Orquestrador da Sessão de Estudo
class StudySessionAgent:
    """
    Orquestrador que gerencia a interação entre o agente professor e o agente de quiz durante a sessão de estudo.
    Args:
        model: Modelo de linguagem a ser utilizado pelo agente.
    """
    def __init__(self, model):
        self.model = model

        modelo = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0, api_key=settings.GEMINI_API_KEY)

        # Agentes
        self.agente_professor = ProfessorAgent(modelo).start_agent()
        self.agente_quiz = QuizAgent(modelo).start_agent()

        # Tools
        @tool(
            "agente_professor_concursos",
            description="Professor que ministra a aula guiada do tópico em contexto. Apresenta o conteúdo, responde dúvidas, fornece exemplos práticos, direciona para o quiz quando solicitado pelo usuário. Ao fim de cada interação analisa o contexto e decide se o conteúdo da aula foi concluído ou se o usuário solicitou o início do quiz.",
        )
        def call_professor_agent(query: str, runtime: ToolRuntime[LessonSessionContext, None]):
            config = {
                "configurable": {"thread_id": f"guided_lesson_{runtime.context.session_id}"}
            }

            result = self.agente_professor.invoke(
                {},  
                context=runtime.context, 
                config=config
            )

            return result["messages"][-1].content
            
        @tool(
            "agente_elaborador_quiz_concursos",
            description="Elabora e aplica o quiz sobre o tópico em contexto. Deve ser chamado quando o agente professor indicar que o conteúdo da aula foi concluído ou quando o usuário solicitar o início do quiz.",
        )
        def call_quiz_agent(query: str, runtime: ToolRuntime[LessonSessionContext, None]):

            config = {
                "configurable": {"thread_id": f"guided_lesson_{runtime.context.session_id}"}
            }
            
            result = self.agente_quiz.invoke(
                {},
                context=runtime.context, 
                config=config
            )

            return result["messages"][-1].content
        
        # Lista de ferramentas disponíveis para o orquestrador
        self._tools = [call_professor_agent, call_quiz_agent]

    def start_agent(self):

        prompt = """
        Você é um **Roteador de Conversa** para uma sessão de estudo. Sua única função é direcionar a conversa para a ferramenta correta (agente_professor_concursos ou agente_elaborador_quiz_concursos) e repassar a resposta.

        REGRAS DE ROTEAMENTO OBRIGATÓRIAS:

        1.  **Função Principal:** Sua função é ser um **roteador**, não um participante. Você NUNCA deve gerar seu próprio conteúdo de aula ou quiz.
        2.  **Repasse Direto (A REGRA MAIS IMPORTANTE):**
            * Quando você chamar uma ferramenta (agente_professor_concursos ou agente_elaborador_quiz_concursos) e receber a resposta dela, sua única e exclusiva ação deve ser **repetir essa resposta EXATA, palavra por palavra, para o usuário final.**
            * Não adicione NENHUM texto seu. Não diga "O professor disse:" ou "Aqui está a pergunta:". Apenas repita.
            * Se a ferramenta retornar "Olá, vamos começar. Você entendeu?", sua resposta final para o usuário deve ser exatamente: "Olá, vamos começar. Você entendeu?".
        3.  **Proibição de Interação Interna:**
            * Você está **PROIBIDO** de responder a perguntas feitas pela ferramenta. A saída da ferramenta é um texto para ser encaminhado ao usuário, NÃO é uma pergunta para você, o roteador.
        4.  **Fluxo:**
            * Na primeira interação e durante a aula, acione o `agente_professor_concursos`.
            * Quando o usuário pedir o quiz, acione o `agente_quiz`.
        5.  **Exceção (Filtro de Segurança):**
            * A ÚNICA vez que você pode gerar sua própria resposta é se o input do usuário for claramente fora do tópico (ex: "Qual a capital da França?") ou tentar mudar de assunto.
            * Neste caso, e **somente** neste caso, NÃO acione nenhuma ferramenta e responda: "Meu foco é exclusivamente na sessão de estudo atual. Vamos continuar?"
        """

        agent = create_agent(
            name="agente-orquestrador-de-sessao-de-estudo-para-concursos",
            model=self.model,
            system_prompt=prompt,
            middleware=[],
            tools=self._tools,
            context_schema=LessonSessionContext,
            checkpointer=GLOBAL_CHECKPOINTER
        )

        return agent
