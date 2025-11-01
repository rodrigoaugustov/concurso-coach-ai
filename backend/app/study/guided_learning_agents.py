"""
Multi-Agent Guided Learning System using LangGraph.
Implements the Agent Supervisor pattern with specialized agents for different learning tasks.
"""

from typing import Dict, List, Any, Optional, TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import Runnable
from pydantic import BaseModel
from enum import Enum

from ..core.ai_service import ChainFactory
from ..core.logging import get_logger
from .guided_learning_schemas import (
    ConversationState, 
    AgentRouting, 
    AgentResponse,
    AssistantMessage,
    SessionIntroResponse
)

# Try to import LangGraph components, fallback if not available
try:
    from langgraph.graph import StateGraph, END
    from langgraph.prebuilt import ToolExecutor
    import operator
    LANGGRAPH_AVAILABLE = True
except ImportError:
    StateGraph = None
    END = None
    ToolExecutor = None
    operator = None
    LANGGRAPH_AVAILABLE = False


class AgentType(str, Enum):
    """Available agent types."""
    SUPERVISOR = "supervisor"
    EXPLANATION = "explanation"
    EXAMPLE = "example"
    QUIZ = "quiz"


class SimplifiedAgentRouter:
    """Simplified agent router when LangGraph is not available - now with real AI responses."""
    
    def __init__(self, chain_factory: ChainFactory):
        self.chain_factory = chain_factory
        self.logger = get_logger("simplified_agent_router")
        self.logger.info("Using simplified agent router with real AI responses")
    
    async def route_and_process(
        self,
        chat_id: str,
        user_id: int,
        user_message: str,
        session_context: Dict[str, Any],
        message_history: List[BaseMessage]
    ) -> AssistantMessage:
        """Route message to appropriate agent and process response."""
        
        try:
            # Simple routing logic based on message content
            agent_type = self._route_message(user_message)
            
            self.logger.info(
                "Routing message to agent",
                chat_id=chat_id,
                agent=agent_type,
                message_preview=user_message[:50]
            )
            
            # Process with selected agent using real AI
            response = await self._process_with_agent(
                agent_type,
                user_message,
                session_context,
                message_history
            )
            
            # Generate suggestions
            suggestions = self._generate_suggestions(agent_type, response.content)
            
            return AssistantMessage(
                content=response.content,
                ui_kind=response.ui_kind,
                agent=response.agent,
                suggestions=suggestions
            )
            
        except Exception as e:
            self.logger.error(
                "Simplified routing failed",
                chat_id=chat_id,
                error=str(e)
            )
            
            # Fallback response
            return AssistantMessage(
                content="Desculpe, ocorreu um erro. Pode reformular sua pergunta?",
                ui_kind="explanation",
                agent="system",
                suggestions=[
                    "Pode explicar melhor?",
                    "Precisa de um exemplo?",
                    "Vamos fazer um exercício?"
                ]
            )
    
    def _route_message(self, message: str) -> str:
        """Enhanced routing based on message content."""
        message_lower = message.lower()
        
        # Quiz/assessment keywords
        if any(word in message_lower for word in [
            "quiz", "teste", "avaliação", "pergunta", "questão", "exercício", 
            "praticar", "treinar", "avaliar", "verificar"
        ]):
            return "quiz"
        
        # Example keywords  
        elif any(word in message_lower for word in [
            "exemplo", "prático", "aplicação", "como fazer", "na prática", 
            "caso real", "situação", "demonstre", "mostre"
        ]):
            return "example"
        
        # Default to explanation for concepts, theory, "what is", etc.
        else:
            return "explanation"
    
    async def _process_with_agent(
        self,
        agent_type: str,
        user_message: str,
        session_context: Dict[str, Any],
        message_history: List[BaseMessage]
    ) -> AgentResponse:
        """Process message with specific agent using real AI."""
        
        try:
            # Prepare context for the agent
            context = {
                "topic_name": session_context["topic_name"],
                "subject": session_context["subject"],
                "proficiency": int(session_context["proficiency"] * 10),  # Convert to 1-10 scale
                "banca": session_context.get("banca", "Não especificada"),
                "supervisor_instructions": f"Responda como agente {agent_type} sobre '{user_message}'",
                "messages": self._format_messages_for_context(message_history + [HumanMessage(content=user_message)])
            }
            
            # Get agent response using real AI
            template_name = f"{agent_type}_agent"
            
            self.logger.info(
                "Calling real AI for agent response",
                agent_type=agent_type,
                template_name=template_name,
                topic=context["topic_name"]
            )
            
            response = await self.chain_factory.ainvoke(
                template_name, 
                context, 
                AgentResponse
            )
            
            self.logger.info(
                "AI response received",
                agent_type=agent_type,
                content_length=len(response.content),
                ui_kind=response.ui_kind
            )
            
            return response
            
        except Exception as e:
            self.logger.error(
                "Agent processing failed",
                agent_type=agent_type,
                error=str(e)
            )
            
            # Fallback response with contextual content
            topic_name = session_context.get("topic_name", "este tópico")
            
            fallback_content = {
                "explanation": f"Vou explicar **{topic_name}** para você. Este é um conceito importante que aparece frequentemente em concursos. Precisa de algum aspecto específico?",
                "example": f"Aqui está um exemplo prático de **{topic_name}**: [exemplo contextual seria gerado aqui]. Gostaria de ver mais exemplos?",
                "quiz": f"Vamos testar seu conhecimento sobre **{topic_name}**. Aqui está uma questão: [questão seria gerada aqui]. Qual sua resposta?"
            }
            
            return AgentResponse(
                content=fallback_content.get(agent_type, fallback_content["explanation"]),
                ui_kind=agent_type if agent_type in ["explanation", "example", "quiz"] else "explanation",
                agent=agent_type,
                suggestions=self._generate_suggestions(agent_type, ""),
                next_step=None
            )
    
    def _format_messages_for_context(self, messages: List[BaseMessage]) -> str:
        """Format messages for AI context."""
        if not messages:
            return "Nenhuma mensagem anterior."
        
        formatted = []
        for msg in messages[-5:]:  # Last 5 messages for context
            role = "Usuário" if isinstance(msg, HumanMessage) else "Assistente"
            content = msg.content[:150] + "..." if len(msg.content) > 150 else msg.content
            formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted)
    
    def _generate_suggestions(self, agent_type: str, content: str) -> List[str]:
        """Generate contextual suggestions."""
        base_suggestions = {
            "explanation": [
                "Pode dar um exemplo prático?",
                "Como isso cai nas provas?",
                "Quais são os erros mais comuns?"
            ],
            "example": [
                "Pode explicar o passo a passo?",
                "Tem mais exemplos similares?",
                "Vamos praticar com um exercício?"
            ],
            "quiz": [
                "Pode explicar a resposta correta?",
                "Quero tentar outro exercício",
                "Como posso melhorar nesse tópico?"
            ]
        }
        
        suggestions = base_suggestions.get(agent_type, base_suggestions["explanation"])
        suggestions.append("Vamos para o próximo tópico?")
        
        return suggestions[:3]


class GuidedLearningAgents:
    """
    Multi-agent system for guided learning conversations.
    Uses real AI responses with simplified routing.
    """
    
    def __init__(self, chain_factory: ChainFactory):
        self.chain_factory = chain_factory
        self.logger = get_logger("guided_learning_agents")
        
        if LANGGRAPH_AVAILABLE:
            self.graph = self._build_conversation_graph()
            self.logger.info("LangGraph conversation system initialized")
        else:
            self.simplified_router = SimplifiedAgentRouter(chain_factory)
            self.logger.info("Simplified agent system with real AI initialized")
    
    async def process_message(
        self, 
        chat_id: str,
        user_id: int,
        user_message: str,
        session_context: Dict[str, Any],
        message_history: List[BaseMessage]
    ) -> AssistantMessage:
        """Process a user message through the multi-agent system."""
        
        self.logger.info(
            "Processing message through multi-agent system",
            chat_id=chat_id,
            user_id=user_id,
            message_length=len(user_message)
        )
        
        # Use simplified router (which now has real AI)
        return await self.simplified_router.route_and_process(
            chat_id, user_id, user_message, session_context, message_history
        )
    
    async def start_session(
        self, 
        chat_id: str,
        session_context: Dict[str, Any]
    ) -> AssistantMessage:
        """Start a new guided learning session with real AI introduction."""
        
        self.logger.info(
            "Starting new guided learning session",
            chat_id=chat_id,
            topic=session_context["topic_name"]
        )
        
        try:
            # Use real AI to generate session introduction
            intro_context = {
                "topic_name": session_context["topic_name"],
                "subject": session_context["subject"],
                "proficiency": int(session_context["proficiency"] * 10),  # Convert to 1-10 scale
                "banca": session_context.get("banca", "Não especificada")
            }
            
            self.logger.info(
                "Generating session introduction with AI",
                chat_id=chat_id,
                context=intro_context
            )
            
            # Call AI to generate introduction
            response = await self.chain_factory.ainvoke(
                "session_intro",
                intro_context,
                SessionIntroResponse
            )
            
            return AssistantMessage(
                content=response.content,
                ui_kind=response.ui_kind,
                agent=response.agent,
                suggestions=response.suggestions
            )
            
        except Exception as e:
            self.logger.error(
                "AI session start failed, using fallback",
                chat_id=chat_id,
                error=str(e)
            )
            
            # Enhanced fallback with context
            topic_name = session_context["topic_name"]
            subject = session_context["subject"]
            proficiency = session_context["proficiency"]
            
            # Generate contextual introduction
            if proficiency < 0.3:
                intro = f"Olá! Vamos começar do básico com **{topic_name}** em {subject}. Não se preocupe, vamos construir seu conhecimento passo a passo!"
                suggestions = [
                    "Não sei nada sobre isso",
                    "Explique desde o início",
                    "O que é mais importante saber?"
                ]
            elif proficiency < 0.7:
                intro = f"Ótimo! Vamos aprofundar seus conhecimentos em **{topic_name}**. Vejo que você já tem uma base, então podemos focar nos pontos mais desafiadores."
                suggestions = [
                    "Tenho dúvidas específicas",
                    "Quero ver exemplos práticos",
                    "Como isso cai nas provas?"
                ]
            else:
                intro = f"Excelente! Você já tem bom domínio de **{topic_name}**. Vamos refinar e praticar os aspectos mais complexos para garantir nota máxima."
                suggestions = [
                    "Quero questões difíceis",
                    "Mostre pegadinhas comuns",
                    "Vamos revisar rapidamente"
                ]
            
            return AssistantMessage(
                content=intro,
                ui_kind="explanation",
                agent="teacher",
                suggestions=suggestions
            )


# Update the main GuidedLearningAgents class to use the new logic
if LANGGRAPH_AVAILABLE:
    # Keep LangGraph implementation for future use
    class GraphState(TypedDict):
        """State structure for the LangGraph conversation flow."""
        # Session context
        chat_id: str
        user_id: int
        topic_name: str
        subject: str
        proficiency: float
        banca: Optional[str]
        
        # Current conversation
        messages: Annotated[List[BaseMessage], operator.add]
        user_message: str
        
        # Agent routing
        current_agent: Optional[str]
        agent_instructions: Optional[str]
        
        # Response
        assistant_response: Optional[Dict[str, Any]]
        suggestions: List[str]
        
        # Flow control
        next_action: Optional[str]
        session_complete: bool
else:
    # Fallback state class without LangGraph dependencies
    class GraphState:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
