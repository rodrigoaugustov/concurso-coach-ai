
from typing import Dict, List, Type
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel as LangChainBaseModel
from langchain_core.messages import HumanMessage
from pydantic import BaseModel


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
            raise ValueError(f"Provedor '{provider}' não suportado.")
        
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
        # Vincula o schema de saída ao modelo para forçar a resposta JSON
        structured_llm = self.llm.with_structured_output(response_schema)
        
        prompt = ChatPromptTemplate.from_template(prompt_template)
        
        # Cria a "cadeia" (chain) de execução: dados de entrada -> prompt -> modelo
        chain = prompt | structured_llm
        
        print(f"AI Service (LangChain): Invocando cadeia com schema {response_schema.__name__}...")
        # Executa a cadeia com os dados de entrada
        response = chain.invoke(prompt_input)
        print("AI Service (LangChain): Resposta estruturada recebida.")
        
        return response
    
    def generate_structured_output_from_content(
        self,
        content_parts: List, # Lista de partes (texto, imagem, pdf)
        response_schema: Type[LangChainBaseModel]
    ) -> LangChainBaseModel:
        """
        Gera uma saída estruturada a partir de uma lista de conteúdos (multimodal).
        """
        chain = self._create_chain(response_schema)
        
        # Constrói a mensagem a partir das partes
        message = HumanMessage(content=content_parts)
        
        print(f"AI Service (LangChain/Content): Invocando cadeia com schema {response_schema.__name__}...")
        response = chain.invoke([message])
        print("AI Service (LangChain/Content): Resposta recebida.")
        return response
    
    def invoke_with_history(self, messages: List, response_schema: Type[BaseModel]) -> BaseModel:
        structured_llm = self.llm.with_structured_output(response_schema)
        
        print(f"AI Service (LangChain/History): Invocando cadeia com histórico e schema {response_schema.__name__}...")
        response = structured_llm.invoke(messages)
        print("AI Service (LangChain/History): Resposta recebida.")
        return response