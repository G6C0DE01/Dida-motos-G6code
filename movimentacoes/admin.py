from django.contrib import admin
from .models import Movimentacao


@admin.register(Movimentacao)
class MovimentacaoAdmin(admin.ModelAdmin):
    list_display = (
        "data", "peca", "tipo", "motivo", "quantidade",
        "direcao_ajuste", "usuario", "ordem_servico",
    )
    list_filter = ("tipo", "motivo", "data")
    search_fields = ("peca__codigo", "peca__nome", "usuario__username")
    autocomplete_fields = ("peca", "ordem_servico")
    readonly_fields = ("data",)

    def save_model(self, request, obj, form, change):
        if not change and not obj.usuario_id:
            obj.usuario = request.user
        obj.full_clean()
        super().save_model(request, obj, form, change)
