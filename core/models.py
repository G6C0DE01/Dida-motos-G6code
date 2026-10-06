from django.conf import settings
from django.db import models


class PerfilUsuario(models.Model):
    """
    Dados extras do usuário que o model padrão do Django não guarda.
    Por enquanto só controla se a pessoa ainda está usando a senha
    temporária gerada no cadastro (ver core.utils.gerar_senha_temporaria
    e core.views.funcionario_form) — enquanto True, o
    ForcarTrocaSenhaMiddleware bloqueia o resto do sistema até a senha
    ser trocada.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil"
    )
    deve_trocar_senha = models.BooleanField("Deve trocar a senha no próximo login", default=False)

    class Meta:
        verbose_name = "Perfil do usuário"
        verbose_name_plural = "Perfis de usuário"

    def __str__(self):
        return f"Perfil de {self.user.username}"
