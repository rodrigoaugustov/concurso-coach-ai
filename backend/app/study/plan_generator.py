# Em backend/app/study/plan_generator.py

import json
from datetime import date
from typing import List, Type
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

# Importações de modelos do nosso app
from app.users.models import UserContest
from app.contests.models import ExamStructure, ProgrammaticContent, ContestRole
from app.users.models import UserTopicProgress
from app.core.ai_service import LangChainService
from .models import StudyRoadmapSession

# Importações dos nossos schemas e prompts
from .ai_schemas import AITopicAnalysisResponse, AIStudyPlanResponse
from .prompts import topic_analysis_prompt, plan_organization_prompt

# --- NOVAS IMPORTAÇÕES PARA O LANGCHAIN ---
from app.core.settings import settings # Para pegar a API Key
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel
from typing import Callable

class StudyPlanGenerator:
    def __init__(self, db: Session, user_contest: UserContest):
        self.db = db
        self.user_contest = user_contest
        self.conversation_history = []  # Histórico de mensagens para o LangChain
        
        # Instancia o serviço LangChain, configurado para o Google Gemini
        self.ai_service = LangChainService(
            provider="google",
            api_key=settings.GEMINI_API_KEY,
            model_name="gemini-2.5-pro",
            temperature=0.5
        )
        
        # Atributos que serão preenchidos durante o pipeline
        self.total_sessions = 0
        self.topics_data_for_ai = []
        self.analyzed_data = None
        self.final_plan = None

    def _collect_initial_data(self):
        """Etapa 0: Coleta todos os dados necessários do banco."""
        print("Pipeline - Etapa 0: Coletando dados iniciais...")
        
        # Lógica para calcular N (total de sessões)
        exam_date = self.user_contest.role.contest.exam_date
        if not exam_date:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contest has no exam date set.")
        days_until_exam = (exam_date - date.today()).days
        if days_until_exam <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exam date is in the past.")
        self.total_sessions = days_until_exam * 2

        # Lógica para calcular o impacto efetivo
        exam_structures = self.db.query(ExamStructure).filter(
            ExamStructure.contest_role_id == self.user_contest.contest_role_id
        ).all()
        impact_map = {}
        for s in exam_structures:
            questions = s.number_of_questions or 0
            weight = s.weight_per_question or 0
            total_impact = questions * weight
            if total_impact > 0:
                impact_map[(s.level_type.value, s.level_name)] = total_impact
        default_impact = 1.0

        # Lógica para coletar os tópicos e proficiência
        topics_with_proficiency = self.db.query(
            ProgrammaticContent, UserTopicProgress.current_proficiency_score
        ).join(
            UserTopicProgress, UserTopicProgress.programmatic_content_id == ProgrammaticContent.id
        ).filter(
            ProgrammaticContent.contest_role_id == self.user_contest.contest_role_id,
            UserTopicProgress.user_contest_id == self.user_contest.id
        ).all()

        for topic, proficiency in topics_with_proficiency:
            effective_impact = impact_map.get(("SUBJECT", topic.subject), None)
            if effective_impact is None:
                effective_impact = impact_map.get(("MODULE", topic.exam_module), default_impact)
            
            self.topics_data_for_ai.append({
                "topic_id": topic.id,
                "exam_module": topic.exam_module,
                "subject": topic.subject,
                "topic_name": topic.topic,
                "proficiency": proficiency,
                "subject_weight": effective_impact
            })

    def _run_analysis_phase(self):
        print("Pipeline - Etapa 1: Analisando tópicos com validação...")
        prompt_input = {"topics_json": json.dumps(self.topics_data_for_ai, indent=2)}
        
        ai_response_obj = self._invoke_ai_with_validation(
            prompt_template=topic_analysis_prompt,
            prompt_input=prompt_input,
            response_schema=AITopicAnalysisResponse,
            validation_function=self._validate_analysis_phase_output # <-- Passa a função de validação
        )
        self.analyzed_data = ai_response_obj.dict()

    def _run_organization_phase(self):
        print("Pipeline - Etapa 2: Organizando o plano de estudos com validação...")
        prompt_input = {
            "total_sessions": self.total_sessions,
            "analyzed_topics_json": json.dumps(self.analyzed_data, indent=2)
        }
        
        final_plan_obj = self._invoke_ai_with_validation(
            prompt_template=plan_organization_prompt,
            prompt_input=prompt_input,
            response_schema=AIStudyPlanResponse,
            validation_function=self._validate_organization_phase_output # <-- Passa a função de validação
        )
        self.final_plan = final_plan_obj.dict()

    def _save_plan_to_db(self):
        """Etapa 3: Persiste o plano final no banco de dados."""
        print("Pipeline - Etapa 3: Salvando o roadmap no banco de dados...")

        # Limpa o roadmap antigo
        self.db.query(StudyRoadmapSession).filter(StudyRoadmapSession.user_contest_id == self.user_contest.id).delete()

        all_user_topics = self.db.query(ProgrammaticContent).filter(
            ProgrammaticContent.contest_role_id == self.user_contest.contest_role_id
        ).all()
        topic_id_to_obj_map = {topic.id: topic for topic in all_user_topics}
        
        new_sessions_to_add = []
        for session_data in self.final_plan.get("roadmap", []):
            topic_ids_list = session_data.get("topic_ids", [])
            if not topic_ids_list: continue

            new_session = StudyRoadmapSession(
                user_contest_id=self.user_contest.id,
                session_number=session_data.get("session_number"),
                summary=session_data.get("summary"),
                priority_level=session_data.get("priority_level"),
                priority_reason=session_data.get("priority_reason")
            )
            
            topics_in_session = [topic_id_to_obj_map.get(tid) for tid in topic_ids_list if tid in topic_id_to_obj_map]
            
            if topics_in_session:
                new_session.topics = topics_in_session
                new_sessions_to_add.append(new_session)

        self.db.add_all(new_sessions_to_add)
        self.db.commit()
        
        return len(new_sessions_to_add)
    
    def _validate_analysis_phase_output(self, analysis_response: AITopicAnalysisResponse) -> List[str]:
        """
        Executa validações de negócio determinísticas na saída da fase de análise.
        Retorna uma lista de erros encontrados. Se a lista estiver vazia, a validação passou.
        """
        errors = []
        
        # Validação 1: Completude (todos os tópicos de entrada estão na saída?)
        input_ids = {topic['topic_id'] for topic in self.topics_data_for_ai}
        # CORREÇÃO: Acessa o atributo com notação de ponto
        output_ids = {analysis.topic_id for analysis in analysis_response.analyzed_topics}

        if input_ids != output_ids:
            missing_ids = input_ids - output_ids
            extra_ids = output_ids - input_ids
            if missing_ids:
                errors.append(f"Validação falhou: A IA não analisou os seguintes topic_ids: {missing_ids}.")
            if extra_ids:
                errors.append(f"Validação falhou: A IA inventou os seguintes topic_ids: {extra_ids}.")
        
        # Validação 2: Valores de 'estimated_sessions'
        for analysis in analysis_response.analyzed_topics:
            # CORREÇÃO: Acessa o atributo com notação de ponto
            sessions = analysis.estimated_sessions
            if sessions is None or sessions <= 0 or sessions > 10: # Define um limite razoável
                errors.append(f"Validação falhou: 'estimated_sessions' inválido ({sessions}) para o topic_id {analysis.topic_id}.")

        # Validação 3: Diversidade de 'priority_level'
        # CORREÇÃO: Acessa o atributo com notação de ponto
        priority_levels = {analysis.priority_level for analysis in analysis_response.analyzed_topics}
        if len(priority_levels) == 1 and len(output_ids) > 1:
            errors.append(f"Validação falhou: A IA atribuiu o mesmo nível de prioridade '{list(priority_levels)[0]}' para todos os tópicos.")

        return errors
    
    def _validate_organization_phase_output(self, plan_response: AIStudyPlanResponse) -> List[str]:
        """
        Executa validações de negócio determinísticas na saída da fase de organização.
        """
        errors = []
        
        # Validação 1: Limite de sessões
        if len(plan_response.roadmap) > self.total_sessions:
            errors.append(f"Validação falhou: O plano gerado ({len(plan_response.roadmap)} sessões) excede o limite disponível ({self.total_sessions}).")

        # Validação 2: Completude dos tópicos
        input_ids = {topic['topic_id'] for topic in self.topics_data_for_ai}
        output_ids = set()
        for session in plan_response.roadmap:
            # CORREÇÃO: Acessa o atributo com notação de ponto
            for topic_id in session.topic_ids:
                output_ids.add(topic_id)
        
        if input_ids != output_ids:
            missing_ids = input_ids - output_ids
            extra_ids = output_ids - input_ids
            if missing_ids:
                errors.append(f"Validação falhou: O plano final não incluiu os seguintes topic_ids: {missing_ids}.")
            if extra_ids:
                errors.append(f"Validação falhou: O plano final incluiu topic_ids inventados: {extra_ids}.")

        return errors
    
    def _invoke_ai_with_validation(
        self, 
        prompt_template: str, 
        prompt_input: dict, 
        response_schema: Type[BaseModel],
        validation_function: Callable[[BaseModel], List[str]],
        max_retries: int = 2
    ) -> BaseModel:
        """
        Orquestra uma chamada de IA com um ciclo de validação e auto-correção.

        1. Envia o prompt para a IA.
        2. Valida a resposta sintaticamente (contra o schema Pydantic via LangChain).
        3. Executa uma função de validação de negócio (determinística).
        4. Se qualquer validação falhar, constrói um prompt de correção e tenta novamente.
        """

        current_messages = self.conversation_history.copy()
        prompt = ChatPromptTemplate.from_template(prompt_template)
        
        # Formata e adiciona a mensagem do usuário à lista de mensagens da tentativa atual
        user_messages = prompt.format_messages(**prompt_input)
        current_messages.extend(user_messages)

        last_error = None
        ai_response_obj = None

        for attempt in range(max_retries + 1):
            print(f"--- Iniciando chamada à IA (Tentativa {attempt + 1}/{max_retries + 1}) ---")
            try:
                ai_response_obj = self.ai_service.invoke_with_history(
                    messages=current_messages,
                    response_schema=response_schema
                )
                
                print("Validando regras de negócio da resposta da IA...")
                validation_errors = validation_function(ai_response_obj)
                
                if validation_errors:
                    error_message = "Validação de negócio falhou:\n- " + "\n- ".join(validation_errors)
                    raise ValueError(error_message)

                print("--- Validação bem-sucedida! ---")
                
                # --- CORREÇÃO PRINCIPAL ---
                # 1. Atualiza o histórico principal com as mensagens do usuário desta rodada
                self.conversation_history = current_messages
                
                # 2. Converte a resposta Pydantic para uma string JSON
                ai_response_json_str = ai_response_obj.json()
                
                # 3. Adiciona a resposta da IA ao histórico como um objeto AIMessage
                self.conversation_history.append(AIMessage(content=ai_response_json_str))
                
                return ai_response_obj

            except Exception as e:
                last_error = e
                print(f"AVISO: Tentativa {attempt + 1} falhou. Erro: {e}")
                
                if attempt >= max_retries:
                    print("ERRO FATAL: Número máximo de tentativas de correção atingido.")
                    raise last_error
                
                # Tenta extrair a resposta inválida da IA para usar no prompt de correção
                invalid_response_str = ""
                if ai_response_obj: # Se já recebemos um objeto Pydantic (falha de validação de negócio)
                    invalid_response_str = ai_response_obj.json()
                elif hasattr(e, 'llm_output'): # Se for um erro do LangChain
                    invalid_response_str = getattr(e, 'llm_output', str(e))
                else:
                    invalid_response_str = str(e)

                from .prompts import json_correction_prompt
                correction_prompt_input = {
                    "error_message": str(e),
                    "invalid_response": invalid_response_str
                }
                correction_prompt = ChatPromptTemplate.from_template(json_correction_prompt)
                current_messages.extend(correction_prompt.format_messages(**correction_prompt_input))
                print("Construindo e enviando prompt de correção...")

        raise Exception(f"Falha ao obter uma resposta válida da IA. Último erro: {last_error}")

    def generate(self):
        """Método principal que orquestra todo o pipeline."""
        self._collect_initial_data()
        self._run_analysis_phase()
        self._run_organization_phase()
        created_count = self._save_plan_to_db()
        return {"status": "success", "message": "Study plan generated successfully via LangChain pipeline.", "roadmap_items_created": created_count}