from django.urls import path
from . import views

app_name = "relatorios"

urlpatterns = [
    path("estoque-por-categoria/", views.estoque_por_categoria, name="estoque_por_categoria"),
    path("pecas-em-falta/", views.pecas_em_falta, name="pecas_em_falta"),
    path("pecas-paradas/", views.pecas_paradas, name="pecas_paradas"),
    path("custo-total-estoque/", views.custo_total_estoque, name="custo_total_estoque"),
    path("rotatividade/", views.rotatividade_pecas, name="rotatividade"),
    path("previsao-falta/", views.previsao_falta, name="previsao_falta"),
]
