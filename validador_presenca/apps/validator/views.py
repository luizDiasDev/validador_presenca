from django.shortcuts import render

# Create your views here.

def painel(request):
    return render(request, 'validator/painel.html')