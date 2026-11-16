from django.core.paginator import Paginator

ITENS_POR_PAGINA = 20


def paginar(request, itens, por_pagina: int = ITENS_POR_PAGINA):
    return Paginator(itens, por_pagina).get_page(request.GET.get("pagina"))
