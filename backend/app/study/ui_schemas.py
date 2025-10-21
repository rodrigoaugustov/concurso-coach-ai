from typing import List, Optional

# --- IMPORTAÇÃO CORRETA E ÚNICA ---
# Usamos o Pydantic padrão (V2), pois a versão instalada do LangChain espera isso.
from pydantic import BaseModel, Field


# ===================================================================
# 1. DEFINIÇÃO DOS COMPONENTES INDIVIDUAIS
# ===================================================================

class TextBlock(BaseModel):
    content_md: str = Field(description="Conteúdo em formato Markdown.")

class FlipCard(BaseModel):
    front_text: str = Field(description="Texto para a frente do card.")
    back_text: str = Field(description="Texto para o verso do card.")

class CarouselItem(BaseModel):
    title: str = Field(description="O título deste slide.")
    content: str = Field(description="O conteúdo em texto deste slide.")

class Carousel(BaseModel):
    items: List[CarouselItem] = Field(description="Uma lista de slides para o carrossel.")

class QuizQuestion(BaseModel):
    question: str = Field(description="A pergunta do quiz.")
    options: List[str] = Field(description="Uma lista de 4 opções de resposta.")
    correct_answer: str = Field(description="A opção de resposta correta.")
    explanation: str = Field(description="Breve explicação da resposta correta.")

class Quiz(BaseModel):
    questions: List[QuizQuestion] = Field(description="Uma lista de 3 a 5 questões para a avaliação.")


# ===================================================================
# 2. SCHEMA "CONTAINER" E RESPOSTA PRINCIPAL
# ===================================================================

class LayoutItem(BaseModel):
    """
    Representa um único item no layout da aula. A IA deve preencher
    APENAS UM dos campos de componente (text_block, flip_card, etc.).
    """
    component_type: str = Field(description="O nome do componente usado: 'TextBlock', 'FlipCard', 'Carousel', ou 'Quiz'.")
    text_block: Optional[TextBlock] = None
    flip_card: Optional[FlipCard] = None
    carousel: Optional[Carousel] = None
    quiz: Optional[Quiz] = None

class ProceduralLayout(BaseModel):
    """
    O layout completo da aula, composto por uma lista de LayoutItems.
    """
    layout: List[LayoutItem]