from django.shortcuts import render
from .models import PresencaRecord

# Create your views here.

def painel(request):
    registers = PresencaRecord.objects.all().order_by("-data_criacao")
    return render(request, 'validator/painel.html', {"registers": registers})