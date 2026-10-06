from django.contrib import admin
from .models import Cliente, Motocicleta, OrdemServico, ItemOrdemServico


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "telefone", "email")
    search_fields = ("nome", "telefone", "email")


@admin.register(Motocicleta)
class MotocicletaAdmin(admin.ModelAdmin):
    list_display = ("__str__", "cliente", "marca", "modelo", "ano", "placa")
    search_fields = ("marca", "modelo", "placa", "cliente__nome")
    autocomplete_fields = ("cliente",)


class ItemOrdemServicoInline(admin.TabularInline):
    model = ItemOrdemServico
    extra = 1
    autocomplete_fields = ("peca",)


@admin.register(OrdemServico)
class OrdemServicoAdmin(admin.ModelAdmin):
    list_display = (
        "numero", "cliente", "motocicleta", "status",
        "mecanico", "data_abertura", "alerta_peca_em_falta",
    )
    list_filter = ("status", "data_abertura")
    search_fields = ("numero", "cliente__nome", "motocicleta__placa")
    autocomplete_fields = ("cliente", "motocicleta", "mecanico")
    inlines = [ItemOrdemServicoInline]
    readonly_fields = ("numero", "data_abertura")

    @admin.display(description="Peça em falta", boolean=True)
    def alerta_peca_em_falta(self, obj):
        return obj.peca_em_falta
