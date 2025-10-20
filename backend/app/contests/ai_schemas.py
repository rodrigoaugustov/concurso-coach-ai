from pydantic import BaseModel, Field
from typing import List
from datetime import date


class AIExamStructure(BaseModel):
    level_name: str = Field(description="O nome do agrupamento (ex: 'Conhecimentos Básicos' ou 'Língua Portuguesa').")
    level_type: str = Field(description="O tipo de agrupamento: 'MODULE' ou 'SUBJECT'.")
    number_of_questions: int = Field(description="Número de questões para este agrupamento.")
    weight_per_question: float = Field(description="Peso de cada questão neste agrupamento.")

class AIProgrammaticContent(BaseModel):
    exam_module: str = Field(description="O módulo da prova, ex: 'Conhecimentos Básicos'.")
    subject: str = Field(description="A matéria ou disciplina, ex: 'Língua Portuguesa'.")
    topic: str = Field(description="O tópico específico do edital, ex: 'Concordância Verbal'.")

class AIContestRole(BaseModel):
    job_title: str = Field(description="O nome do cargo, por exemplo, 'Analista Judiciário'.")
    exam_composition: List[AIExamStructure] = Field(description="A estrutura da prova, com pesos por módulo ou matéria.")
    programmatic_content: List[AIProgrammaticContent] = Field(description="A lista completa de tópicos organizados hierarquicamente.")

class EdictExtractionResponse(BaseModel):
    contest_name: str = Field(description="O nome oficial e completo do concurso público.")
    examining_board: str = Field(description="O nome da banca examinadora responsável pela aplicação da prova do concurso. Ex.: FGV, CESPE, FCC.")
    exam_date: date = Field(description="A data provável da prova objetiva, no formato AAAA-MM-DD. Caso não tenha essa informação, deixe como null.")
    contest_roles: List[AIContestRole] = Field(description="Lista de cargos oferecidos no concurso, com suas respectivas composições de prova e conteúdos programáticos.")