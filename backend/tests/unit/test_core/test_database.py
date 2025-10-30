import types
from contextlib import contextmanager
from app.core.database import engine, SessionLocal, get_db


def test_engine_exists():
    # Apenas valida que o engine foi importado e possui atributos básicos
    assert hasattr(engine, "connect")


def test_get_db_yields_and_closes(monkeypatch):
    calls = {"closed": False}

    class DummySession:
        def close(self):
            calls["closed"] = True

    def dummy_sessionlocal():
        return DummySession()

    monkeypatch.setattr("app.core.database.SessionLocal", dummy_sessionlocal)

    gen = get_db()
    assert hasattr(gen, "__iter__")

    # Consome o generator
    db = next(gen)
    assert isinstance(db, DummySession)

    try:
        next(gen)
    except StopIteration:
        pass

    assert calls["closed"] is True
