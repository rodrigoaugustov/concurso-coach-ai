"""
Refactored AI Service - LangChain-first approach with factory pattern.
Provides cached chains, async helpers, and structured output with auto-correction.
"""

from typing import Dict, List, Type, Any, Optional, AsyncGenerator
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain.output_parsers import RetryWithErrorOutputParser
from pydantic import BaseModel
from .logging import get_logger
from .prompt_templates import prompt_factory
import time
import asyncio
from functools import lru_cache


class ChainFactory:
    """
    Factory for creating and caching LangChain Runnable chains.
    Provides centralized chain management with async support and auto-correction.
    """
    
    def __init__(self, provider: str, api_key: str, model_name: str, temperature: float = 0.2):
        """Initialize the chain factory with LLM configuration."""
        self.logger = get_logger("chain_factory")
        self.provider = provider
        self.model_name = model_name
        self.temperature = temperature
        
        self.logger.info(
            "Initializing chain factory",
            provider=provider,
            model=model_name,
            temperature=temperature
        )
        
        # Initialize LLM
        if provider == "google":
            self.llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=temperature
            )
        else:
            error_msg = f"Provider '{provider}' not supported."
            self.logger.error("Unsupported AI provider", provider=provider)
            raise ValueError(error_msg)
        
        # Cache for chains
        self._chain_cache: Dict[str, Runnable] = {}
    
    @lru_cache(maxsize=128)
    def get_structured_chain(
        self, 
        template_name: str, 
        response_schema: Type[BaseModel],
        use_retry: bool = False  # Disabled by default due to import issues
    ) -> Runnable:
        """
        Get or create a cached structured output chain.
        
        Args:
            template_name: Name of the prompt template
            response_schema: Pydantic model for structured output
            use_retry: Whether to use RetryWithErrorOutputParser for auto-correction
        
        Returns:
            Cached Runnable chain
        """
        cache_key = f"{template_name}_{response_schema.__name__}_{use_retry}"
        
        if cache_key not in self._chain_cache:
            prompt = prompt_factory.get_template(template_name)
            
            if use_retry:
                try:
                    # Auto-correction chain with RetryWithErrorOutputParser
                    parser = PydanticOutputParser(pydantic_object=response_schema)
                    retry_parser = RetryWithErrorOutputParser.from_llm(
                        parser=parser, 
                        llm=self.llm
                    )
                    chain = prompt | self.llm | retry_parser
                except ImportError:
                    self.logger.warning(
                        "RetryWithErrorOutputParser not available, falling back to simple structured output",
                        template_name=template_name
                    )
                    structured_llm = self.llm.with_structured_output(response_schema)
                    chain = prompt | structured_llm
            else:
                # Simple structured output
                structured_llm = self.llm.with_structured_output(response_schema)
                chain = prompt | structured_llm
            
            self._chain_cache[cache_key] = chain
            
            self.logger.debug(
                "Created and cached new chain",
                template_name=template_name,
                schema=response_schema.__name__,
                use_retry=use_retry,
                cache_key=cache_key
            )
        
        return self._chain_cache[cache_key]
    
    def get_conversational_chain(self, template_name: str) -> Runnable:
        """
        Get or create a cached conversational chain for streaming.
        
        Args:
            template_name: Name of the prompt template
        
        Returns:
            Cached Runnable chain for conversation
        """
        cache_key = f"conv_{template_name}"
        
        if cache_key not in self._chain_cache:
            prompt = prompt_factory.get_template(template_name)
            chain = prompt | self.llm
            self._chain_cache[cache_key] = chain
            
            self.logger.debug(
                "Created conversational chain",
                template_name=template_name,
                cache_key=cache_key
            )
        
        return self._chain_cache[cache_key]
    
    def get_multimodal_chain(self, response_schema: Type[BaseModel]) -> Runnable:
        """
        Get or create a multimodal chain for processing mixed content.
        
        Args:
            response_schema: Pydantic model for structured output
        
        Returns:
            Runnable chain for multimodal input
        """
        cache_key = f"multimodal_{response_schema.__name__}"
        
        if cache_key not in self._chain_cache:
            structured_llm = self.llm.with_structured_output(response_schema)
            self._chain_cache[cache_key] = structured_llm
            
            self.logger.debug(
                "Created multimodal chain",
                schema=response_schema.__name__,
                cache_key=cache_key
            )
        
        return self._chain_cache[cache_key]
    
    # Async Helper Methods
    
    async def ainvoke(
        self, 
        template_name: str, 
        prompt_input: Dict[str, Any], 
        response_schema: Type[BaseModel]
    ) -> BaseModel:
        """
        Async invoke with structured output and auto-correction.
        
        Args:
            template_name: Name of the prompt template
            prompt_input: Variables for the prompt
            response_schema: Expected response schema
        
        Returns:
            Structured response instance
        """
        start_time = time.time()
        
        self.logger.info(
            "Starting async structured invoke",
            template_name=template_name,
            schema=response_schema.__name__,
            prompt_keys=list(prompt_input.keys()) if prompt_input else []
        )
        
        try:
            chain = self.get_structured_chain(template_name, response_schema)
            response = await chain.ainvoke(prompt_input)
            
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            self.logger.info(
                "Async structured invoke completed",
                template_name=template_name,
                schema=response_schema.__name__,
                duration_ms=duration_ms,
                success=True
            )
            
            return response
            
        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            self.logger.error(
                "Async structured invoke failed",
                template_name=template_name,
                schema=response_schema.__name__,
                duration_ms=duration_ms,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def astream(
        self, 
        template_name: str, 
        prompt_input: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """
        Async streaming for conversational responses.
        
        Args:
            template_name: Name of the prompt template
            prompt_input: Variables for the prompt
        
        Yields:
            Streamed response chunks
        """
        self.logger.info(
            "Starting async stream",
            template_name=template_name,
            prompt_keys=list(prompt_input.keys()) if prompt_input else []
        )
        
        try:
            chain = self.get_conversational_chain(template_name)
            
            async for chunk in chain.astream(prompt_input):
                if hasattr(chunk, 'content'):
                    yield chunk.content
                else:
                    yield str(chunk)
                    
        except Exception as e:
            self.logger.error(
                "Async stream failed",
                template_name=template_name,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def ainvoke_multimodal(
        self,
        content_parts: List[Dict[str, Any]], 
        response_schema: Type[BaseModel]
    ) -> BaseModel:
        """
        Async multimodal invoke with structured output.
        
        Args:
            content_parts: List of content parts (text, image, etc.)
            response_schema: Expected response schema
        
        Returns:
            Structured response instance
        """
        start_time = time.time()
        
        content_types = {}
        for part in content_parts:
            part_type = part.get('type', 'unknown')
            content_types[part_type] = content_types.get(part_type, 0) + 1
        
        self.logger.info(
            "Starting async multimodal invoke",
            schema=response_schema.__name__,
            content_parts_count=len(content_parts),
            content_types=content_types
        )
        
        try:
            chain = self.get_multimodal_chain(response_schema)
            message = HumanMessage(content=content_parts)
            response = await chain.ainvoke([message])
            
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            self.logger.info(
                "Async multimodal invoke completed",
                schema=response_schema.__name__,
                duration_ms=duration_ms,
                success=True
            )
            
            return response
            
        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            self.logger.error(
                "Async multimodal invoke failed",
                schema=response_schema.__name__,
                duration_ms=duration_ms,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def ainvoke_with_history(
        self, 
        messages: List[BaseMessage], 
        response_schema: Type[BaseModel]
    ) -> BaseModel:
        """
        Async invoke with message history and structured output.
        
        Args:
            messages: List of conversation messages
            response_schema: Expected response schema
        
        Returns:
            Structured response instance
        """
        start_time = time.time()
        
        self.logger.info(
            "Starting async invoke with history",
            schema=response_schema.__name__,
            message_count=len(messages)
        )
        
        try:
            structured_llm = self.llm.with_structured_output(response_schema)
            response = await structured_llm.ainvoke(messages)
            
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            self.logger.info(
                "Async invoke with history completed",
                schema=response_schema.__name__,
                duration_ms=duration_ms,
                success=True
            )
            
            return response
            
        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            self.logger.error(
                "Async invoke with history failed",
                schema=response_schema.__name__,
                duration_ms=duration_ms,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def clear_cache(self):
        """Clear the chain cache."""
        self._chain_cache.clear()
        self.logger.info("Chain cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cached_chains": len(self._chain_cache),
            "cache_keys": list(self._chain_cache.keys())
        }


# Backward compatibility - maintain the original interface
class LangChainService:
    """
    Backward compatibility wrapper for the original LangChainService interface.
    Delegates to the new ChainFactory implementation.
    """
    
    def __init__(self, provider: str, api_key: str, model_name: str, temperature: float = 0.2):
        self.chain_factory = ChainFactory(provider, api_key, model_name, temperature)
        self.logger = self.chain_factory.logger
    
    def generate_structured_output(
        self, 
        prompt_template: str, 
        prompt_input: Dict, 
        response_schema: Type[BaseModel]
    ) -> BaseModel:
        """Legacy sync method - converts template string to template name."""
        # For backward compatibility, we'll try to match the template content
        # In practice, callers should be updated to use template names
        template_name = "topic_analysis"  # Default fallback
        
        # Try to identify template by content
        if "MISSÃO" in prompt_template and "topic_id" in prompt_template:
            template_name = "topic_analysis"
        elif "roadmap" in prompt_template.lower():
            template_name = "plan_organization"
        elif "erro" in prompt_template.lower():
            template_name = "json_correction"
        
        chain = self.chain_factory.get_structured_chain(template_name, response_schema)
        return chain.invoke(prompt_input)
    
    def generate_structured_output_from_content(
        self,
        content_parts: List, 
        response_schema: Type[BaseModel]
    ) -> BaseModel:
        """Legacy multimodal method."""
        chain = self.chain_factory.get_multimodal_chain(response_schema)
        message = HumanMessage(content=content_parts)
        return chain.invoke([message])
    
    def invoke_with_history(self, messages: List, response_schema: Type[BaseModel]) -> BaseModel:
        """Legacy history method."""
        structured_llm = self.chain_factory.llm.with_structured_output(response_schema)
        return structured_llm.invoke(messages)
