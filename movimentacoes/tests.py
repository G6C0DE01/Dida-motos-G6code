from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from pecas.models import Categoria, Peca
from .models import Movimentacao


class MovimentacaoEstoqueTests(TestCase):
    """
    Garante que Movimentacao mantém Peca.quantidade_estoque correta em
    todos os cenários: criação, edição (mesma peça e trocando de peça) e
    exclusão — inclusive quando a operação deveria ser bloqueada por
    deixar o estoque negativo.
    """

    def setUp(self):
        self.admin = User.objects.create_superuser("admin_mov", "a@a.com", "SenhaForte123!")
        cat = Categoria.objects.create(nome="Motor QA")
        self.peca_a = Peca.objects.create(
            codigo="MOV-A", nome="Peça A", categoria=cat,
            quantidade_estoque=10, quantidade_minima=2,
        )
        self.peca_b = Peca.objects.create(
            codigo="MOV-B", nome="Peça B", categoria=cat,
            quantidade_estoque=5, quantidade_minima=2,
        )
        self.client.force_login(self.admin)

    def test_entrada_aumenta_estoque(self):
        Movimentacao.objects.create(
            peca=self.peca_a, tipo="entrada", motivo="recebimento_fornecedor",
            quantidade=4, usuario=self.admin,
        )
        self.peca_a.refresh_from_db()
        self.assertEqual(self.peca_a.quantidade_estoque, 14)

    def test_saida_diminui_estoque(self):
        Movimentacao.objects.create(
            peca=self.peca_a, tipo="saida", motivo="venda",
            quantidade=3, usuario=self.admin,
        )
        self.peca_a.refresh_from_db()
        self.assertEqual(self.peca_a.quantidade_estoque, 7)

    def test_ajuste_sem_direcao_e_invalido(self):
        mov = Movimentacao(
            peca=self.peca_a, tipo="ajuste", motivo="inventario",
            quantidade=1, usuario=self.admin,
        )
        with self.assertRaises(ValidationError):
            mov.full_clean()

    def test_saida_maior_que_estoque_e_bloqueada(self):
        mov = Movimentacao(
            peca=self.peca_a, tipo="saida", motivo="venda",
            quantidade=999, usuario=self.admin,
        )
        with self.assertRaises(ValidationError):
            mov.full_clean()

    def test_editar_mesma_peca_recalcula_estoque(self):
        mov = Movimentacao.objects.create(
            peca=self.peca_a, tipo="saida", motivo="venda",
            quantidade=3, usuario=self.admin,
        )
        self.peca_a.refresh_from_db()
        self.assertEqual(self.peca_a.quantidade_estoque, 7)

        resp = self.client.post(reverse("movimentacoes:editar", args=[mov.pk]), {
            "peca": self.peca_a.pk, "tipo": "saida", "motivo": "venda", "quantidade": 5,
            "direcao_ajuste": "", "observacao": "", "ordem_servico": "",
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.peca_a.refresh_from_db()
        self.assertEqual(self.peca_a.quantidade_estoque, 5)

    def test_editar_trocando_peca_reverte_e_aplica(self):
        mov = Movimentacao.objects.create(
            peca=self.peca_a, tipo="saida", motivo="venda",
            quantidade=5, usuario=self.admin,
        )
        resp = self.client.post(reverse("movimentacoes:editar", args=[mov.pk]), {
            "peca": self.peca_b.pk, "tipo": "saida", "motivo": "venda", "quantidade": 2,
            "direcao_ajuste": "", "observacao": "", "ordem_servico": "",
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.peca_a.refresh_from_db()
        self.peca_b.refresh_from_db()
        self.assertEqual(self.peca_a.quantidade_estoque, 10)  # devolvido
        self.assertEqual(self.peca_b.quantidade_estoque, 3)   # 5 - 2

    def test_excluir_devolve_estoque(self):
        mov = Movimentacao.objects.create(
            peca=self.peca_a, tipo="saida", motivo="venda",
            quantidade=4, usuario=self.admin,
        )
        resp = self.client.post(reverse("movimentacoes:excluir", args=[mov.pk]), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.peca_a.refresh_from_db()
        self.assertEqual(self.peca_a.quantidade_estoque, 10)
        self.assertFalse(Movimentacao.objects.filter(pk=mov.pk).exists())

    def test_excluir_bloqueada_quando_deixaria_estoque_negativo(self):
        entrada = Movimentacao.objects.create(
            peca=self.peca_b, tipo="entrada", motivo="recebimento_fornecedor",
            quantidade=10, usuario=self.admin,
        )
        Movimentacao.objects.create(
            peca=self.peca_b, tipo="saida", motivo="venda",
            quantidade=13, usuario=self.admin,
        )
        self.peca_b.refresh_from_db()
        self.assertEqual(self.peca_b.quantidade_estoque, 2)

        resp = self.client.post(reverse("movimentacoes:excluir", args=[entrada.pk]), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Movimentacao.objects.filter(pk=entrada.pk).exists())
        self.peca_b.refresh_from_db()
        self.assertEqual(self.peca_b.quantidade_estoque, 2)

    def test_lista_mostra_editar_e_excluir(self):
        Movimentacao.objects.create(
            peca=self.peca_a, tipo="entrada", motivo="recebimento_fornecedor",
            quantidade=1, usuario=self.admin,
        )
        resp = self.client.get(reverse("movimentacoes:list"))
        self.assertContains(resp, "Editar")
        self.assertContains(resp, "Excluir")

    def test_form_peca_tem_combobox_com_busca(self):
        """O campo Peça usa o widget searchable (JS progressive enhancement)."""
        resp = self.client.get(reverse("movimentacoes:nova"))
        self.assertContains(resp, 'class="searchable"')
        self.assertContains(resp, "core/js/searchable-select.js")


class MovimentacaoPermissaoGerenteTests(TestCase):
    """
    Excluir movimentação é restrito ao grupo "Gerentes" (ou staff) — ver
    core.decorators.gerente_required. Mecânicos comuns podem registrar e
    editar movimentações normalmente, mas não excluir.
    """

    def setUp(self):
        cat = Categoria.objects.create(nome="Motor QA 2")
        self.peca = Peca.objects.create(
            codigo="MOV-C", nome="Peça C", categoria=cat,
            quantidade_estoque=10, quantidade_minima=2,
        )
        self.mecanico = User.objects.create_user("mecanico1", "m@a.com", "SenhaForte123!")
        self.mov = Movimentacao.objects.create(
            peca=self.peca, tipo="saida", motivo="venda",
            quantidade=3, usuario=self.mecanico,
        )

    def test_mecanico_comum_nao_pode_excluir(self):
        self.client.force_login(self.mecanico)
        resp = self.client.post(reverse("movimentacoes:excluir", args=[self.mov.pk]), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Movimentacao.objects.filter(pk=self.mov.pk).exists())
        self.peca.refresh_from_db()
        self.assertEqual(self.peca.quantidade_estoque, 7)  # inalterado

    def test_membro_do_grupo_gerentes_pode_excluir(self):
        from django.contrib.auth.models import Group
        self.mecanico.groups.add(Group.objects.get(name="Gerentes"))
        self.client.force_login(self.mecanico)
        resp = self.client.post(reverse("movimentacoes:excluir", args=[self.mov.pk]), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Movimentacao.objects.filter(pk=self.mov.pk).exists())
        self.peca.refresh_from_db()
        self.assertEqual(self.peca.quantidade_estoque, 10)  # devolvido

    def test_botao_excluir_escondido_para_mecanico_comum(self):
        self.client.force_login(self.mecanico)
        resp = self.client.get(reverse("movimentacoes:list"))
        self.assertContains(resp, "Editar")
        self.assertNotContains(resp, "Excluir")
