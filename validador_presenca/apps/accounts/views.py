from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Usuario
from .domain.cipher import Cipher
from .domain.totp_auth import TotpAuth
import qrcode
import io
import base64
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from apps.audit.domain.log_register import LogRegister
from apps.privacy.domain.term_acceptance import registrar_aceite, termos_pendentes
from django.conf import settings

class AdsumLoginView(LoginView):
    template_name = "accounts/login.html"

    def form_valid(self, form):
        user = form.get_user()

        if user.totp_ativo:
            self.request.session["read_2fa_user"] = user.id
            proximo_passo = "accounts:read_totp"
        else:
            self.request.session["config_2fa_user"] = user.id
            proximo_passo = "accounts:config_totp"

        if termos_pendentes(user):
            self.request.session["termos_user"] = user.id
            self.request.session["apos_termos"] = proximo_passo
            return redirect("accounts:aceitar_termos")

        return redirect(proximo_passo)

    def form_invalid(self, form):
        LogRegister().register({
            "autor_id": 0,
            "origem": "accounts",
            "acao": "LOGIN_FALHA",
            "tabela": "usuario",
            "linha_tabela_id": 0,
            "payload": {"email_tentado": self.request.POST.get("username", "")},
        })
        return super().form_invalid(form)

class AdsumLogoutView(LogoutView):
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            LogRegister().register({
                "autor_id": request.user.id,
                "origem": "accounts",
                "acao": "LOGOUT",
                "tabela": "usuario",
                "linha_tabela_id": request.user.id,
                "payload": {},
            })
        return super().post(request, *args, **kwargs)

def csrf_failure(request, reason=""):
    messages.error(request, "Sua sessão expirou. Tente novamente.")
    return redirect("accounts:login")

def aceitar_termos(request):
    user_id = request.session.get("termos_user")

    if not user_id:
        return redirect("accounts:login")

    user = Usuario.objects.get(id=user_id)
    termos = termos_pendentes(user)

    if request.method == "POST":
        if request.POST.get("aceite") == "sim":
            registrar_aceite(
                user,
                termos,
                evidencia={
                    "ip": request.META.get("REMOTE_ADDR", ""),
                    "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                    "contexto": "login",
                },
            )
            del request.session["termos_user"]
            return redirect(request.session.pop("apos_termos", "accounts:login"))

        messages.error(request, "Você precisa aceitar os documentos para continuar.")

    return render(request, "accounts/aceitar_termos.html", {"termos": termos})


def config_totp(request):
    if request.session.get("termos_user"):
        return redirect("accounts:aceitar_termos")

    user_id = request.session.get("config_2fa_user")

    if not user_id:
        return redirect("accounts:login")

    user = Usuario.objects.get(id=user_id)

    totp_auth = TotpAuth(cipher=Cipher(settings.TOTP_ENCRYPTION_KEY))

    if not user.totp_cifrado:
        totp_auth.create_secret(user)
        user.save(update_fields=["totp_cifrado"])

    if request.method == "POST":
        code = request.POST.get("code")

        if totp_auth.verify_code(user, code):
            user.totp_ativo = True
            user.save(update_fields=["totp_ativo"])
            del request.session["config_2fa_user"]

            LogRegister().register({
                "autor_id": user.id,
                "origem": "accounts",
                "acao": "TOTP_CONFIGURADO",
                "tabela": "usuario",
                "linha_tabela_id": user.id,
                "payload": {},
            })

            login(request, user)
            return redirect(settings.LOGIN_REDIRECT_URL)

        LogRegister().register({
            "autor_id": user.id,
            "origem": "accounts",
            "acao": "TOTP_CONFIG_FALHA",
            "tabela": "usuario",
            "linha_tabela_id": user.id,
            "payload": {},
        })
        
        messages.error(request, "Código inválido. Tente novamente.")

    uri = totp_auth.create_uri(user)

    qr_img = qrcode.make(uri)
    buffer = io.BytesIO()
    qr_img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return render(request, "accounts/config_totp.html", {"qr_base64": qr_base64})

def read_totp(request):
    if request.session.get("termos_user"):
        return redirect("accounts:aceitar_termos")

    user_id = request.session.get("read_2fa_user")

    if not user_id:
        return redirect("accounts:login")

    user = Usuario.objects.get(id=user_id)

    totp_auth  = TotpAuth(cipher=Cipher(settings.TOTP_ENCRYPTION_KEY))

    if request.method == "POST":
        code = request.POST.get("code")

        if totp_auth.verify_code(user, code):
            del request.session["read_2fa_user"]

            LogRegister().register({
                "autor_id": user.id,
                "origem": "accounts",
                "acao": "LOGIN_SUCESSO",
                "tabela": "usuario",
                "linha_tabela_id": user.id,
                "payload": {},
            })

            login(request, user)
            return redirect(settings.LOGIN_REDIRECT_URL)

        LogRegister().register({
            "autor_id": user.id,
            "origem": "accounts",
            "acao": "TOTP_FALHA",
            "tabela": "usuario",
            "linha_tabela_id": user.id,
            "payload": {},
        })
        
        messages.error(request, "Código incorreto.")

    return render(request, "accounts/read_totp.html")