# backend/app/study/ai_validation_service.py

"""
AIValidationService: Responsável pela validação e auto-correção de respostas de IA.

Esta classe implementa o padrão Strategy para validação,
permitindo diferentes estratégias de validação para diferentes tipos de resposta.
"""

import time
from typing import Type, Callable, List, Dict, Any
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage

from app.core.ai_service import LangChainService
from app.core.constants import AIConstants
from app.core.logging import get_logger, LogContext


class AIValidationService:
    """
    Serviço especializado em validação e auto-correção de respostas de IA.
    
    Implementa um ciclo de validação que inclui:
    1. Validação sintática (via Pydantic schema)
    2. Validação de negócio (via função customizada)
    3. Auto-correção em caso de falha
    """
    
    def __init__(self, ai_service: LangChainService, max_retries: int = None):
        self.ai_service = ai_service
        self.max_retries = max_retries or AIConstants.MAX_RETRIES_AI_VALIDATION
        self.conversation_history = []
        self.logger = get_logger("study.ai_validation")
        
    def invoke_with_validation(
        self,
        prompt_template: str,
        prompt_input: dict,
        response_schema: Type[BaseModel],
        validation_function: Callable[[BaseModel], List[str]],
        context: Dict[str, Any] = None
    ) -> BaseModel:
        """
        Orquestra uma chamada de IA com ciclo de validação e auto-correção.
        
        Args:
            prompt_template: Template do prompt
            prompt_input: Dados de entrada para o prompt
            response_schema: Schema Pydantic para validação sintática
            validation_function: Função para validação de negócio
            context: Contexto adicional para logs
            
        Returns:
            BaseModel: Resposta validada da IA
            
        Raises:
            Exception: Se todas as tentativas de correção falharem
        """
        ai_start = time.time()
        context = context or {}
        
        with LogContext(
            ai_validation_cycle=True, 
            schema=response_schema.__name__,
            **context
        ) as ai_logger:
            ai_logger.info(
                "Starting AI validation cycle",
                max_retries=self.max_retries,
                schema=response_schema.__name__
            )
            
            # Preparar mensagens iniciais
            current_messages = self.conversation_history.copy()
            prompt = ChatPromptTemplate.from_template(prompt_template)
            user_messages = prompt.format_messages(**prompt_input)
            current_messages.extend(user_messages)
            
            last_error = None
            ai_response_obj = None
            
            for attempt in range(self.max_retries + 1):
                attempt_start = time.time()
                
                ai_logger.info(
                    "Starting AI attempt",
                    attempt=attempt + 1,
                    max_attempts=self.max_retries + 1
                )
                
                try:
                    # Tentativa de geração com IA
                    ai_response_obj = self.ai_service.invoke_with_history(
                        messages=current_messages,
                        response_schema=response_schema
                    )
                    
                    # Validação de negócio
                    ai_logger.debug("Running business validation")
                    validation_errors = validation_function(ai_response_obj)
                    
                    if validation_errors:
                        error_message = "Validação de negócio falhou:\n- " + "\n- ".join(validation_errors)
                        raise ValueError(error_message)
                    
                    # Sucesso - atualizar histórico e retornar
                    attempt_duration = round((time.time() - attempt_start) * 1000, 2)
                    total_duration = round((time.time() - ai_start) * 1000, 2)
                    
                    ai_logger.info(
                        "AI validation cycle completed successfully",
                        attempt=attempt + 1,
                        attempt_duration_ms=attempt_duration,
                        total_duration_ms=total_duration
                    )
                    
                    # Atualizar histórico de conversação
                    self._update_conversation_history(current_messages, ai_response_obj)
                    
                    return ai_response_obj
                    
                except Exception as e:
                    last_error = e
                    attempt_duration = round((time.time() - attempt_start) * 1000, 2)
                    
                    ai_logger.warning(
                        "AI attempt failed",
                        attempt=attempt + 1,
                        duration_ms=attempt_duration,
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    
                    # Se é a última tentativa, lançar erro
                    if attempt >= self.max_retries:
                        ai_logger.error(
                            "Maximum retry attempts reached - AI validation cycle failed",
                            total_attempts=self.max_retries + 1,
                            final_error=str(e)
                        )
                        raise last_error
                    
                    # Preparar prompt de correção para próxima tentativa
                    current_messages = self._prepare_correction_prompt(
                        current_messages, ai_response_obj, e, ai_logger
                    )
                    
            raise Exception(f"Falha ao obter uma resposta válida da IA. Último erro: {last_error}")
            
    def _update_conversation_history(self, current_messages: list, ai_response_obj: BaseModel):
        """
        Atualiza o histórico de conversação após sucesso.
        
        Args:
            current_messages: Mensagens da tentativa atual
            ai_response_obj: Resposta bem-sucedida da IA
        """
        # Atualizar histórico principal
        self.conversation_history = current_messages
        
        # Adicionar resposta da IA como AIMessage
        ai_response_json_str = ai_response_obj.json()
        self.conversation_history.append(AIMessage(content=ai_response_json_str))
        
    def _prepare_correction_prompt(
        self, 
        current_messages: list, 
        ai_response_obj: BaseModel, 
        error: Exception,
        logger
    ) -> list:
        """
        Prepara prompt de correção para a próxima tentativa.
        
        Args:
            current_messages: Mensagens da tentativa atual
            ai_response_obj: Resposta inválida (pode ser None)
            error: Erro que ocorreu
            logger: Logger para registrar ação
            
        Returns:
            list: Mensagens atualizadas com prompt de correção
        """
        # Extrair resposta inválida da IA para usar no prompt de correção
        invalid_response_str = ""
        if ai_response_obj:  # Falha de validação de negócio
            invalid_response_str = ai_response_obj.json()
        elif hasattr(error, 'llm_output'):  # Erro do LangChain
            invalid_response_str = getattr(error, 'llm_output', str(error))
        else:
            invalid_response_str = str(error)
            
        # Importar prompt de correção
        from app.study.prompts import json_correction_prompt
        
        correction_prompt_input = {
            "error_message": str(error),
            "invalid_response": invalid_response_str
        }
        
        correction_prompt = ChatPromptTemplate.from_template(json_correction_prompt)
        correction_messages = correction_prompt.format_messages(**correction_prompt_input)
        
        current_messages.extend(correction_messages)
        
        logger.info(
            "Built correction prompt for next attempt",
            correction_prompt_length=len(correction_messages)
        )
        
        return current_messages
        
    def reset_conversation_history(self):
        """
        Limpa o histórico de conversação.
        Útil quando começar um novo ciclo de validação independente.
        """
        self.conversation_history = []
        self.logger.debug("Conversation history reset")
