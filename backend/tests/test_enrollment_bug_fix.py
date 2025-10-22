# backend/tests/test_enrollment_bug_fix.py
"""
Testes para validar a correção do bug de inscrição duplicada (Issue #1).

Cenários testados:
1. Primeira inscrição em um cargo (deve funcionar)
2. Tentativa de re-inscrição no mesmo cargo (deve retornar 409)
3. Listagem de cargos disponíveis (deve filtrar cargos já inscritos)
4. Listagem de inscrições do usuário
"""

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.users.models import User, UserContest
from app.contests.models import ContestRole, PublishedContest, ContestStatus
from app.study.services import (
    subscribe_user_to_role,
    get_available_roles_for_user,
    get_user_enrolled_roles
)
from datetime import date

# === FIXTURES DE DADOS DE TESTE ===

@pytest.fixture
def sample_user(db_session: Session):
    """Cria um usuário de teste."""
    user = User(
        name="João Silva",
        email="joao.silva@test.com",
        password_hash="hashed_password_123"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def sample_contest_with_roles(db_session: Session):
    """Cria um concurso de teste com múltiplos cargos."""
    contest = PublishedContest(
        name="Concurso Banco Central 2025",
        exam_date=date(2025, 6, 15),
        status=ContestStatus.COMPLETED,
        file_url="https://example.com/edital.pdf",
        file_hash="abc123hash"
    )
    db_session.add(contest)
    db_session.flush()
    
    # Cria múltiplos cargos para o concurso
    roles = [
        ContestRole(job_title="Analista - Área 1", published_contest_id=contest.id),
        ContestRole(job_title="Analista - Área 2", published_contest_id=contest.id),
        ContestRole(job_title="Técnico Bancário", published_contest_id=contest.id),
    ]
    
    for role in roles:
        db_session.add(role)
    
    db_session.commit()
    return contest, roles

# === TESTES DE SERVIÇOS ===

class TestSubscribeUserToRole:
    """Testa o serviço de inscrição em cargos."""
    
    def test_first_enrollment_success(self, db_session: Session, sample_user: User, sample_contest_with_roles):
        """Testa que a primeira inscrição em um cargo funciona corretamente."""
        contest, roles = sample_contest_with_roles
        target_role = roles[0]  # Analista - Área 1
        
        # Primeira inscrição deve funcionar
        user_contest = subscribe_user_to_role(db=db_session, user=sample_user, role_id=target_role.id)
        
        assert user_contest is not None
        assert user_contest.user_id == sample_user.id
        assert user_contest.contest_role_id == target_role.id
        
        # Verifica que o registro foi salvo no banco
        db_enrollment = db_session.query(UserContest).filter(
            UserContest.user_id == sample_user.id,
            UserContest.contest_role_id == target_role.id
        ).first()
        assert db_enrollment is not None
    
    def test_duplicate_enrollment_raises_409(self, db_session: Session, sample_user: User, sample_contest_with_roles):
        """Testa que tentativa de re-inscrição retorna erro 409 Conflict."""
        contest, roles = sample_contest_with_roles
        target_role = roles[0]  # Analista - Área 1
        
        # Primeira inscrição
        subscribe_user_to_role(db=db_session, user=sample_user, role_id=target_role.id)
        
        # Segunda tentativa deve falhar com 409
        with pytest.raises(HTTPException) as exc_info:
            subscribe_user_to_role(db=db_session, user=sample_user, role_id=target_role.id)
        
        assert exc_info.value.status_code == 409
        assert "já está inscrito" in exc_info.value.detail.lower()
        assert target_role.job_title in exc_info.value.detail
    
    def test_enrollment_in_different_roles_allowed(self, db_session: Session, sample_user: User, sample_contest_with_roles):
        """Testa que o usuário pode se inscrever em cargos diferentes."""
        contest, roles = sample_contest_with_roles
        role_1, role_2 = roles[0], roles[1]
        
        # Inscrição no primeiro cargo
        user_contest_1 = subscribe_user_to_role(db=db_session, user=sample_user, role_id=role_1.id)
        
        # Inscrição no segundo cargo deve funcionar
        user_contest_2 = subscribe_user_to_role(db=db_session, user=sample_user, role_id=role_2.id)
        
        assert user_contest_1.contest_role_id != user_contest_2.contest_role_id
        
        # Verifica que ambos estão no banco
        enrollments = db_session.query(UserContest).filter(
            UserContest.user_id == sample_user.id
        ).all()
        assert len(enrollments) == 2
    
    def test_nonexistent_role_raises_404(self, db_session: Session, sample_user: User):
        """Testa que tentativa de inscrição em cargo inexistente retorna 404."""
        nonexistent_role_id = 99999
        
        with pytest.raises(HTTPException) as exc_info:
            subscribe_user_to_role(db=db_session, user=sample_user, role_id=nonexistent_role_id)
        
        assert exc_info.value.status_code == 404
        assert "Role not found" in exc_info.value.detail

class TestGetAvailableRolesForUser:
    """Testa o serviço que lista cargos disponíveis para inscrição."""
    
    def test_all_roles_available_for_new_user(self, db_session: Session, sample_user: User, sample_contest_with_roles):
        """Testa que usuário novo vê todos os cargos como disponíveis."""
        contest, roles = sample_contest_with_roles
        
        available_roles = get_available_roles_for_user(db=db_session, user=sample_user)
        
        # Todos os 3 cargos devem estar disponíveis
        assert len(available_roles) == 3
        available_titles = {role.job_title for role in available_roles}
        expected_titles = {role.job_title for role in roles}
        assert available_titles == expected_titles
    
    def test_enrolled_roles_excluded_from_available(self, db_session: Session, sample_user: User, sample_contest_with_roles):
        """Testa que cargos já inscritos são excluídos da lista de disponíveis."""
        contest, roles = sample_contest_with_roles
        enrolled_role = roles[0]  # Analista - Área 1
        
        # Inscreve o usuário no primeiro cargo
        subscribe_user_to_role(db=db_session, user=sample_user, role_id=enrolled_role.id)
        
        # Lista cargos disponíveis
        available_roles = get_available_roles_for_user(db=db_session, user=sample_user)
        
        # Deve ter 2 cargos disponíveis (excluindo o inscrito)
        assert len(available_roles) == 2
        available_titles = {role.job_title for role in available_roles}
        assert enrolled_role.job_title not in available_titles
        assert "Analista - Área 2" in available_titles
        assert "Técnico Bancário" in available_titles
    
    def test_multiple_enrollments_reduce_available_roles(self, db_session: Session, sample_user: User, sample_contest_with_roles):
        """Testa que múltiplas inscrições reduzem progressivamente os cargos disponíveis."""
        contest, roles = sample_contest_with_roles
        
        # Estado inicial: 3 cargos disponíveis
        available_roles = get_available_roles_for_user(db=db_session, user=sample_user)
        assert len(available_roles) == 3
        
        # Inscreve no primeiro cargo
        subscribe_user_to_role(db=db_session, user=sample_user, role_id=roles[0].id)
        available_roles = get_available_roles_for_user(db=db_session, user=sample_user)
        assert len(available_roles) == 2
        
        # Inscreve no segundo cargo
        subscribe_user_to_role(db=db_session, user=sample_user, role_id=roles[1].id)
        available_roles = get_available_roles_for_user(db=db_session, user=sample_user)
        assert len(available_roles) == 1
        
        # Inscreve no terceiro cargo
        subscribe_user_to_role(db=db_session, user=sample_user, role_id=roles[2].id)
        available_roles = get_available_roles_for_user(db=db_session, user=sample_user)
        assert len(available_roles) == 0

class TestGetUserEnrolledRoles:
    """Testa o serviço que lista inscrições do usuário."""
    
    def test_empty_enrollments_for_new_user(self, db_session: Session, sample_user: User, sample_contest_with_roles):
        """Testa que usuário novo não tem inscrições."""
        enrolled_roles = get_user_enrolled_roles(db=db_session, user=sample_user)
        assert len(enrolled_roles) == 0
    
    def test_enrolled_roles_listed_correctly(self, db_session: Session, sample_user: User, sample_contest_with_roles):
        """Testa que inscrições do usuário são listadas corretamente."""
        contest, roles = sample_contest_with_roles
        
        # Inscreve em 2 cargos
        subscribe_user_to_role(db=db_session, user=sample_user, role_id=roles[0].id)
        subscribe_user_to_role(db=db_session, user=sample_user, role_id=roles[1].id)
        
        # Lista inscrições
        enrolled_subscriptions = get_user_enrolled_roles(db=db_session, user=sample_user)
        
        assert len(enrolled_subscriptions) == 2
        enrolled_role_ids = {sub.contest_role_id for sub in enrolled_subscriptions}
        assert roles[0].id in enrolled_role_ids
        assert roles[1].id in enrolled_role_ids
        assert roles[2].id not in enrolled_role_ids

# === TESTES DE INTEGRAÇÃO (ENDPOINTS) ===

# Note: Para testes de endpoints, seria necessário usar o TestClient do FastAPI
# e mockar a autenticação. Por simplicidade, focamos nos testes de serviços.

class TestEnrollmentWorkflow:
    """Testa o fluxo completo de inscrição."""
    
    def test_complete_enrollment_workflow(self, db_session: Session, sample_user: User, sample_contest_with_roles):
        """Testa o fluxo completo: listar → inscrever → verificar."""
        contest, roles = sample_contest_with_roles
        target_role = roles[0]
        
        # 1. Usuário vê todos os cargos disponíveis
        available_before = get_available_roles_for_user(db=db_session, user=sample_user)
        assert len(available_before) == 3
        
        # 2. Usuário se inscreve em um cargo
        enrollment = subscribe_user_to_role(db=db_session, user=sample_user, role_id=target_role.id)
        assert enrollment.contest_role_id == target_role.id
        
        # 3. Cargo inscrito não aparece mais nos disponíveis
        available_after = get_available_roles_for_user(db=db_session, user=sample_user)
        assert len(available_after) == 2
        
        # 4. Cargo aparece nas inscrições do usuário
        user_enrollments = get_user_enrolled_roles(db=db_session, user=sample_user)
        assert len(user_enrollments) == 1
        assert user_enrollments[0].contest_role_id == target_role.id
        
        # 5. Tentativa de re-inscrição falha
        with pytest.raises(HTTPException) as exc_info:
            subscribe_user_to_role(db=db_session, user=sample_user, role_id=target_role.id)
        assert exc_info.value.status_code == 409

# === CONFIGURAÇÃO DE PYTEST ===

# Note: Este arquivo assume que existe um conftest.py com as fixtures:
# - db_session: Session do SQLAlchemy para testes
# - Configuração de banco de dados de teste
# - Limpeza automática entre testes