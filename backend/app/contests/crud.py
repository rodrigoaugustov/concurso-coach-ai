from sqlalchemy.orm import Session
from . import models

def create_contest(db: Session, name: str, file_hash: str, file_content: bytes, file_url: str = None) -> models.PublishedContest:
    db_contest = models.PublishedContest(
        name=name,
        file_url=file_url,
        file_hash=file_hash,
        file_content=file_content,
        status=models.ContestStatus.PENDING
    )
    db.add(db_contest)
    db.commit()
    db.refresh(db_contest)
    return db_contest

def get_contest_by_hash(db: Session, file_hash: str):
    return db.query(models.PublishedContest).filter(models.PublishedContest.file_hash == file_hash).first()

def save_structured_edict_data(db: Session, contest_id: int, data: dict):
    """
    Salva os dados estruturados extraídos pela IA no banco de dados.
    """
    contest = db.query(models.PublishedContest).filter(models.PublishedContest.id == contest_id).first()
    if not contest:
        raise Exception(f"Concurso com ID {contest_id} não encontrado para salvar dados estruturados.")

    # Atualiza o nome oficial do concurso
    official_name = data.get("contest_name")
    if official_name:
        contest.name = official_name

    exam_date = data.get("exam_date")
    if exam_date:                    
        contest.exam_date = exam_date
    
    # Limpa dados antigos, caso seja um reprocessamento
    for role in contest.roles:
        db.delete(role)
    db.commit()

    # Itera e salva os novos dados
    for role_data in data.get("contest_roles", []):
        new_role = models.ContestRole(
            job_title=role_data.get("job_title"),
            contest=contest
        )
        db.add(new_role)

        for comp_data in role_data.get("exam_composition", []):
            new_structure_item = models.ExamStructure(
                level_name=comp_data.get("level_name"),
                level_type=comp_data.get("level_type"),
                number_of_questions=comp_data.get("number_of_questions"),
                weight_per_question=comp_data.get("weight_per_question"),
                role=new_role
            )
            db.add(new_structure_item)

        for content_data in role_data.get("programmatic_content", []):
            new_content = models.ProgrammaticContent(
                exam_module=content_data.get("exam_module"),
            subject=content_data.get("subject"),
            topic=content_data.get("topic"),
            role=new_role
            )
            db.add(new_content)
            
    db.commit()
