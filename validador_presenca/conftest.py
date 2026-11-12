# Separa os testes: todo teste que usa o banco recebe o marcador "integration".
# Unitários:  pytest -m "not integration"
# Integração: pytest -m integration
import pytest
from django.test import TestCase

DB_FIXTURES = {"db", "transactional_db", "django_db_reset_sequences", "client", "admin_client"}


def pytest_collection_modifyitems(items):
    for item in items:
        test_class = getattr(item, "cls", None)
        uses_db = (
            item.get_closest_marker("django_db") is not None
            or DB_FIXTURES & set(getattr(item, "fixturenames", ()))
            or (test_class is not None and issubclass(test_class, TestCase))
        )
        if uses_db:
            item.add_marker(pytest.mark.integration)
