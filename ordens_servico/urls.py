from django.urls import path
from . import views

app_name = "ordens_servico"

urlpatterns = [
    path("", views.os_list, name="list"),
    path("nova/", views.os_form, name="nova"),
    path("<int:pk>/editar/", views.os_form, name="editar"),

    path("clientes/", views.cliente_list, name="cliente_list"),
    path("clientes/novo/", views.cliente_form, name="cliente_novo"),
    path("clientes/<int:pk>/editar/", views.cliente_form, name="cliente_editar"),
    path("clientes/buscar-cpf/", views.cliente_buscar_cpf, name="cliente_buscar_cpf"),

    path("motocicletas/nova/", views.motocicleta_form, name="motocicleta_novo"),
    path("motocicletas/<int:pk>/editar/", views.motocicleta_form, name="motocicleta_editar"),
]
