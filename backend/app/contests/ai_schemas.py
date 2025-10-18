from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date


class AIExamComposition(BaseModel):
    subject_name: str = Field(description="Nome da disciplina ou matéria.")
    number_of_questions: Optional[int] = Field(description="Quantidade de questões para esta disciplina.")
    weight_per_question: Optional[float] = Field(description="Peso de cada questão para esta disciplina.")

class AIProgrammaticContent(BaseModel):
    subject_name: str = Field(description="Nome da disciplina à qual este tópico pertence.")
    topic_group: str = Field(description="O grupo lógico ao qual este tópico pertence.")
    topic_name: str = Field(description="O tópico específico do conteúdo programático.")

class AIContestRole(BaseModel):
    job_title: str = Field(description="O nome do cargo, por exemplo, 'Analista Judiciário'.")
    exam_composition: List[AIExamComposition] = Field(description="Lista de disciplinas e a composição da prova para este cargo.")
    programmatic_content: List[AIProgrammaticContent] = Field(description="Lista de todos os tópicos do conteúdo programático para este cargo.")

class EdictExtractionResponse(BaseModel):
    contest_name: str = Field(description="O nome oficial e completo do concurso público.")
    examining_board: str = Field(description="O nome da banca examinadora responsável pelo concurso.")
    exam_date: Optional[date] = Field(description="A data provável da prova objetiva, no formato AAAA-MM-DD.")
    contest_roles: List[AIContestRole] = Field(description="Lista de cargos oferecidos no concurso.")