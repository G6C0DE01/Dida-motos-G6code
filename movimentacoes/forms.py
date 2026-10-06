from django import forms
from .models import Movimentacao


class MovimentacaoForm(forms.ModelForm):
    class Meta:
        model = Movimentacao
        fields = [
            "peca", "tipo", "motivo", "quantidade",
            "direcao_ajuste", "observacao", "ordem_servico",
        ]
        widgets = {
            "observacao": forms.Textarea(attrs={"rows": 2}),
            "peca": forms.Select(attrs={"class": "searchable", "data-placeholder": "Buscar peça..."}),
        }
