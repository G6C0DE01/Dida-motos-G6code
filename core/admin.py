from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User


@admin.action(description="Ativar acesso dos selecionados")
def ativar_acesso(modeladmin, request, queryset):
    atualizados = queryset.update(is_active=True)
    modeladmin.message_user(request, f"{atualizados} usuário(s) com acesso ativado.")


@admin.action(description="Revogar acesso dos selecionados")
def revogar_acesso(modeladmin, request, queryset):
    atualizados = queryset.update(is_active=False)
    modeladmin.message_user(request, f"{atualizados} usuário(s) com acesso revogado.")


class UserAdmin(BaseUserAdmin):
    """
    Admin de usuário customizado. O cadastro normal de funcionário é
    feito pela tela do próprio sistema (core:funcionario_novo, restrita
    a gerentes) — este admin do Django fica como acesso de apoio/backup
    (ex.: para um superusuário ativar/desativar acesso em massa).
    """
    list_display = (
        "username", "first_name", "is_active", "is_staff", "date_joined",
    )
    list_filter = BaseUserAdmin.list_filter + ("is_active",)
    actions = [ativar_acesso, revogar_acesso]


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
