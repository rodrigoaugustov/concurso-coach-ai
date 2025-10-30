# Em backend/app/study/plan_generator.py

import json
import time
from datetime import date
from typing import List, Type
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

# Importações de modelos do nosso app
from app.users.models import UserContest
from app.contests.models import ExamStructure, ProgrammaticContent, ContestRole
from app.users.models import UserTopicProgress
from app.core.ai_service import LangChainService
from app.core.logging import get_logger, LogContext
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
        self.logger = get_logger("study.plan_generator")
        
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
        
        self.logger.info(
            "StudyPlanGenerator initialized",
            user_contest_id=user_contest.id,
            contest_name=user_contest.role.contest.name,
            user_id=user_contest.user_id
        )

    def _collect_initial_data(self):
        """Etapa 0: Coleta todos os dados necessários do banco."""
        collection_start = time.time()
        
        with LogContext(phase="data_collection", user_contest_id=self.user_contest.id) as phase_logger:
            phase_logger.info("Starting data collection phase")
            
            # Lógica para calcular N (total de sessões)
            exam_date = self.user_contest.role.contest.exam_date
            if not exam_date:
                phase_logger.error("Contest has no exam date set")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contest has no exam date set.")
                
            days_until_exam = (exam_date - date.today()).days
            if days_until_exam <= 0:
                phase_logger.error(
                    "Exam date is in the past",
                    exam_date=exam_date.isoformat(),
                    days_until_exam=days_until_exam
                )
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exam date is in the past.")
                
            self.total_sessions = days_until_exam * 2
            
            phase_logger.info(
                "Calculated total sessions",
                exam_date=exam_date.isoformat(),
                days_until_exam=days_until_exam,
                total_sessions=self.total_sessions
            )

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
            
            phase_logger.info(
                "Built impact map from exam structures",
                exam_structures_count=len(exam_structures),
                impact_map_size=len(impact_map)
            )

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
                
            collection_duration = round((time.time() - collection_start) * 1000, 2)
            
            phase_logger.info(
                "Data collection phase completed",
                duration_ms=collection_duration,
                topics_collected=len(self.topics_data_for_ai)
            )

    def _run_analysis_phase(self):
        analysis_start = time.time()
        
        with LogContext(phase="topic_analysis", user_contest_id=self.user_contest.id) as phase_logger:
            phase_logger.info(
                "Starting topic analysis phase",
                topics_count=len(self.topics_data_for_ai)
            )
            
            prompt_input = {"topics_json": json.dumps(self.topics_data_for_ai, indent=2)}
            
            ai_response_obj = self._invoke_ai_with_validation(
                prompt_template=topic_analysis_prompt,
                prompt_input=prompt_input,
                response_schema=AITopicAnalysisResponse,
                validation_function=self._validate_analysis_phase_output # <-- Passa a função de validação
            )
            
            self.analyzed_data = ai_response_obj.dict()
            
            analysis_duration = round((time.time() - analysis_start) * 1000, 2)
            
            # Conta prioridades para logging
            priority_counts = {}
            for topic in self.analyzed_data.get("analyzed_topics", []):
                priority = topic.get("priority_level", "UNKNOWN")
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
            phase_logger.info(
                "Topic analysis phase completed",
                duration_ms=analysis_duration,
                analyzed_topics_count=len(self.analyzed_data.get("analyzed_topics", [])),
                priority_distribution=priority_counts
            )

    def _run_organization_phase(self):
        organization_start = time.time()
        
        with LogContext(phase="plan_organization", user_contest_id=self.user_contest.id) as phase_logger:
            phase_logger.info(
                "Starting plan organization phase",
                total_sessions=self.total_sessions,
                analyzed_topics_count=len(self.analyzed_data.get("analyzed_topics", []))
            )
            
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
            
            organization_duration = round((time.time() - organization_start) * 1000, 2)
            
            # Conta sessões por prioridade
            priority_session_counts = {}
            for session in self.final_plan.get("roadmap", []):
                priority = session.get("priority_level", "UNKNOWN")
                priority_session_counts[priority] = priority_session_counts.get(priority, 0) + 1
            
            phase_logger.info(
                "Plan organization phase completed",
                duration_ms=organization_duration,
                roadmap_sessions_count=len(self.final_plan.get("roadmap", [])),
                priority_session_distribution=priority_session_counts
            )

    def _save_plan_to_db(self):
        """Etapa 3: Persiste o plano final no banco de dados."""
        persistence_start = time.time()
        
        with LogContext(phase="database_persistence", user_contest_id=self.user_contest.id) as phase_logger:
            phase_logger.info(
                "Starting database persistence phase",
                roadmap_sessions_to_save=len(self.final_plan.get("roadmap", []))
            )

            # Limpa o roadmap antigo
            deleted_count = self.db.query(StudyRoadmapSession).filter(
                StudyRoadmapSession.user_contest_id == self.user_contest.id
            ).delete()
            
            phase_logger.info(
                "Cleared previous roadmap sessions",
                deleted_sessions_count=deleted_count
            )

            all_user_topics = self.db.query(ProgrammaticContent).filter(
                ProgrammaticContent.contest_role_id == self.user_contest.contest_role_id
            ).all()
            topic_id_to_obj_map = {topic.id: topic for topic in all_user_topics}
            
            new_sessions_to_add = []
            skipped_sessions = 0
            
            for session_data in self.final_plan.get("roadmap", []):
                topic_ids_list = session_data.get("topic_ids", [])
                if not topic_ids_list:
                    skipped_sessions += 1
                    continue

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
                else:
                    skipped_sessions += 1

            self.db.add_all(new_sessions_to_add)
            self.db.commit()
            
            persistence_duration = round((time.time() - persistence_start) * 1000, 2)
            
            phase_logger.info(
                "Database persistence phase completed",
                duration_ms=persistence_duration,
                sessions_created=len(new_sessions_to_add),
                sessions_skipped=skipped_sessions
            )
            
            return len(new_sessions_to_add)
    
    def _validate_analysis_phase_output(self, analysis_response: AITopicAnalysisResponse) -> List[str]:
        """
        Executa validações de negócio determinísticas na saída da fase de análise.
        Retorna uma lista de erros encontrados. Se a lista estiver vazia, a validação passou.
        """
        validation_start = time.time()
        errors = []
        
        with LogContext(validation_phase="analysis", user_contest_id=self.user_contest.id) as val_logger:
            val_logger.debug("Starting analysis validation")
            
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
            invalid_sessions = []
            for analysis in analysis_response.analyzed_topics:
                # CORREÇÃO: Acessa o atributo com notação de ponto
                sessions = analysis.estimated_sessions
                if sessions is None or sessions <= 0 or sessions > 10: # Define um limite razoável
                    invalid_sessions.append((analysis.topic_id, sessions))
                    
            if invalid_sessions:
                errors.append(f"Validação falhou: 'estimated_sessions' inválidos: {invalid_sessions}")

            # Validação 3: Diversidade de 'priority_level'
            # CORREÇÃO: Acessa o atributo com notação de ponto
            priority_levels = {analysis.priority_level for analysis in analysis_response.analyzed_topics}
            if len(priority_levels) == 1 and len(output_ids) > 1:
                errors.append(f"Validação falhou: A IA atribuiu o mesmo nível de prioridade '{list(priority_levels)[0]}' para todos os tópicos.")
            
            validation_duration = round((time.time() - validation_start) * 1000, 2)
            
            val_logger.info(
                "Analysis validation completed",
                duration_ms=validation_duration,
                errors_found=len(errors),
                input_topics_count=len(input_ids),
                output_topics_count=len(output_ids),
                priority_diversity=len(priority_levels)
            )

        return errors
    
    def _validate_organization_phase_output(self, plan_response: AIStudyPlanResponse) -> List[str]:
        """
        Executa validações de negócio determinísticas na saída da fase de organização.
        """
        validation_start = time.time()
        errors = []
        
        with LogContext(validation_phase="organization", user_contest_id=self.user_contest.id) as val_logger:
            val_logger.debug("Starting organization validation")
            
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
            
            validation_duration = round((time.time() - validation_start) * 1000, 2)
            
            val_logger.info(
                "Organization validation completed",
                duration_ms=validation_duration,
                errors_found=len(errors),
                planned_sessions_count=len(plan_response.roadmap),
                max_allowed_sessions=self.total_sessions,
                input_topics_count=len(input_ids),
                output_topics_count=len(output_ids)
            )

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
        ai_start = time.time()
        
        with LogContext(ai_validation_cycle=True, schema=response_schema.__name__) as ai_logger:
            ai_logger.info(
                "Starting AI validation cycle",
                max_retries=max_retries,
                schema=response_schema.__name__
            )

            current_messages = self.conversation_history.copy()
            prompt = ChatPromptTemplate.from_template(prompt_template)
            
            # Formata e adiciona a mensagem do usuário à lista de mensagens da tentativa atual
            user_messages = prompt.format_messages(**prompt_input)
            current_messages.extend(user_messages)

            last_error = None
            ai_response_obj = None

            for attempt in range(max_retries + 1):
                attempt_start = time.time()
                
                ai_logger.info(
                    "Starting AI attempt",
                    attempt=attempt + 1,
                    max_attempts=max_retries + 1
                )
                
                try:
                    ai_response_obj = self.ai_service.invoke_with_history(
                        messages=current_messages,
                        response_schema=response_schema
                    )
                    
                    ai_logger.debug("Running business validation")
                    validation_errors = validation_function(ai_response_obj)
                    
                    if validation_errors:
                        error_message = "Validação de negócio falhou:\n- " + "\n- ".join(validation_errors)
                        raise ValueError(error_message)

                    attempt_duration = round((time.time() - attempt_start) * 1000, 2)
                    total_duration = round((time.time() - ai_start) * 1000, 2)
                    
                    ai_logger.info(
                        "AI validation cycle completed successfully",
                        attempt=attempt + 1,
                        attempt_duration_ms=attempt_duration,
                        total_duration_ms=total_duration
                    )
                    
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
                    attempt_duration = round((time.time() - attempt_start) * 1000, 2)
                    
                    ai_logger.warning(
                        "AI attempt failed",
                        attempt=attempt + 1,
                        duration_ms=attempt_duration,
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    
                    if attempt >= max_retries:
                        ai_logger.error(
                            "Maximum retry attempts reached - AI validation cycle failed",
                            total_attempts=max_retries + 1,
                            final_error=str(e)
                        )
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
                    
                    ai_logger.info(
                        "Built correction prompt for next attempt",
                        next_attempt=attempt + 2
                    )

            raise Exception(f"Falha ao obter uma resposta válida da IA. Último erro: {last_error}")

    def generate(self):
        """Método principal que orquestra todo o pipeline."""
        pipeline_start = time.time()
        
        with LogContext(pipeline="study_plan_generation", user_contest_id=self.user_contest.id) as pipeline_logger:
            pipeline_logger.info(
                "Starting study plan generation pipeline",
                contest_name=self.user_contest.role.contest.name,
                user_id=self.user_contest.user_id
            )
            
            try:
                self._collect_initial_data()
                self._run_analysis_phase()
                self._run_organization_phase()
                created_count = self._save_plan_to_db()
                
                pipeline_duration = round((time.time() - pipeline_start) * 1000, 2)
                
                pipeline_logger.info(
                    "Study plan generation pipeline completed successfully",
                    total_duration_ms=pipeline_duration,
                    roadmap_items_created=created_count,
                    total_sessions_available=self.total_sessions,
                    topics_processed=len(self.topics_data_for_ai)
                )
                
                return {
                    "status": "success", 
                    "message": "Study plan generated successfully via LangChain pipeline.", 
                    "roadmap_items_created": created_count
                }
                
            except Exception as e:
                pipeline_duration = round((time.time() - pipeline_start) * 1000, 2)
                
                pipeline_logger.error(
                    "Study plan generation pipeline failed",
                    total_duration_ms=pipeline_duration,
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise