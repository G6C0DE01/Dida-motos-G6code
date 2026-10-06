from django.contrib import admin
from .models import Fornecedor, HistoricoCompra


class HistoricoCompraInline(admin.TabularInline):
    model = HistoricoCompra
    extra = 0
    autocomplete_fields = ("peca",)
    readonly_fields = ("data",)


@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ("nome", "contato_nome", "telefone", "email", "prazo_entrega_dias")
    search_fields = ("nome", "contato_nome", "email")
    inlines = [HistoricoCompraInline]


@admin.register(HistoricoCompra)
class HistoricoCompraAdmin(admin.ModelAdmin):
    list_display = ("data", "fornecedor", "peca", "tipo", "quantidade", "preco_unitario")
    list_filter = ("tipo", "fornecedor")
    search_fields = ("peca__nome", "peca__codigo", "fornecedor__nome")
    autocomplete_fields = ("fornecedor", "peca")
