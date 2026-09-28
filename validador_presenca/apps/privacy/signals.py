from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from apps.privacy.models import Termo, AceiteTermo


@receiver(user_logged_in)
def registrar_aceite_no_login(sender, request, user, **kwargs):
    if not request:
        return

    # só registra se o form de login validou a checkbox (sinalizado pela session)
    if not request.session.get("aceite_termos_dado"):
        return

    for termo in Termo.objects.filter(ativo=True):
        ja_aceitou = AceiteTermo.objects.filter(
            usuario=user,
            termo=termo,
            concedido=True,
        ).exists()

        if ja_aceitou:
            continue

        AceiteTermo.objects.create(
            usuario=user,
            termo=termo,
            concedido=True,
            evidencia={
                "ip": request.META.get("REMOTE_ADDR", ""),
                "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                "contexto": "login_form",
            },
        )

    # limpa a flag após login para evitar novo registro em logins seguintes
    request.session.pop("aceite_termos_dado", None)