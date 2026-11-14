import hashlib
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from apps.checkin.domain.services.chamada_service import ChamadaService
from apps.checkin.domain.services.qr_service import QrTokenService
from apps.checkin.models import ChamadaSession
from apps.validator.domain.case import register_checkin
from apps.institution.domain.services.geolocation_service import GeolocationService
from apps.institution.domain.services.geocoding_service import GeocodingService
from apps.institution.models import Campus, Machine
from django.contrib.auth.decorators import login_required
from apps.accounts.decorators import only_student
from apps.biometrics.domain.services.biometric_service import BiometricService, BiometricTermUnavailableError
from apps.biometrics.models import Biometria
from apps.class_client.domain.services.face_authorization_service import (
    MODE_CHECKIN,
    MODE_ENROLLMENT,
    FaceAuthorization,
    FaceAuthorizationService,
)
from apps.validator.models import PresencaRecord


@login_required
@only_student
def qr_demo(request):
    if request.method != "POST":
        return render(request, "checkin/checkin_aluno.html", {"token": request.GET.get("t", "")})

    svc = QrTokenService(cache=cache)
    resultado, geo_resultado, endereco_aluno, registro, results_pack = _registrar_checkin(request, svc)
    contexto = {
        "enviado": True,
        "status": registro.status,
        "token_valido": resultado is not None,
        "geo_resultado": geo_resultado,
        "endereco_aluno": endereco_aluno,
        "registro": registro,
        "etapa_rosto": _liberar_etapa_do_rosto(request, registro, results_pack),
    }
    return render(request, "checkin/checkin_aluno.html", contexto)


def _liberar_etapa_do_rosto(request, registro, results_pack) -> str:
    maquina_id = results_pack.get("maquina_id")
    passou_qr_e_local = results_pack.get("qr_code") and results_pack.get("geo_valida")
    if registro.status != "PENDING" or not passou_qr_e_local or not maquina_id:
        return ""
    if not Machine.objects.filter(pk=maquina_id).exists():
        return ""

    if Biometria.objects.filter(usuario=request.user).exists():
        _liberar_camera(maquina_id, registro, results_pack, MODE_CHECKIN)
        return "comparar"

    if BiometricService().get_active_consent(request.user):
        _liberar_camera(maquina_id, registro, results_pack, MODE_ENROLLMENT)
        return "cadastrar"

    # guarda o check-in na sessão do navegador até o aluno responder ao termo
    request.session["checkin_aguardando_termo"] = {
        "presenca_id": registro.id,
        "maquina_id": maquina_id,
        "results_pack": results_pack,
    }
    return "consentimento"


def _liberar_camera(maquina_id, registro, results_pack, modo):
    FaceAuthorizationService(cache).authorize(
        maquina_id,
        FaceAuthorization(
            presenca_id=registro.id,
            aluno_id=registro.usuario_id,
            mode=modo,
            base_pack=results_pack,
        ),
    )


@login_required
@only_student
@require_POST
def consentimento_biometrico(request):
    pendente = request.session.pop("checkin_aguardando_termo", None)
    if not pendente:
        return redirect("checkin:qr_demo")

    registro = PresencaRecord.objects.filter(pk=pendente["presenca_id"], usuario=request.user).first()
    if registro is None:
        return redirect("checkin:qr_demo")

    contexto = {"enviado": True, "status": registro.status, "token_valido": True, "registro": registro}
    if request.POST.get("resposta") != "aceito":
        contexto["etapa_rosto"] = ""
        contexto["recusou_termo"] = True
        return render(request, "checkin/checkin_aluno.html", contexto)

    try:
        BiometricService().grant_consent(
            request.user,
            evidence={
                "ip": request.META.get("REMOTE_ADDR"),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:255],
                "origem": "primeiro check-in",
            },
        )
    except BiometricTermUnavailableError:
        contexto["etapa_rosto"] = ""
        return render(request, "checkin/checkin_aluno.html", contexto)

    _liberar_camera(pendente["maquina_id"], registro, pendente["results_pack"], MODE_ENROLLMENT)
    contexto["etapa_rosto"] = "cadastrar"
    return render(request, "checkin/checkin_aluno.html", contexto)


