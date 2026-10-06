from django.urls import path
from . import views

app_name = "pecas"

urlpatterns = [
    path("", views.peca_list, name="list"),
    path("nova/", views.peca_form, name="novo"),
    path("<int:pk>/editar/", views.peca_form, name="editar"),
    path("<int:pk>/toggle-ativo/", views.peca_toggle_ativo, name="toggle_ativo"),

    path("categorias/", views.categoria_list, name="categoria_list"),
    path("categorias/nova/", views.categoria_form, name="categoria_novo"),
    path("categorias/<int:pk>/editar/", views.categoria_form, name="categoria_editar"),

    path("fabricantes/", views.fabricante_list, name="fabricante_list"),
    path("fabricantes/novo/", views.fabricante_form, name="fabricante_novo"),
    path("fabricantes/<int:pk>/editar/", views.fabricante_form, name="fabricante_editar"),

    path("modelos/", views.modelo_moto_list, name="modelo_list"),
    path("modelos/novo/", views.modelo_moto_form, name="modelo_novo"),
    path("modelos/<int:pk>/editar/", views.modelo_moto_form, name="modelo_editar"),

    path("localizacoes/", views.localizacao_list, name="localizacao_list"),
    path("localizacoes/nova/", views.localizacao_form, name="localizacao_novo"),
    path("localizacoes/<int:pk>/editar/", views.localizacao_form, name="localizacao_editar"),
]
