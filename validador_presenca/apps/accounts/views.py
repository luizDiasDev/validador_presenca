from django.shortcuts import render

# Create your views here.

from django.contrib import messages
from django.shortcuts import redirect


def csrf_failure(request, reason=""):
    messages.error(request, "Sua sessão expirou. Tente novamente.")
    return redirect("accounts:login")