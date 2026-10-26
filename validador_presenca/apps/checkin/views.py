import base64
import hashlib
import io
import qrcode
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from apps.checkin.domain.services.chamada_service import ChamadaService
from apps.checkin.domain.services.qr_service import QrTokenService
from apps.validator.domain.case import try_checkin
from apps.institution.domain.services.geolocation_service import GeolocationService
from apps.institution.domain.services.geocoding_service import GeocodingService
from apps.institution.models import Campus
from django.contrib.auth.decorators import login_required


@login_required
def qr_demo(request):
    svc = QrTokenService(cache=cache)

    # Simula scan consome token
    resultado = None
    geo_resultado = None
    endereco_aluno = None
    if request.method == "POST":
        token = request.POST.get("token", "")
        resultado = svc.consumir(token)

        # hash para auditoria
        qr_token_hash = hashlib.sha256(token.encode()).hexdigest() if token else ""

        # dado chumbado, virá depois quando o PWA for desenvolvido
        aluno_id = request.user.id

        sessao_id = resultado.sessao_id if resultado else None
        maquina_id = resultado.maquina_id if resultado else None

        lat_raw = request.POST.get("lat", "")
        lon_raw = request.POST.get("lon", "")
        campus_id = 1 # vai ser dinâmico depois quando vier da sessão

        geo_valida = False
        geo_motivo = "Localização não fornecida pelo aluno"
    
        if lat_raw and lon_raw:
            try:
                lat = float(lat_raw)
                lon = float(lon_raw)
                geo_svc = GeolocationService()
                geo_resultado = geo_svc.validate(lat, lon, campus_id)
                endereco_decoding = GeocodingService()
                endereco_aluno = endereco_decoding.translate_location(lat_raw,lon_raw)
                geo_valida = geo_resultado.valida
                geo_motivo = geo_resultado.motivo
            except (ValueError, Campus.DoesNotExist):
                geo_motivo = f"Coordenada inválida ou campus não encontrado"

        # informações que serão úteis no PresencaRecord
        results_pack = {
            "qr_code": resultado is not None,
            "qr_token_hash": qr_token_hash,
            "sessao_id": sessao_id,
            "maquina_id": maquina_id,
            "aluno_id": aluno_id,
            "geo_valida": geo_valida,
            "geo_motivo": geo_motivo,
        }

        try_checkin(results_pack=results_pack)
        

    # Gera novo QR
    sessao_id = int(request.GET.get("sessao", 1))
    maquina_id = int(request.GET.get("maquina", 1))
    qr = svc.gerar(sessao_id=sessao_id, maquina_id=maquina_id)

    # Renderiza QR
    img = qrcode.make(qr.token)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_image_b64 = base64.b64encode(buffer.getvalue()).decode()

    contexto = {
        "token": qr.token,
        "sessao_id": qr.sessao_id,
        "maquina_id": qr.maquina_id,
        "ttl_s": qr.ttl_s,
        "qr_image": qr_image_b64,
        "resultado": resultado,
        "geo_resultado": geo_resultado,
        "endereco_aluno": endereco_aluno,
    }
    return render(request, "checkin/qr_demo.html", contexto)

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