from django.test import RequestFactory

from apps.accounts.decorators import only_teacher, only_admin


class UsuarioSemPapel:
    pass


class UsuarioProfessor:
    def __init__(self):
        self.professor = object()


class UsuarioAdministrador:
    def __init__(self):
        self.administrador = object()


def _view_protegida(request):
    return "acesso liberado"


def test_only_teacher_allows_user_with_professor():
    request = RequestFactory().get("/qualquer-url/")
    request.user = UsuarioProfessor()

    view_decorada = only_teacher(_view_protegida)
    resultado = view_decorada(request)

    assert resultado == "acesso liberado"


def test_only_teacher_blocks_user_without_professor():
    request = RequestFactory().get("/qualquer-url/")
    request.user = UsuarioSemPapel()

    view_decorada = only_teacher(_view_protegida)
    resposta = view_decorada(request)

    assert resposta.status_code == 302
    assert resposta.url == "/accounts/login/"


def test_only_admin_allows_user_with_administrador():
    request = RequestFactory().get("/qualquer-url/")
    request.user = UsuarioAdministrador()

    view_decorada = only_admin(_view_protegida)
    resultado = view_decorada(request)

    assert resultado == "acesso liberado"


def test_only_admin_blocks_user_without_administrador():
    request = RequestFactory().get("/qualquer-url/")
    request.user = UsuarioSemPapel()

    view_decorada = only_admin(_view_protegida)
    resposta = view_decorada(request)

    assert resposta.status_code == 302