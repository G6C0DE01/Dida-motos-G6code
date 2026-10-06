from django.contrib import admin
from .models import Categoria, Localizacao, Fabricante, ModeloMoto, Peca


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome", "descricao")
    search_fields = ("nome",)


@admin.register(Localizacao)
class LocalizacaoAdmin(admin.ModelAdmin):
    list_display = ("__str__", "setor", "prateleira", "caixa")
    search_fields = ("setor", "prateleira", "caixa")


@admin.register(Fabricante)
class FabricanteAdmin(admin.ModelAdmin):
    list_display = ("nome",)
    search_fields = ("nome",)


@admin.register(ModeloMoto)
class ModeloMotoAdmin(admin.ModelAdmin):
    list_display = ("marca", "modelo")
    search_fields = ("marca", "modelo")
    list_filter = ("marca",)


@admin.register(Peca)
class PecaAdmin(admin.ModelAdmin):
    list_display = (
        "codigo", "nome", "categoria", "fabricante",
        "quantidade_estoque", "quantidade_minima", "alerta_estoque",
        "preco_custo", "preco_venda", "ativo",
    )
    list_filter = ("categoria", "fabricante", "ativo")
    search_fields = ("codigo", "nome")
    filter_horizontal = ("modelos_compativeis",)
    autocomplete_fields = ("categoria", "fabricante", "localizacao")

    @admin.display(description="Estoque baixo", boolean=True)
    def alerta_estoque(self, obj):
        return obj.abaixo_do_minimo


admin.site.site_header = "Dida Motos - Gestão de Estoque"
admin.site.site_title = "Dida Motos"
admin.site.index_title = "Administração"
