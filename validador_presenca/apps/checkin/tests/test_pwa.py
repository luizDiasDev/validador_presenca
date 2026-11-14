import json
from pathlib import Path

from django.conf import settings

from apps.accounts.models import Usuario
from apps.teacher_panel.models import Aluno
from apps.teacher_panel.tests.test_teacher_panel import cenario_professor  # noqa: F401

MANIFEST = Path(settings.BASE_DIR) / "static" / "manifest.webmanifest"


def test_manifest_opens_the_student_checkin_as_an_app():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["start_url"] == "/checkin/"
    assert manifest["display"] == "standalone"
    assert {icon["sizes"] for icon in manifest["icons"]} >= {"192x192", "512x512"}


def test_service_worker_is_served_from_the_site_root(client):
    response = client.get("/sw.js")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/javascript")
    assert "addEventListener" in response.content.decode()


def test_student_pages_link_the_manifest_and_register_the_worker(client, cenario_professor):
    student = Usuario.objects.create_user(email="aluno.pwa@alunos.umc.br", password="senha-forte-123")
    Aluno.objects.create(usuario=student, turma=cenario_professor["turma"], matricula="771122")
    client.force_login(student)

    for page in ("/checkin/", "/checkin/minhas-presencas/"):
        html = client.get(page).content.decode()
        assert "manifest.webmanifest" in html
        assert 'serviceWorker.register("/sw.js")' in html
