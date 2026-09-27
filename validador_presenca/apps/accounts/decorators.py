from functools import wraps
from django.shortcuts import redirect


def only_teacher(view_func):
    #encapsula a função para se tornar um decorador
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        #verifica se o atibuto existe no usuario
        if not hasattr(request.user, "professor"):
            return redirect("accounts:login")
        return view_func(request, *args, **kwargs)
    return wrapper


def only_admin(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, "administrador"):
            return redirect("accounts:login")
        return view_func(request, *args, **kwargs)
    return wrapper