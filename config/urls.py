from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("pecas/", include("pecas.urls")),
    path("movimentacoes/", include("movimentacoes.urls")),
    path("ordens-servico/", include("ordens_servico.urls")),
    path("fornecedores/", include("fornecedores.urls")),
    path("relatorios/", include("relatorios.urls")),
    path("", include("core.urls")),
]
