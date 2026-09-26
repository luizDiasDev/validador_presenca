from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import Usuario, Administrador, Professor

admin.site.register(Usuario)
admin.site.register(Administrador)
admin.site.register(Professor)