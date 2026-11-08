import json
import pytest
from django.urls import reverse

from apps.accounts.models import Administrador, Professor, Usuario
from apps.audit.models import AuditLog
from apps.institution.domain.services.pairing_service import MachinePairingService
from apps.institution.forms import CampusForm
from apps.institution.models import Campus, Institution, Machine, Room


@pytest.fixture
def cenario_instituicao(db):
    # Cria o cenario institucional com instituicao, campus, sala e usuario administrador
    inst = Institution.objects.create(
        nome="Universidade de Mogi das Cruzes",
        cnpj="54303514000185",
    )
    campus = Campus.objects.create(
        instituicao=inst,
        nome="Campus Sede",
        latitude="-23.5169621",
        longitude="-46.1826845",
        raio_metros=300,
    )
    sala = Room.objects.create(campus=campus, codigo="B-207", nome="Laboratorio 7")
    user_admin = Usuario.objects.create_user(
        email="admin.infra@umc.br",
        password="testpassword123",
        instituicao=inst,
    )
    Administrador.objects.create(usuario=user_admin, cargo="Infraestrutura")
    return {
        "inst": inst,
        "campus": campus,
        "sala": sala,
        "user": user_admin,
    }


@pytest.mark.django_db
def test_usuario_sem_perfil_admin_eh_redirecionado_em_infraestrutura(
    client, cenario_instituicao
):
    # Usuario sem perfil de administrador e redirecionado pelo decorator @only_admin
    user_prof = Usuario.objects.create_user(
        email="prof.sem.admin@umc.br",
        password="testpassword123",
        instituicao=cenario_instituicao["inst"],
    )
    Professor.objects.create(usuario=user_prof, area_atuacao="Engenharia de Software")
    client.force_login(user_prof)

    resp = client.get(reverse("institution:infraestrutura"))
    assert resp.status_code == 302


@pytest.mark.django_db
def test_crud_completo_campus_sala_e_maquina(client, cenario_instituicao):
    client.force_login(cenario_instituicao["user"])

    # 1. Criar Campus (vincula instituicao automaticamente sem pedir no formulario)
    resp_c = client.post(
        reverse("institution:criar_campus"),
        data={
            "nome": "Campus Villa Lobos",
            "latitude": "-23.5469621",
            "longitude": "-46.7226845",
            "raio_metros": 250,
        },
    )
    assert resp_c.status_code == 302
    novo_campus = Campus.objects.get(nome="Campus Villa Lobos")
    assert novo_campus.instituicao_id == cenario_instituicao["inst"].id

    # 2. Editar Campus
    client.post(
        reverse("institution:editar_campus", kwargs={"campus_id": novo_campus.id}),
        data={
            "nome": "Campus Villa Lobos II",
            "latitude": "-23.5469621",
            "longitude": "-46.7226845",
            "raio_metros": 400,
        },
    )
    novo_campus.refresh_from_db()
    assert novo_campus.nome == "Campus Villa Lobos II"
    assert novo_campus.raio_metros == 400

    # 3. Criar e Editar Sala
    client.post(
        reverse("institution:criar_sala"),
        data={"campus": novo_campus.id, "codigo": "VL-101", "nome": "Lab Redes"},
    )
    nova_sala = Room.objects.get(codigo="VL-101")

    client.post(
        reverse("institution:editar_sala", kwargs={"sala_id": nova_sala.id}),
        data={
            "campus": novo_campus.id,
            "codigo": "VL-102",
            "nome": "Lab Redes Avancado",
        },
    )
    nova_sala.refresh_from_db()
    assert nova_sala.codigo == "VL-102"

    # 4. Criar, Editar e Excluir Maquina (codigo de pareamento permanece intacto na edicao)
    client.post(
        reverse("institution:criar_maquina"),
        data={"sala": nova_sala.id, "apelido": "PC-VL-01"},
    )
    maq = Machine.objects.get(apelido="PC-VL-01")
    codigo_original = maq.codigo_pareamento

    client.post(
        reverse("institution:editar_maquina", kwargs={"maquina_id": maq.id}),
        data={"sala": nova_sala.id, "apelido": "PC-VL-01-EDITADO"},
    )
    maq.refresh_from_db()
    assert maq.apelido == "PC-VL-01-EDITADO"
    assert maq.codigo_pareamento == codigo_original

    client.post(reverse("institution:excluir_maquina", kwargs={"maquina_id": maq.id}))
    assert Machine.objects.filter(pk=maq.id).exists() is False

    # 5. Excluir Sala e Campus
    client.post(reverse("institution:excluir_sala", kwargs={"sala_id": nova_sala.id}))
    assert Room.objects.filter(pk=nova_sala.id).exists() is False

    client.post(
        reverse("institution:excluir_campus", kwargs={"campus_id": novo_campus.id})
    )
    assert Campus.objects.filter(pk=novo_campus.id).exists() is False


@pytest.mark.django_db
def test_campus_form_rejeita_coordenadas_ou_raio_invalidos(cenario_instituicao):
    # Formulario rejeita latitudes fora de -90 a 90 e raios menores ou iguais a zero
    form = CampusForm(
        data={
            "nome": "Campus Invalido",
            "latitude": "-95.0000000",
            "longitude": "-46.1826845",
            "raio_metros": 0,
        }
    )
    assert form.is_valid() is False
    assert "latitude" in form.errors
    assert "raio_metros" in form.errors


@pytest.mark.django_db
def test_criar_e_regenerar_codigo_pareamento_4_digitos(cenario_instituicao):
    # Valida geracao inicial e regeneracao do codigo com registro de auditoria
    svc = MachinePairingService()
    maquina = svc.criar_maquina(
        sala=cenario_instituicao["sala"],
        apelido="PC-BANCADA-01",
        autor_id=cenario_instituicao["user"].id,
    )

    assert len(maquina.codigo_pareamento) == 4
    assert maquina.codigo_pareamento.isdigit()

    svc.regenerar_codigo(maquina_id=maquina.id, autor_id=cenario_instituicao["user"].id)
    maquina.refresh_from_db()

    assert len(maquina.codigo_pareamento) == 4
    assert AuditLog.objects.filter(
        acao="CODIGO_PAREAMENTO_REGENERADO",
        linha_tabela_id=maquina.id,
    ).exists()


@pytest.mark.django_db
def test_endpoint_parear_maquina_atualiza_ip_e_visto_em(client, cenario_instituicao):
    # Endpoint do PySide6 envia o codigo e o Django atualiza IP e visto_em
    svc = MachinePairingService()
    maquina = svc.criar_maquina(
        sala=cenario_instituicao["sala"],
        apelido="PC-BANCADA-02",
        autor_id=cenario_instituicao["user"].id,
    )

    url = reverse("institution:parear_maquina_api")
    resp = client.post(
        url,
        data=json.dumps({"codigo_pareamento": maquina.codigo_pareamento}),
        content_type="application/json",
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["pareado"] is True
    assert payload["sala_codigo"] == "B-207"

    maquina.refresh_from_db()
    assert maquina.ip is not None
    assert maquina.visto_em is not None
