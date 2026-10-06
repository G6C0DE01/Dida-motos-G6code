from django import forms
from .models import Peca, Categoria, Fabricante, ModeloMoto, Localizacao


class PecaForm(forms.ModelForm):
    class Meta:
        model = Peca
        fields = [
            "codigo", "nome", "categoria", "fabricante", "modelos_compativeis",
            "quantidade_estoque", "quantidade_minima",
            "preco_custo", "preco_venda",
            "localizacao", "lote", "data_validade", "ativo",
        ]
        widgets = {
            "modelos_compativeis": forms.SelectMultiple(attrs={"size": 6}),
            "data_validade": forms.DateInput(attrs={"type": "date"}),
        }
        help_texts = {
            "quantidade_estoque": "Só edite aqui na criação da peça ou em correções pontuais. "
                                   "Para o dia a dia, use Movimentações (entrada/saída/ajuste).",
        }


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nome", "descricao"]


class FabricanteForm(forms.ModelForm):
    class Meta:
        model = Fabricante
        fields = ["nome"]


class ModeloMotoForm(forms.ModelForm):
    class Meta:
        model = ModeloMoto
        fields = ["marca", "modelo"]


class LocalizacaoForm(forms.ModelForm):
    class Meta:
        model = Localizacao
        fields = ["setor", "prateleira", "caixa"]
