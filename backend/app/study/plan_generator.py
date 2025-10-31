# Em backend/app/study/plan_generator.py (refatorado parcialmente para usar as novas classes)

import json
import time
from datetime import date
from typing import List, Type
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.users.models import UserContest
from app.core.ai_service import LangChainService
from app.core.logging import get_logger, LogContext
from app.core.constants import AIConstants, ValidationConstants
from .ai_schemas import AITopicAnalysisResponse, AIStudyPlanResponse

# Novas classes extraídas
from app.study.data_collector import StudyDataCollector
from app.study.topic_analyzer import StudyTopicAnalyzer
from app.study.plan_organizer import StudyPlanOrganizer
from app.study.plan_persister import StudyPlanPersister
from app.core.settings import settings


class StudyPlanGenerator:
    def __init__(self, db: Session, user_contest: UserContest):
        self.db = db
        self.user_contest = user_contest
        self.logger = get_logger("study.plan_generator")

        # Serviço de IA compartilhado pelas fases
        self.ai_service = LangChainService(
            provider="google",
            api_key=settings.GEMINI_API_KEY,
            model_name="gemini-2.5-pro",
            temperature=AIConstants.TEMPERATURE_BALANCED,
        )

        # Dependências (injeção facilita testes)
        self.collector = StudyDataCollector(db)
        self.analyzer = StudyTopicAnalyzer(self.ai_service)
        self.organizer = StudyPlanOrganizer(self.ai_service)
        self.persister = StudyPlanPersister(db)

    def generate(self):
        """Orquestra o pipeline de geração do plano de estudo."""
        pipeline_start = time.time()
        with LogContext(pipeline="study_plan_generation", user_contest_id=self.user_contest.id) as log:
            log.info("Starting study plan generation pipeline", contest_name=self.user_contest.role.contest.name, user_id=self.user_contest.user_id)
            try:
                # Etapa 0: Coleta de dados
                topics_data = self.collector.collect_topics_data(self.user_contest)

                # Etapa 1: Análise de tópicos (IA + validação)
                analysis_obj = self.analyzer.analyze_topics(topics_data, user_contest_id=self.user_contest.id)

                # Etapa 2: Organização do plano (IA + validação)
                input_ids = {t["topic_id"] for t in topics_data.topics_data_for_ai}
                final_plan_obj = self.organizer.organize_plan(
                    analysis=analysis_obj,
                    total_sessions=topics_data.total_sessions,
                    input_topic_ids=input_ids,
                    user_contest_id=self.user_contest.id,
                )

                # Etapa 3: Persistência
                created_count = self.persister.save_plan(self.user_contest, final_plan_obj)

                log.info(
                    "Study plan generation pipeline completed successfully",
                    total_duration_ms=round((time.time() - pipeline_start) * 1000, 2),
                    roadmap_items_created=created_count,
                    total_sessions_available=topics_data.total_sessions,
                    topics_processed=len(topics_data.topics_data_for_ai),
                )

                return {
                    "status": "success",
                    "message": "Study plan generated successfully via refactored pipeline.",
                    "roadmap_items_created": created_count,
                }

            except Exception as e:
                log.error(
                    "Study plan generation pipeline failed",
                    total_duration_ms=round((time.time() - pipeline_start) * 1000, 2),
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise
