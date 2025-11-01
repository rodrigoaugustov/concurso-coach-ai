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
    AssistantMessage
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


if LANGGRAPH_AVAILABLE:
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


class SimplifiedAgentRouter:
    """Fallback agent router when LangGraph is not available."""
    
    def __init__(self, chain_factory: ChainFactory):
        self.chain_factory = chain_factory
        self.logger = get_logger("simplified_agent_router")
        self.logger.warning("Using simplified agent router - LangGraph not available")
    
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
            
            # Process with selected agent
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
        """Simple routing based on message content."""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["exemplo", "exercício", "prática", "aplicação"]):
            return "example"
        elif any(word in message_lower for word in ["quiz", "teste", "avaliação", "pergunta"]):
            return "quiz"
        else:
            return "explanation"
    
    async def _process_with_agent(
        self,
        agent_type: str,
        user_message: str,
        session_context: Dict[str, Any],
        message_history: List[BaseMessage]
    ) -> AgentResponse:
        """Process message with specific agent."""
        
        try:
            # Prepare context for the agent
            context = {
                "topic_name": session_context["topic_name"],
                "subject": session_context["subject"],
                "proficiency": session_context["proficiency"],
                "banca": session_context.get("banca", "Não especificada"),
                "supervisor_instructions": f"Responda como agente {agent_type}",
                "messages": message_history
            }
            
            # Get agent response
            template_name = f"{agent_type}_agent"
            response = await self.chain_factory.ainvoke(
                template_name, 
                context, 
                AgentResponse
            )
            
            return response
            
        except Exception as e:
            self.logger.error(
                "Agent processing failed",
                agent_type=agent_type,
                error=str(e)
            )
            
            # Fallback response
            return AgentResponse(
                content=f"Como {agent_type}, posso ajudar você com essa questão.",
                ui_kind="explanation",
                agent=agent_type,
                suggestions=[],
                next_step=None
            )
    
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
    Uses LangGraph to orchestrate specialized teaching agents.
    """
    
    def __init__(self, chain_factory: ChainFactory):
        self.chain_factory = chain_factory
        self.logger = get_logger("guided_learning_agents")
        
        if LANGGRAPH_AVAILABLE:
            self.graph = self._build_conversation_graph()
            self.logger.info("LangGraph conversation system initialized")
        else:
            self.simplified_router = SimplifiedAgentRouter(chain_factory)
            self.logger.warning("Using simplified agent system - LangGraph not available")
    
    def _build_conversation_graph(self) -> StateGraph:
        """Build the LangGraph conversation flow."""
        
        if not LANGGRAPH_AVAILABLE:
            return None
        
        workflow = StateGraph(GraphState)
        
        # Add nodes
        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("explanation_agent", self._explanation_agent_node)
        workflow.add_node("example_agent", self._example_agent_node)
        workflow.add_node("quiz_agent", self._quiz_agent_node)
        workflow.add_node("generate_suggestions", self._generate_suggestions_node)
        
        # Define the flow
        workflow.set_entry_point("supervisor")
        
        # Supervisor routing
        workflow.add_conditional_edges(
            "supervisor",
            self._should_route_to_agent,
            {
                "explanation": "explanation_agent",
                "example": "example_agent", 
                "quiz": "quiz_agent",
                "complete": END
            }
        )
        
        # All agents go to suggestion generation
        workflow.add_edge("explanation_agent", "generate_suggestions")
        workflow.add_edge("example_agent", "generate_suggestions")
        workflow.add_edge("quiz_agent", "generate_suggestions")
        
        # End after suggestions
        workflow.add_edge("generate_suggestions", END)
        
        return workflow.compile()
    
    def _supervisor_node(self, state: GraphState) -> GraphState:
        """Supervisor agent that routes to specialized agents."""
        self.logger.info("Supervisor analyzing message", chat_id=state["chat_id"])
        
        try:
            # Prepare context for supervisor
            context = {
                "topic_name": state["topic_name"],
                "subject": state["subject"],
                "proficiency": state["proficiency"],
                "banca": state.get("banca", "Não especificada"),
                "history": self._format_message_history(state["messages"]),
                "message": state["user_message"]
            }
            
            # Get routing decision from supervisor
            chain = self.chain_factory.get_structured_chain(
                "teacher_supervisor", 
                AgentRouting
            )
            
            routing = chain.invoke(context)
            
            # Update state with routing decision
            state["current_agent"] = routing.selected_agent
            state["agent_instructions"] = routing.instructions
            
            self.logger.info(
                "Supervisor routing decision",
                chat_id=state["chat_id"],
                selected_agent=routing.selected_agent,
                reasoning=routing.reasoning
            )
            
            return state
            
        except Exception as e:
            self.logger.error(
                "Supervisor node failed",
                chat_id=state["chat_id"],
                error=str(e)
            )
            # Fallback to explanation agent
            state["current_agent"] = "explanation"
            state["agent_instructions"] = "Provide a helpful explanation about the topic."
            return state
    
    def _explanation_agent_node(self, state: GraphState) -> GraphState:
        """Explanation agent - focuses on clear concept explanations."""
        return self._execute_agent_node(state, AgentType.EXPLANATION)
    
    def _example_agent_node(self, state: GraphState) -> GraphState:
        """Example agent - provides practical examples and exercises."""
        return self._execute_agent_node(state, AgentType.EXAMPLE)
    
    def _quiz_agent_node(self, state: GraphState) -> GraphState:
        """Quiz agent - creates assessments and provides feedback."""
        return self._execute_agent_node(state, AgentType.QUIZ)
    
    def _execute_agent_node(self, state: GraphState, agent_type: AgentType) -> GraphState:
        """Common execution logic for agent nodes."""
        self.logger.info(
            "Executing agent",
            chat_id=state["chat_id"],
            agent=agent_type.value
        )
        
        try:
            # Prepare context for the agent
            context = {
                "topic_name": state["topic_name"],
                "subject": state["subject"],
                "proficiency": state["proficiency"],
                "banca": state.get("banca", "Não especificada"),
                "supervisor_instructions": state["agent_instructions"],
                "messages": state["messages"]
            }
            
            # Get agent response
            template_name = f"{agent_type.value}_agent"
            chain = self.chain_factory.get_structured_chain(template_name, AgentResponse)
            
            response = chain.invoke(context)
            
            # Store the response
            state["assistant_response"] = {
                "content": response.content,
                "ui_kind": response.ui_kind,
                "agent": response.agent,
                "next_step": response.next_step
            }
            
            # Add assistant message to history
            assistant_msg = AIMessage(content=response.content)
            state["messages"].append(assistant_msg)
            
            self.logger.info(
                "Agent response generated",
                chat_id=state["chat_id"],
                agent=agent_type.value,
                ui_kind=response.ui_kind
            )
            
            return state
            
        except Exception as e:
            self.logger.error(
                "Agent node failed",
                chat_id=state["chat_id"],
                agent=agent_type.value,
                error=str(e)
            )
            
            # Fallback response
            state["assistant_response"] = {
                "content": "Desculpe, ocorreu um erro. Pode reformular sua pergunta?",
                "ui_kind": "explanation",
                "agent": agent_type.value,
                "next_step": None
            }
            
            return state
    
    def _generate_suggestions_node(self, state: GraphState) -> GraphState:
        """Generate follow-up suggestions based on the agent response."""
        self.logger.info("Generating suggestions", chat_id=state["chat_id"])
        
        try:
            # Generate contextual suggestions
            suggestions = self._generate_contextual_suggestions(
                state["topic_name"],
                state["subject"],
                state["current_agent"],
                state["assistant_response"]["content"]
            )
            
            state["suggestions"] = suggestions
            
            self.logger.info(
                "Suggestions generated",
                chat_id=state["chat_id"],
                suggestion_count=len(suggestions)
            )
            
            return state
            
        except Exception as e:
            self.logger.error(
                "Suggestion generation failed",
                chat_id=state["chat_id"],
                error=str(e)
            )
            
            # Fallback suggestions
            state["suggestions"] = [
                "Pode explicar melhor esse conceito?",
                "Tem algum exemplo prático?",
                "Vamos fazer um exercício?"
            ]
            
            return state
    
    def _should_route_to_agent(self, state: GraphState) -> str:
        """Conditional routing logic."""
        current_agent = state.get("current_agent")
        
        if current_agent in ["explanation", "example", "quiz"]:
            return current_agent
        
        # Default to explanation if no clear routing
        return "explanation"
    
    def _format_message_history(self, messages: List[BaseMessage]) -> str:
        """Format message history for context."""
        if not messages:
            return "Nenhuma mensagem anterior."
        
        formatted = []
        for msg in messages[-10:]:  # Last 10 messages for context
            role = "Usuário" if isinstance(msg, HumanMessage) else "Assistente"
            content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted)
    
    def _generate_contextual_suggestions(
        self, 
        topic_name: str, 
        subject: str, 
        agent_type: str, 
        response_content: str
    ) -> List[str]:
        """Generate contextual follow-up suggestions."""
        
        base_suggestions = {
            "explanation": [
                f"Pode dar um exemplo prático de {topic_name}?",
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
        
        # Add a generic "next topic" suggestion
        suggestions.append("Vamos para o próximo tópico?")
        
        return suggestions[:3]  # Limit to 3 suggestions
    
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
        
        if not LANGGRAPH_AVAILABLE:
            return await self.simplified_router.route_and_process(
                chat_id, user_id, user_message, session_context, message_history
            )
        
        # Prepare initial state
        initial_state = GraphState(
            chat_id=chat_id,
            user_id=user_id,
            topic_name=session_context["topic_name"],
            subject=session_context["subject"],
            proficiency=session_context["proficiency"],
            banca=session_context.get("banca"),
            messages=message_history,
            user_message=user_message,
            current_agent=None,
            agent_instructions=None,
            assistant_response=None,
            suggestions=[],
            next_action=None,
            session_complete=False
        )
        
        # Add user message to history
        user_msg = HumanMessage(content=user_message)
        initial_state["messages"].append(user_msg)
        
        try:
            # Run the conversation graph
            final_state = await self.graph.ainvoke(initial_state)
            
            # Extract response
            response_data = final_state["assistant_response"]
            suggestions = final_state["suggestions"]
            
            # Create structured response
            assistant_message = AssistantMessage(
                content=response_data["content"],
                ui_kind=response_data["ui_kind"],
                agent=response_data["agent"],
                suggestions=suggestions
            )
            
            self.logger.info(
                "Message processed successfully",
                chat_id=chat_id,
                agent=response_data["agent"],
                ui_kind=response_data["ui_kind"]
            )
            
            return assistant_message
            
        except Exception as e:
            self.logger.error(
                "Message processing failed",
                chat_id=chat_id,
                error=str(e),
                error_type=type(e).__name__
            )
            
            # Return fallback response
            return AssistantMessage(
                content="Desculpe, houve um problema ao processar sua mensagem. Pode tentar novamente?",
                ui_kind="explanation",
                agent="system",
                suggestions=[
                    "Pode reformular a pergunta?",
                    "Precisa de ajuda com algum conceito específico?",
                    "Vamos começar do básico?"
                ]
            )
    
    async def start_session(
        self, 
        chat_id: str,
        session_context: Dict[str, Any]
    ) -> AssistantMessage:
        """Start a new guided learning session."""
        
        self.logger.info(
            "Starting new guided learning session",
            chat_id=chat_id,
            topic=session_context["topic_name"]
        )
        
        try:
            # Generate session introduction using a simple approach
            topic_name = session_context["topic_name"]
            
            return AssistantMessage(
                content=f"Olá! Vamos estudar **{topic_name}** juntos! O que você já sabe sobre este tópico?",
                ui_kind="explanation",
                agent="teacher",
                suggestions=[
                    "Não sei nada sobre isso",
                    "Já estudei um pouco",
                    "Tenho dúvidas específicas"
                ]
            )
            
        except Exception as e:
            self.logger.error(
                "Session start failed",
                chat_id=chat_id,
                error=str(e)
            )
            
            # Fallback introduction
            topic_name = session_context.get("topic_name", "este tópico")
            return AssistantMessage(
                content=f"Olá! Vamos estudar **{topic_name}** juntos! O que você gostaria de saber?",
                ui_kind="explanation",
                agent="teacher",
                suggestions=[
                    "Explique o básico",
                    "Mostre um exemplo",
                    "Faça uma pergunta"
                ]
            )
