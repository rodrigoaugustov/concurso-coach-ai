
from typing import Dict, List, Type
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel as LangChainBaseModel
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from .logging import get_logger
import time


class LangChainService:
    def __init__(self, provider: str, api_key: str, model_name: str, temperature: float = 0.2):
        """
        Inicializa o serviço com um provedor e modelo específicos.
        
        Args:
            provider (str): 'google' ou 'openai'.
            api_key (str): A chave de API para o provedor.
            model_name (str): O nome do modelo a ser usado.
            temperature (float): A criatividade do modelo (0.0 = determinístico).
        """
        self.logger = get_logger("ai_service")
        self.provider = provider
        self.model_name = model_name
        self.temperature = temperature
        
        self.logger.info(
            "Initializing AI service",
            provider=provider,
            model=model_name,
            temperature=temperature
        )
        
        if provider == "google":
            self.llm = ChatGoogleGenerativeAI(
                model=model_name, 
                google_api_key=api_key,
                temperature=temperature
            )
        # Exemplo de como adicionar outro provedor no futuro
        # elif provider == "openai":
        #     self.llm = ChatOpenAI(model=model_name, api_key=api_key, temperature=temperature)
        else:
            error_msg = f"Provedor '{provider}' não suportado."
            self.logger.error("Unsupported AI provider", provider=provider)
            raise ValueError(error_msg)
        
    def _create_chain(self, response_schema: Type[LangChainBaseModel]):
        """Método auxiliar para criar a cadeia de processamento."""
        structured_llm = self.llm.with_structured_output(response_schema)
        # Para chamadas multimodais, o prompt é construído dinamicamente
        return structured_llm

    def generate_structured_output(
        self, 
        prompt_template: str, 
        prompt_input: Dict, 
        response_schema: Type[LangChainBaseModel]
    ) -> LangChainBaseModel:
        """
        Gera uma saída estruturada (JSON/Pydantic) a partir de um prompt e dados de entrada.

        Returns:
            Uma instância do objeto Pydantic 'response_schema' preenchida.
        """
        start_time = time.time()
        
        self.logger.info(
            "Starting structured output generation",
            schema=response_schema.__name__,
            provider=self.provider,
            model=self.model_name,
            temperature=self.temperature,
            prompt_keys=list(prompt_input.keys()) if prompt_input else []
        )
        
        try:
            # Vincula o schema de saída ao modelo para forçar a resposta JSON
            structured_llm = self.llm.with_structured_output(response_schema)
            
            prompt = ChatPromptTemplate.from_template(prompt_template)
            
            # Cria a "cadeia" (chain) de execução: dados de entrada -> prompt -> modelo
            chain = prompt | structured_llm
            
            # Executa a cadeia com os dados de entrada
            response = chain.invoke(prompt_input)
            
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            self.logger.info(
                "Structured output generation completed",
                schema=response_schema.__name__,
                duration_ms=duration_ms,
                success=True
            )
            
            return response
            
        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            self.logger.error(
                "Structured output generation failed",
                schema=response_schema.__name__,
                duration_ms=duration_ms,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def generate_structured_output_from_content(
        self,
        content_parts: List, # Lista de partes (texto, imagem, pdf)
        response_schema: Type[LangChainBaseModel]
    ) -> LangChainBaseModel:
        """
        Gera uma saída estruturada a partir de uma lista de conteúdos (multimodal).
        """
        start_time = time.time()
        
        # Conta tipos de conteúdo para logging
        content_types = {}
        for part in content_parts:
            part_type = part.get('type', 'unknown')
            content_types[part_type] = content_types.get(part_type, 0) + 1
        
        self.logger.info(
            "Starting multimodal content processing",
            schema=response_schema.__name__,
            provider=self.provider,
            model=self.model_name,
            content_parts_count=len(content_parts),
            content_types=content_types
        )
        
        try:
            chain = self._create_chain(response_schema)
            
            # Constrói a mensagem a partir das partes
            message = HumanMessage(content=content_parts)
            
            response = chain.invoke([message])
            
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            self.logger.info(
                "Multimodal content processing completed",
                schema=response_schema.__name__,
                duration_ms=duration_ms,
                success=True
            )
            
            return response
            
        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            self.logger.error(
                "Multimodal content processing failed",
                schema=response_schema.__name__,
                duration_ms=duration_ms,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def invoke_with_history(self, messages: List, response_schema: Type[BaseModel]) -> BaseModel:
        """Invoca o modelo com histórico de conversação."""
        start_time = time.time()
        
        self.logger.info(
            "Starting conversation with history",
            schema=response_schema.__name__,
            message_count=len(messages),
            provider=self.provider,
            model=self.model_name
        )
        
        try:
            structured_llm = self.llm.with_structured_output(response_schema)
            
            response = structured_llm.invoke(messages)
            
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            self.logger.info(
                "Conversation with history completed",
                schema=response_schema.__name__,
                duration_ms=duration_ms,
                success=True
            )
            
            return response
            
        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            self.logger.error(
                "Conversation with history failed",
                schema=response_schema.__name__,
                duration_ms=duration_ms,
                error=str(e),
                error_type=type(e).__name__
            )
            raise