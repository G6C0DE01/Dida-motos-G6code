from django.conf import settings
from django.db import models, transaction
from django.core.exceptions import ValidationError

from pecas.models import Peca


class Movimentacao(models.Model):
    """
    Registro de movimentação de estoque (módulo B do escopo): toda
    entrada, saída ou ajuste de uma peça passa por aqui, o que dá o
    histórico completo (data, usuário, motivo, quantidade) pedido no
    escopo. `Peca.quantidade_estoque` é atualizada automaticamente no
    save() da movimentação, então a peça nunca deve ser editada
    diretamente para mudar estoque.
    """

    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        SAIDA = "saida", "Saída"
        AJUSTE = "ajuste", "Ajuste"

    class Motivo(models.TextChoices):
        # Entrada
        RECEBIMENTO_FORNECEDOR = "recebimento_fornecedor", "Recebimento de fornecedor"
        DEVOLUCAO = "devolucao", "Devolução"
        TRANSFERENCIA_ENTRADA = "transferencia_entrada", "Transferência (entrada)"
        # Saída
        USO_REPARO = "uso_reparo", "Uso em reparo"
        VENDA = "venda", "Venda"
        EMPRESTIMO = "emprestimo", "Empréstimo"
        # Ajuste
        INVENTARIO = "inventario", "Inventário"
        PERDA = "perda", "Perda"
        DANO = "dano", "Dano"
        OUTRO = "outro", "Outro"

    peca = models.ForeignKey(
        Peca, on_delete=models.PROTECT, related_name="movimentacoes", verbose_name="Peça"
    )
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    motivo = models.CharField(max_length=30, choices=Motivo.choices)

    class DirecaoAjuste(models.TextChoices):
        AUMENTO = "aumento", "Aumento (entrou mais do que constava)"
        REDUCAO = "reducao", "Redução (perda, dano ou contagem menor)"

    quantidade = models.PositiveIntegerField(
        help_text="Quantidade movimentada (sempre um número positivo)."
    )
    direcao_ajuste = models.CharField(
        "Direção do ajuste",
        max_length=10, choices=DirecaoAjuste.choices, blank=True,
        help_text="Só se aplica quando o tipo é Ajuste: define se a "
                   "quantidade acima deve ser somada ou subtraída do estoque."
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="movimentacoes"
    )
    data = models.DateTimeField(auto_now_add=True)
    observacao = models.CharField("Observação", max_length=255, blank=True)

    ordem_servico = models.ForeignKey(
        "ordens_servico.OrdemServico", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="movimentacoes",
        verbose_name="Ordem de serviço",
        help_text="Preenchido quando a saída é para uso em reparo (OS)."
    )

    class Meta:
        verbose_name = "Movimentação"
        verbose_name_plural = "Movimentações"
        ordering = ["-data"]

    def __str__(self):
        sinal = "+" if self.tipo == self.Tipo.ENTRADA else "-"
        return f"{self.get_tipo_display()} {sinal}{self.quantidade} - {self.peca.codigo}"

    def _delta_estoque(self):
        """
        Efeito desta movimentação sobre Peca.quantidade_estoque: positivo
        soma, negativo subtrai. Usado tanto para aplicar (criação) quanto
        para reverter (edição/exclusão) o efeito no estoque.
        """
        reduz = self.tipo == self.Tipo.SAIDA or (
            self.tipo == self.Tipo.AJUSTE and self.direcao_ajuste == self.DirecaoAjuste.REDUCAO
        )
        return -self.quantidade if reduz else self.quantidade

    def clean(self):
        if self.tipo == self.Tipo.AJUSTE and not self.direcao_ajuste:
            raise ValidationError(
                "Para um ajuste, informe se a quantidade deve ser somada "
                "(aumento) ou subtraída (redução) do estoque."
            )
        if self.peca_id:
            # Estoque disponível considerando o efeito desta própria
            # movimentação: numa edição, o efeito antigo dela precisa ser
            # "desfeito" antes de checar se o novo valor cabe no estoque.
            estoque_disponivel = self.peca.quantidade_estoque
            if not self._state.adding:
                original = Movimentacao.objects.filter(pk=self.pk).first()
                if original and original.peca_id == self.peca_id:
                    estoque_disponivel -= original._delta_estoque()
            if estoque_disponivel + self._delta_estoque() < 0:
                raise ValidationError(
                    f"Estoque insuficiente: essa operação deixaria o estoque de "
                    f"{self.peca.nome} negativo (disponível: {estoque_disponivel})."
                )

    @transaction.atomic
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if is_new:
            peca = Peca.objects.select_for_update().get(pk=self.peca_id)
            novo_estoque = peca.quantidade_estoque + self._delta_estoque()
            if novo_estoque < 0:
                raise ValidationError("Estoque insuficiente para essa movimentação.")
            peca.quantidade_estoque = novo_estoque
            peca.save(update_fields=["quantidade_estoque", "atualizado_em"])
        else:
            # Edição: desfaz o efeito antigo (na peça antiga) e aplica o
            # novo efeito (na peça nova), que podem ser a mesma peça ou não.
            original = Movimentacao.objects.get(pk=self.pk)
            old_delta = original._delta_estoque()
            new_delta = self._delta_estoque()
            if original.peca_id == self.peca_id:
                peca = Peca.objects.select_for_update().get(pk=self.peca_id)
                novo_estoque = peca.quantidade_estoque - old_delta + new_delta
                if novo_estoque < 0:
                    raise ValidationError("Estoque insuficiente para aplicar essa alteração.")
                peca.quantidade_estoque = novo_estoque
                peca.save(update_fields=["quantidade_estoque", "atualizado_em"])
            else:
                peca_antiga = Peca.objects.select_for_update().get(pk=original.peca_id)
                peca_nova = Peca.objects.select_for_update().get(pk=self.peca_id)
                estoque_antigo = peca_antiga.quantidade_estoque - old_delta
                estoque_novo = peca_nova.quantidade_estoque + new_delta
                if estoque_antigo < 0 or estoque_novo < 0:
                    raise ValidationError("Estoque insuficiente para aplicar essa alteração.")
                peca_antiga.quantidade_estoque = estoque_antigo
                peca_antiga.save(update_fields=["quantidade_estoque", "atualizado_em"])
                peca_nova.quantidade_estoque = estoque_novo
                peca_nova.save(update_fields=["quantidade_estoque", "atualizado_em"])
        super().save(*args, **kwargs)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        peca = Peca.objects.select_for_update().get(pk=self.peca_id)
        novo_estoque = peca.quantidade_estoque - self._delta_estoque()
        if novo_estoque < 0:
            raise ValidationError(
                f"Não é possível excluir: o estoque de {peca.nome} ficaria negativo. "
                f"Ajuste outras movimentações primeiro."
            )
        peca.quantidade_estoque = novo_estoque
        peca.save(update_fields=["quantidade_estoque", "atualizado_em"])
        super().delete(*args, **kwargs)
