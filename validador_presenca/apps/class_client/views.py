import json
from functools import wraps

from django.core.cache import cache
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from apps.checkin.domain.services.chamada_service import ChamadaService
from apps.checkin.domain.services.qr_service import QrTokenService
from apps.institution.domain.services.pairing_service import MachinePairingService

from .domain.services.face_authorization_service import FaceAuthorizationService
from .domain.services.face_checkin_service import FaceCheckinError, FaceCheckinService

QR_TTL_MINIMUM_SECONDS = 30
QR_REFRESH_SECONDS = 10


def machine_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        header = request.headers.get("Authorization", "")
        token = header.removeprefix("Bearer ").strip() if header.startswith("Bearer ") else ""
        machine = MachinePairingService().autenticar(token)
        if machine is None:
            return JsonResponse({"erro": "Máquina não pareada ou token inválido."}, status=401)
        request.machine = machine
        return view_func(request, *args, **kwargs)
    return wrapper


@require_GET
@machine_required
def current_qr(request):
    session = ChamadaService().sessao_aberta_da_sala(request.machine.sala_id)
    if session is None:
        return JsonResponse({"ativa": False, "mensagem": "Nenhuma chamada aberta nesta sala."})

    qr = QrTokenService(cache=cache).gerar(
        sessao_id=session.id,
        maquina_id=request.machine.id,
        ttl_s=max(session.duracao_qr_s, QR_TTL_MINIMUM_SECONDS),
    )
    return JsonResponse({
        "ativa": True,
        "link": request.build_absolute_uri(f"{reverse('checkin:qr_demo')}?t={qr.token}"),
        "atualizar_em_s": QR_REFRESH_SECONDS,
        "disciplina": session.aula.disciplina.nome if session.aula else "Chamada",
        "fecha_em": timezone.localtime(session.fecha_em).strftime("%H:%M"),
    })


@require_GET
@machine_required
def pending_authorization(request):
    pending = FaceAuthorizationService(cache).pending_for(request.machine.id)
    if pending is None:
        return JsonResponse({"pendente": False})
    return JsonResponse({"pendente": True, "presenca_id": pending.presenca_id, "modo": pending.mode})


@csrf_exempt
@require_POST
@machine_required
def submit_face(request):
    try:
        body = json.loads(request.body.decode("utf-8"))
        presenca_id = int(body["presenca_id"])
        face_payload = body["payload"]
    except (ValueError, KeyError, TypeError):
        return JsonResponse({"erro": "Envio inválido."}, status=400)

    authorization = FaceAuthorizationService(cache).consume(request.machine.id, presenca_id)
    if authorization is None:
        return JsonResponse({"erro": "Nenhum check-in aguardando rosto nesta máquina."}, status=409)

    try:
        record = FaceCheckinService().complete(authorization, face_payload)
    except FaceCheckinError as error:
        return JsonResponse({"status": "PENDING", "mensagem": str(error)}, status=422)

    return JsonResponse({"status": record.status, "mensagem": _message_for(record.status)})


def _message_for(status: str) -> str:
    return {
        "APPROVED": "Presença confirmada.",
        "PENDING": "Presença registrada. O professor vai confirmar.",
        "REJECTED": "Check-in não aceito.",
    }.get(status, "")
