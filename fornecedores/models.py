from django.db import models
from pecas.models import Peca


class Fornecedor(models.Model):
    """Cadastro de fornecedor (módulo D do escopo)."""
    nome = models.CharField(max_length=150)
    contato_nome = models.CharField("Nome do contato", max_length=100, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    localizacao = models.CharField("Localização", max_length=150, blank=True)
    prazo_entrega_dias = models.PositiveIntegerField(
        "Prazo de entrega (dias)", null=True, blank=True
    )

    class Meta:
        verbose_name = "Fornecedor"
        verbose_name_plural = "Fornecedores"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class HistoricoCompra(models.Model):
    """Histórico de compras e cotações de preço junto a um fornecedor."""

    class Tipo(models.TextChoices):
        COMPRA = "compra", "Compra realizada"
        COTACAO = "cotacao", "Cotação"

    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.CASCADE, related_name="historico")
    peca = models.ForeignKey(
        Peca, on_delete=models.CASCADE, related_name="historico_compras", verbose_name="Peça"
    )
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.COMPRA)
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField("Preço unitário", max_digits=10, decimal_places=2)
    data = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Histórico de compra/cotação"
        verbose_name_plural = "Histórico de compras/cotações"
        ordering = ["-data"]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.peca.nome} ({self.fornecedor.nome})"
