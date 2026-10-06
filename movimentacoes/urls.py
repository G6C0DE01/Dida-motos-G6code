from django.urls import path
from . import views

app_name = "movimentacoes"

urlpatterns = [
    path("", views.movimentacao_list, name="list"),
    path("nova/", views.movimentacao_form, name="nova"),
    path("<int:pk>/editar/", views.movimentacao_form, name="editar"),
    path("<int:pk>/excluir/", views.movimentacao_excluir, name="excluir"),
]
