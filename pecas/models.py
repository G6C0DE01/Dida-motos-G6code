from django.db import models
from django.core.validators import MinValueValidator


class Categoria(models.Model):
    """
    Categoria de peças (Motor, Transmissão, Suspensão, Freios, Pneus,
    Acessórios, Eletrônicos, Consumíveis, ...). Modelada como tabela
    (em vez de choices fixas) para o grupo poder criar novas categorias
    sem alterar código.
    """
    nome = models.CharField(max_length=50, unique=True)
    descricao = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Localizacao(models.Model):
    """Localização física da peça no estoque: Prateleira, Caixa, Setor."""
    prateleira = models.CharField(max_length=20, blank=True)
    caixa = models.CharField(max_length=20, blank=True)
    setor = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = "Localização"
        verbose_name_plural = "Localizações"
        unique_together = ("prateleira", "caixa", "setor")

    def __str__(self):
        partes = [p for p in [
            f"Setor {self.setor}" if self.setor else "",
            f"Prateleira {self.prateleira}" if self.prateleira else "",
            f"Caixa {self.caixa}" if self.caixa else "",
        ] if p]
        return " / ".join(partes) or f"Localização #{self.pk}"


class Fabricante(models.Model):
    """Marca/fabricante da peça (ex.: Honda, NGK, Pirelli, Motul)."""
    nome = models.CharField(max_length=80, unique=True)

    class Meta:
        verbose_name = "Fabricante"
        verbose_name_plural = "Fabricantes"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class ModeloMoto(models.Model):
    """Modelo de motocicleta compatível com a peça (ex.: Honda CG 160)."""
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)

    class Meta:
        verbose_name = "Modelo de moto"
        verbose_name_plural = "Modelos de moto"
        unique_together = ("marca", "modelo")
        ordering = ["marca", "modelo"]

    def __str__(self):
        return f"{self.marca} {self.modelo}"


class Peca(models.Model):
    """
    Cadastro de peça/componente (módulo A do escopo).
    quantidade_estoque é mantida como campo desnormalizado para leitura
    rápida no dashboard/relatórios, mas só deve ser alterada através do
    app `movimentacoes` (nunca editada diretamente fora dali), que grava
    o histórico de cada mudança.
    """
    codigo = models.CharField(
        "Código", max_length=30, unique=True,
        help_text="Código interno/SKU da peça."
    )
    nome = models.CharField("Nome", max_length=150)
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name="pecas"
    )
    fabricante = models.ForeignKey(
        Fabricante, on_delete=models.PROTECT, related_name="pecas",
        null=True, blank=True
    )
    modelos_compativeis = models.ManyToManyField(
        ModeloMoto, related_name="pecas_compativeis", blank=True,
        verbose_name="Modelos compatíveis"
    )

    quantidade_estoque = models.PositiveIntegerField("Quantidade em estoque", default=0)
    quantidade_minima = models.PositiveIntegerField(
        "Quantidade mínima", default=0,
        help_text="Quantidade mínima antes de disparar alerta de estoque baixo."
    )
    preco_custo = models.DecimalField("Preço de custo", max_digits=10, decimal_places=2, default=0)
    preco_venda = models.DecimalField("Preço de venda", max_digits=10, decimal_places=2, default=0)

    localizacao = models.ForeignKey(
        Localizacao, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="pecas", verbose_name="Localização"
    )

    lote = models.CharField("Lote/Série", max_length=50, blank=True)
    data_validade = models.DateField(null=True, blank=True)

    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Peça"
        verbose_name_plural = "Peças"
        ordering = ["nome"]
        indexes = [
            models.Index(fields=["codigo"]),
            models.Index(fields=["nome"]),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.nome}"

    @property
    def abaixo_do_minimo(self):
        return self.quantidade_estoque < self.quantidade_minima

    @property
    def valor_total_estoque(self):
        return self.quantidade_estoque * self.preco_custo
