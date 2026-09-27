from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Usuario
from .domain.cipher import Cipher
from .domain.totp_auth import TotpAuth
import qrcode
import io
import base64
from django.contrib.auth import login

def csrf_failure(request, reason=""):
    messages.error(request, "Sua sessão expirou. Tente novamente.")
    return redirect("accounts:login")

def setup_totp(request):
    user_id = request.session.get("setup_2fa_user_id")

    if not user_id:
        return redirect("accounts:login")

    user = Usuario.objects.get(id=user_id)

    totp_auth = TotpAuth(cipher=Cipher())

    if not user.totp_cifrado:
        totp_auth.create_secret(user)
        user.save(update_fields=["totp_cifrado"])

    if request.method == "POST":
        code = request.POST.get("code")

        if totp_auth.verify_code(user, code):
            user.totp_ativo = True
            user.save(update_fields=["totp_ativo"])
            del request.session["setup_2fa_user_id"]
            login(request, user)
            return redirect("validator:painel")
        
        messages.error(request, "Código inválido. Tente novamente.")

    uri = totp_auth.create_uri(user)

    qr_img = qrcode.make(uri)
    buffer = io.BytesIO()
    qr_img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return render(request, "accounts/setup_totp.html", {"qr_base64": qr_base64})