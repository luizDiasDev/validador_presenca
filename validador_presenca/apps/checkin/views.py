import base64
import io
import qrcode
from django.core.cache import cache
from django.shortcuts import render
from apps.checkin.domain.services.qr_service import QrTokenService


def qr_demo(request):
    svc = QrTokenService(cache=cache)

    # Simula scan consome token
    resultado = None
    if request.method == "POST":
        token = request.POST.get("token", "")
        resultado = svc.consumir(token)

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
    }
    return render(request, "checkin/qr_demo.html", contexto)