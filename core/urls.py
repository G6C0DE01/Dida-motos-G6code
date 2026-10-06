from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from .forms import LoginForm

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path(
        "entrar/",
        auth_views.LoginView.as_view(
            template_name="core/login.html", authentication_form=LoginForm
        ),
        name="login",
    ),
    path(
        "sair/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
    path("senha/trocar/", views.trocar_senha, name="trocar_senha"),

    path("funcionarios/", views.funcionario_list, name="funcionario_list"),
    path("funcionarios/novo/", views.funcionario_form, name="funcionario_novo"),
    path(
        "funcionarios/<int:pk>/alternar-acesso/",
        views.funcionario_alternar_acesso, name="funcionario_alternar_acesso",
    ),

    # Esqueci minha senha: fluxo padrão do Django (4 telas), com os
    # templates estilizados como login.html.
    path(
        "senha/esqueci/",
        auth_views.PasswordResetView.as_view(
            template_name="core/password_reset_form.html",
            email_template_name="core/password_reset_email.txt",
            subject_template_name="core/password_reset_subject.txt",
            success_url=reverse_lazy("core:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "senha/esqueci/enviado/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="core/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "senha/redefinir/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="core/password_reset_confirm.html",
            success_url=reverse_lazy("core:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "senha/redefinida/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="core/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]
