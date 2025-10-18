# Este arquivo serve como um ponto de entrada para garantir que todos os modelos
# sejam importados e registrados no Base do SQLAlchemy antes que a aplicação
# tente usá-los, evitando erros de dependência circular.

from app.core.database import Base

from app.users.models import User, UserContest, UserTopicProgress
from app.contests.models import (
    PublishedContest,
    ContestRole,
    ExamComposition,
    ProgrammaticContent
)