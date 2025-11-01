# Este arquivo serve como um ponto de entrada para garantir que todos os modelos
# sejam importados e registrados no Base do SQLAlchemy antes que a aplicação
# tente usá-los, evitando erros de dependência circular.

from app.core.database import Base

from app.users.models import User, UserContest, UserTopicProgress
from app.contests.models import (
    PublishedContest,
    ContestRole,
    ExamStructure,
    ProgrammaticContent
)

from app.study.models import StudyRoadmapSession

# Import guided learning models to register them with SQLAlchemy
try:
    from app.study.guided_learning_persistence import ChatThreadModel, ChatMessageModel
except ImportError:
    # Fallback if guided learning models can't be imported
    pass
