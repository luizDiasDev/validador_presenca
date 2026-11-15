from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect


class SessaoUnicaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if (
            user.is_authenticated
            and user.chave_sessao_ativa
            and user.chave_sessao_ativa != request.session.session_key
        ):
            logout(request)
            messages.warning(request, "Sua conta foi acessada em outro aparelho. Entre novamente.")
            return redirect("accounts:login")
        return self.get_response(request)
