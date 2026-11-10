import base64
import hashlib
import io
import qrcode
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from apps.checkin.domain.services.chamada_service import ChamadaService
from apps.checkin.domain.services.qr_service import QrTokenService
from apps.checkin.models import ChamadaSession
from apps.validator.domain.case import try_checkin
from apps.institution.domain.services.geolocation_service import GeolocationService
from apps.institution.domain.services.geocoding_service import GeocodingService
from apps.institution.models import Campus, Machine
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from apps.accounts.decorators import only_student, only_teacher
from django.urls import reverse


@login_required
@only_student
def qr_demo(request):
    if request.method == "POST":
        svc = QrTokenService(cache=cache)
        resultado, geo_resultado, endereco_aluno, veredito = _registrar_checkin(request, svc)
        contexto = {
            "enviado": True,
            "status": veredito.value,
            "token_valido": resultado is not None,
            "geo_resultado": geo_resultado,
            "endereco_aluno": endereco_aluno,
        }
        return render(request, "checkin/checkin_aluno.html", contexto)

    return render(request, "checkin/checkin_aluno.html", {"token": request.GET.get("t", "")})


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
            geo_motivo = f"Coordenada inválida ou campus não encontrado"

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

    veredito = try_checkin(results_pack=results_pack)
    return resultado, geo_resultado, endereco_aluno, veredito


# Tempo mínimo de vida do QR exibido na sala: o aluno precisa apontar a câmera,
# abrir o link e o celular ainda precisa achar a localização antes de enviar.
QR_SALA_TTL_MINIMO_S = 30
QR_SALA_ATUALIZA_S = 10


@login_required
@only_teacher
def sala_qr(request):
    agora = timezone.now()
    sessao = (
        ChamadaSession.objects.select_related("sala", "aula__disciplina")
        .filter(professor=request.user.professor, abre_em__lte=agora, fecha_em__gt=agora)
        .order_by("-abre_em")
        .first()
    )
    contexto = {"sessao": sessao, "atualiza_s": QR_SALA_ATUALIZA_S, "maquina": None}

    if sessao:
        maquinas_da_sala = Machine.objects.filter(sala_id=sessao.sala_id).order_by("id")
        # com várias máquinas na sala, cada tela informa a sua: /checkin/sala/?maquina=3
        maquina_escolhida = request.GET.get("maquina", "")
        maquina = (
            maquinas_da_sala.filter(pk=maquina_escolhida).first()
            if maquina_escolhida.isdigit()
            else maquinas_da_sala.first()
        )
        contexto["maquina"] = maquina
        qr = QrTokenService(cache=cache).gerar(
            sessao_id=sessao.id,
            maquina_id=maquina.id if maquina else 0,
            ttl_s=max(sessao.duracao_qr_s, QR_SALA_TTL_MINIMO_S),
        )
        # o QR guarda um link: a câmera comum do celular já abre a página de leitura
        link_leitura = request.build_absolute_uri(f"{reverse('checkin:qr_demo')}?t={qr.token}")
        imagem = qrcode.make(link_leitura)
        buffer = io.BytesIO()
        imagem.save(buffer, format="PNG")
        contexto["qr_image"] = base64.b64encode(buffer.getvalue()).decode()

    return render(request, "checkin/sala_qr.html", contexto)