@login_required
@only_student
def status_presenca(request, presenca_id: int):
    registro = get_object_or_404(PresencaRecord, pk=presenca_id, usuario=request.user)
    return JsonResponse({
        "status": registro.status,
        "motivo": registro.motivo,
        "aguardando_rosto": FaceAuthorizationService(cache).is_waiting(registro.id),
    })


@login_required
@only_student
def minhas_presencas(request):
    registros = (
        PresencaRecord.objects.filter(usuario=request.user)
        .select_related("sessao__aula__disciplina", "sessao__sala")
        .order_by("-data_criacao")
    )
    totais = {
        "aprovados": registros.filter(status="APPROVED").count(),
        "pendentes": registros.filter(status="PENDING").count(),
        "rejeitados": registros.filter(status="REJECTED").count(),
    }
    return render(request, "checkin/minhas_presencas.html", {"registros": registros, "totais": totais})


# Endpoint de pooling para o Pyside6
def status_sessao_sala(request, sala_id: int):
    service = ChamadaService()
    sessao = service.sessao_aberta_da_sala(sala_id)

    if not sessao:
        return JsonResponse({
            "ativa": False,
            "mensagem": "Nenhuma chamada em andamento para esta sala.",
        })

    disciplina_nome = sessao.aula.disciplina.nome if sessao.aula else "Chamada Manual"

    return JsonResponse({
        "ativa": True,
        "sessao_id": sessao.id,
        "sequencia": sessao.sequencia,
        "disciplina": disciplina_nome,
        "abre_em": sessao.abre_em.isoformat(),
        "fecha_em": sessao.fecha_em.isoformat(),
    })


def _registrar_checkin(request, svc):
    geo_resultado = None
    endereco_aluno = None
    token = request.POST.get("token", "")
    resultado = svc.consumir(token)

    # hash para auditoria
    qr_token_hash = hashlib.sha256(token.encode()).hexdigest() if token else ""

    aluno_id = request.user.id

    sessao_id = resultado.sessao_id if resultado else None
    maquina_id = resultado.maquina_id if resultado else None

    sessao_obj = (
        ChamadaSession.objects.select_related("sala").filter(pk=sessao_id).first()
        if sessao_id
        else None
    )
    sessao_valida = ChamadaService().esta_aberta(sessao_obj) if sessao_obj else False

    lat_raw = request.POST.get("lat", "")
    lon_raw = request.POST.get("lon", "")
    campus_id = (
        sessao_obj.sala.campus_id if (sessao_obj and sessao_obj.sala_id) else 1
    )

    geo_valida = False
    geo_motivo = "Localização não fornecida pelo aluno"

    if lat_raw and lon_raw:
        try:
            lat = float(lat_raw)
            lon = float(lon_raw)
            geo_svc = GeolocationService()
            geo_resultado = geo_svc.validate(lat, lon, campus_id)
            endereco_decoding = GeocodingService()
            endereco_aluno = endereco_decoding.translate_location(lat_raw, lon_raw)
            geo_valida = geo_resultado.valida
            geo_motivo = geo_resultado.motivo
        except (ValueError, Campus.DoesNotExist):
            geo_motivo = "Coordenada inválida ou campus não encontrado"

    # informações que serão úteis no PresencaRecord
    results_pack = {
        "qr_code": (resultado is not None) and sessao_valida,
        "qr_token_hash": qr_token_hash,
        "sessao_id": sessao_id,
        "maquina_id": maquina_id,
        "aluno_id": aluno_id,
        "geo_valida": geo_valida,
        "geo_motivo": geo_motivo,
    }

    registro = register_checkin(results_pack=results_pack)
    return resultado, geo_resultado, endereco_aluno, registro, results_pack

