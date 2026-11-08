import pytest
from django.urls import reverse

from apps.teacher_panel.tests.test_teacher_management import admin_client, platform_admin  # noqa: F401
from apps.teacher_panel.tests.test_teacher_panel import cenario_professor  # noqa: F401

ACTIVE_ITEM_CLASSES = 'rounded-lg bg-gold text-dark-blue font-semibold">'


def active_item_text(html):
    start = html.index(ACTIVE_ITEM_CLASSES)
    return html[start:start + 200]


@pytest.mark.parametrize("page, menu_text", [
    ("teacher_panel:turmas", "Minhas Turmas"),
    ("validator:painel", "Histórico de Presença"),
    ("checkin:qr_demo", "Chamada ao vivo"),
    ("teacher_panel:alunos", "Gestão de Alunos"),
    ("teacher_panel:chamadas", "Configurar Chamada"),
    ("teacher_panel:pendencias", "Pendências"),
    ("teacher_panel:dashboard", "Dashboard BI"),
    ("privacy:central", "Central de Privacidade"),
    ("privacy:solicitar_direito", "Central de Privacidade"),
])
def test_teacher_sees_only_the_current_page_highlighted(client, cenario_professor, page, menu_text):
    client.force_login(cenario_professor["user"])

    html = client.get(reverse(page)).content.decode()

    assert html.count(ACTIVE_ITEM_CLASSES) == 1
    assert menu_text in active_item_text(html)


@pytest.mark.parametrize("page, menu_text", [
    ("institution:infraestrutura", "Campus e Máquinas"),
    ("teacher_panel:alunos", "Gestão de Usuários"),
    ("teacher_panel:professores", "Gestão de Usuários"),
])
def test_admin_sees_only_the_current_page_highlighted(admin_client, page, menu_text):
    html = admin_client.get(reverse(page)).content.decode()

    assert html.count(ACTIVE_ITEM_CLASSES) == 1
    assert menu_text in active_item_text(html)