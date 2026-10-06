from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class ForcarTrocaSenhaMiddleware:
    """
    Enquanto o usuário logado tiver perfil.deve_trocar_senha=True (conta
    criada pelo admin em core.views.funcionario_form, com senha
    temporária), bloqueia qualquer página do sistema e redireciona para
    a troca de senha — evita que alguém continue usando a senha padrão
    gerada no cadastro.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            perfil = getattr(user, "perfil", None)
            if perfil and perfil.deve_trocar_senha:
                liberadas = {reverse("core:trocar_senha"), reverse("core:logout")}
                # STATIC_URL pode vir sem barra inicial (ex.: "static/"), mas
                # request.path sempre começa com "/" — normaliza os dois
                # antes de comparar, senão a exceção de arquivo estático
                # nunca bate e o CSS/JS da própria tela de troca quebra.
                static_prefix = "/" + settings.STATIC_URL.lstrip("/")
                if request.path not in liberadas and not request.path.startswith(static_prefix):
                    return redirect("core:trocar_senha")
        return self.get_response(request)
