from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Usuario
from .domain.cipher import Cipher
from .domain.totp_auth import TotpAuth
import qrcode
import io
import base64
from django.contrib.auth import login
from django.contrib.auth.views import LoginView

class AdsumLoginView(LoginView):
    template_name = "accounts/login.html"

    def form_valid(self, form):
        user = form.get_user()

        if not user.totp_ativo:
            self.request.session["config_2fa_user"] = user.id
            return redirect("accounts:config_totp")

        self.request.session["read_2fa_user"] = user.id
        return redirect("accounts:read_totp")


def csrf_failure(request, reason=""):
    messages.error(request, "Sua sessão expirou. Tente novamente.")
    return redirect("accounts:login")

def config_totp(request):
    user_id = request.session.get("config_2fa_user")

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
            del request.session["config_2fa_user"]
            login(request, user)
            return redirect("validator:painel")
        
        messages.error(request, "Código inválido. Tente novamente.")

    uri = totp_auth.create_uri(user)

    qr_img = qrcode.make(uri)
    buffer = io.BytesIO()
    qr_img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return render(request, "accounts/config_totp.html", {"qr_base64": qr_base64})

def read_totp(request):
    user_id = request.session.get("read_2fa_user")

    if not user_id:
        return redirect("accounts:login")

    user = Usuario.objects.get(id=user_id)

    totp_auth  = TotpAuth(cipher=Cipher())

    if request.method == "POST":
        code = request.POST.get("code")

        if totp_auth.verify_code(user, code):
            del request.session["read_2fa_user"]
            login(request, user)
            return redirect("validator:painel")
        
        messages.error(request, "Código incorreto.")

    return render(request, "accounts/read_totp.html")