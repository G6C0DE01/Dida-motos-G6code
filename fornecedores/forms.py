from django import forms
from .models import Fornecedor, HistoricoCompra


class FornecedorForm(forms.ModelForm):
    class Meta:
        model = Fornecedor
        fields = [
            "nome", "contato_nome", "telefone", "email",
            "localizacao", "prazo_entrega_dias",
        ]


class HistoricoCompraForm(forms.ModelForm):
    class Meta:
        model = HistoricoCompra
        fields = ["peca", "tipo", "quantidade", "preco_unitario"]
