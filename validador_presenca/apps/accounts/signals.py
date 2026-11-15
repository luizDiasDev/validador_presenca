from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


@receiver(user_logged_in)
def guardar_sessao_ativa(sender, request, user, **kwargs):
    if request is None:
        return
    user.chave_sessao_ativa = request.session.session_key
    user.save(update_fields=["chave_sessao_ativa"])
