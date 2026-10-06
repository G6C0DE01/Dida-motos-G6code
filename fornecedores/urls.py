from django.urls import path
from . import views

app_name = "fornecedores"

urlpatterns = [
    path("", views.fornecedor_list, name="list"),
    path("novo/", views.fornecedor_form, name="novo"),
    path("<int:pk>/editar/", views.fornecedor_form, name="editar"),
    path("<int:fornecedor_id>/historico/novo/", views.historico_novo, name="historico_novo"),
]
