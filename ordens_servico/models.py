from django.conf import settings
from django.db import models, transaction

from pecas.models import Peca

from .validators import validar_cpf


class Cliente(models.Model):
    nome = models.CharField(max_length=150)
    cpf = models.CharField(
        "CPF", max_length=11, unique=True, null=True, blank=True,
        validators=[validar_cpf],
        help_text="Só números. Usado para localizar um cliente já cadastrado ao registrar um veículo novo.",
    )
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Motocicleta(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="motocicletas")
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    ano = models.PositiveIntegerField(null=True, blank=True)
    placa = models.CharField(max_length=10, blank=True)

    class Meta:
        verbose_name = "Motocicleta"
        verbose_name_plural = "Motocicletas"
        ordering = ["cliente__nome"]

    def __str__(self):
        ano = f" {self.ano}" if self.ano else ""
        return f"{self.marca} {self.modelo}{ano} - {self.cliente.nome}"


class OrdemServico(models.Model):
    """Ordem de reparo/serviço (módulo C do escopo)."""

    class Status(models.TextChoices):
        ABERTA = "aberta", "Aberta"
        EM_ANDAMENTO = "em_andamento", "Em andamento"
        AGUARDANDO_PECA = "aguardando_peca", "Aguardando peça"
        CONCLUIDA = "concluida", "Concluída"
        ENTREGUE = "entregue", "Entregue"

    numero = models.CharField(max_length=20, unique=True, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="ordens_servico")
    motocicleta = models.ForeignKey(Motocicleta, on_delete=models.PROTECT, related_name="ordens_servico")
    mecanico = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ordens_servico", verbose_name="Mecânico"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ABERTA)

    descricao_problema = models.TextField("Descrição do problema", blank=True)
    valor_servico = models.DecimalField("Valor do serviço", max_digits=10, decimal_places=2, default=0)

    data_abertura = models.DateTimeField(auto_now_add=True)
    data_conclusao = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Ordem de Serviço"
        verbose_name_plural = "Ordens de Serviço"
        ordering = ["-data_abertura"]

    def __str__(self):
        return f"{self.numero} - {self.cliente.nome}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.numero:
            # Gerado a partir do PK real (já garantido único pelo banco),
            # em vez de "último id + 1" calculado antes do insert — isso
            # evita colisão quando duas OS são criadas ao mesmo tempo.
            self.numero = f"OS-{self.pk:04d}"
            super().save(update_fields=["numero"])

    @property
    def peca_em_falta(self):
        """True se algum item da OS pede mais peça do que há em estoque."""
        return any(
            item.quantidade > item.peca.quantidade_estoque
            for item in self.itens.select_related("peca").all()
        )


class ItemOrdemServico(models.Model):
    """
    Peça utilizada em uma ordem de serviço. Cada item mantém uma
    Movimentacao de saída (motivo "uso_reparo") em dia automaticamente:
    ao salvar o item, a movimentação ligada é criada (ou atualizada, se a
    peça/quantidade mudou) e o estoque é descontado; ao remover o item,
    a movimentação ligada é excluída e o estoque volta. Isso evita o
    passo manual de duplicar o lançamento em Movimentações.
    """
    ordem_servico = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name="itens")
    peca = models.ForeignKey(
        Peca, on_delete=models.PROTECT, related_name="itens_os", verbose_name="Peça"
    )
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField("Preço unitário", max_digits=10, decimal_places=2)
    movimentacao = models.OneToOneField(
        "movimentacoes.Movimentacao", on_delete=models.SET_NULL,
        null=True, blank=True, editable=False, related_name="item_os",
    )

    class Meta:
        verbose_name = "Item da Ordem de Serviço"
        verbose_name_plural = "Itens da Ordem de Serviço"

    def __str__(self):
        return f"{self.peca.codigo} x{self.quantidade} ({self.ordem_servico.numero})"

    @property
    def subtotal(self):
        return self.quantidade * self.preco_unitario

    @transaction.atomic
    def save(self, *args, **kwargs):
        usuario = getattr(self, "_usuario_evento", None)
        super().save(*args, **kwargs)
        self._sync_movimentacao(usuario)

    def _sync_movimentacao(self, usuario=None):
        from movimentacoes.models import Movimentacao

        if self.movimentacao_id:
            mov = self.movimentacao
            mov.peca = self.peca
            mov.quantidade = self.quantidade
            mov.tipo = Movimentacao.Tipo.SAIDA
            mov.motivo = Movimentacao.Motivo.USO_REPARO
            mov.ordem_servico = self.ordem_servico
            mov.observacao = f"Item da OS {self.ordem_servico.numero}"
            mov.full_clean()
            mov.save()
        else:
            mov = Movimentacao(
                peca=self.peca,
                tipo=Movimentacao.Tipo.SAIDA,
                motivo=Movimentacao.Motivo.USO_REPARO,
                quantidade=self.quantidade,
                usuario=usuario or self.ordem_servico.mecanico,
                ordem_servico=self.ordem_servico,
                observacao=f"Item da OS {self.ordem_servico.numero}",
            )
            mov.full_clean()
            mov.save()
            ItemOrdemServico.objects.filter(pk=self.pk).update(movimentacao=mov)
            self.movimentacao = mov

    @transaction.atomic
    def delete(self, *args, **kwargs):
        mov = self.movimentacao
        super().delete(*args, **kwargs)
        if mov is not None:
            mov.delete()
