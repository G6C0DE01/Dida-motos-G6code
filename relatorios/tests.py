from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from pecas.models import Categoria, Peca
from movimentacoes.models import Movimentacao

User = get_user_model()


class RelatoriosAcessoTests(TestCase):
    """Todo relatório exige login (dado sensível de estoque/custo)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="user1", password="senha123", is_active=True
        )
        self.categoria = Categoria.objects.get(nome="Motor")
        self.peca = Peca.objects.create(
            codigo="P001", nome="Vela de ignição", categoria=self.categoria,
            quantidade_estoque=10, quantidade_minima=5, preco_custo=Decimal("12.50"),
        )

    def _urls(self):
        return [
            reverse("relatorios:estoque_por_categoria"),
            reverse("relatorios:pecas_em_falta"),
            reverse("relatorios:pecas_paradas"),
            reverse("relatorios:custo_total_estoque"),
            reverse("relatorios:rotatividade"),
            reverse("relatorios:previsao_falta"),
        ]

    def test_relatorios_exigem_login(self):
        for url in self._urls():
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn("next=", response.url)

    def test_relatorios_carregam_para_usuario_logado(self):
        self.client.login(username="user1", password="senha123")
        for url in self._urls():
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)


class RelatoriosCsvExportTests(TestCase):
    """Cobre o botão "Exportar CSV" presente nos 6 relatórios."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="user1", password="senha123", is_active=True
        )
        self.client.login(username="user1", password="senha123")
        self.categoria = Categoria.objects.get(nome="Motor")
        self.peca_falta = Peca.objects.create(
            codigo="P001", nome="Vela de ignição", categoria=self.categoria,
            quantidade_estoque=2, quantidade_minima=5, preco_custo=Decimal("12.50"),
        )
        self.peca_ok = Peca.objects.create(
            codigo="P002", nome="Filtro de óleo", categoria=self.categoria,
            quantidade_estoque=20, quantidade_minima=5, preco_custo=Decimal("30.00"),
        )
        Movimentacao.objects.create(
            peca=self.peca_ok, tipo=Movimentacao.Tipo.SAIDA,
            motivo=Movimentacao.Motivo.VENDA, quantidade=3, usuario=self.user,
        )

    def test_pecas_em_falta_export_csv(self):
        response = self.client.get(reverse("relatorios:pecas_em_falta"), {"export": "csv"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/csv"))
        self.assertIn('attachment; filename="pecas_em_falta.csv"', response["Content-Disposition"])
        conteudo = response.content.decode("utf-8-sig")
        self.assertIn("Código;Nome;Categoria;Fabricante;Estoque;Mínimo", conteudo)
        self.assertIn("P001;Vela de ignição;Motor;-;2;5", conteudo)
        # Peça com estoque acima do mínimo não deve aparecer nesse relatório.
        self.assertNotIn("P002", conteudo)

    def test_custo_total_estoque_export_csv(self):
        response = self.client.get(reverse("relatorios:custo_total_estoque"), {"export": "csv"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/csv"))
        self.assertIn('attachment; filename="custo_total_estoque.csv"', response["Content-Disposition"])
        conteudo = response.content.decode("utf-8-sig")
        # peca_ok começa com 20 e sofre uma saída de 3 no setUp -> 17 em estoque.
        self.assertIn("P001;Vela de ignição;Motor;2;12.50;25.00", conteudo)
        self.assertIn("P002;Filtro de óleo;Motor;17;30.00;510.00", conteudo)

    def test_rotatividade_export_csv(self):
        response = self.client.get(reverse("relatorios:rotatividade"), {"export": "csv"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/csv"))
        conteudo = response.content.decode("utf-8-sig")
        self.assertIn("P002;Filtro de óleo;3", conteudo)

    def test_estoque_por_categoria_export_csv(self):
        response = self.client.get(reverse("relatorios:estoque_por_categoria"), {"export": "csv"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/csv"))
        conteudo = response.content.decode("utf-8-sig")
        # 2 (P001) + 17 (P002, após a saída de 3 no setUp) = 19; 25.00 + 510.00 = 535.00.
        self.assertIn("Motor;2;19;535.00", conteudo)

    def test_pecas_paradas_export_csv(self):
        response = self.client.get(reverse("relatorios:pecas_paradas"), {"export": "csv"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/csv"))
        conteudo = response.content.decode("utf-8-sig")
        # P001 nunca teve movimentação -> deve aparecer como parada.
        self.assertIn("P001;Vela de ignição;Motor;2", conteudo)

    def test_previsao_falta_export_csv(self):
        response = self.client.get(reverse("relatorios:previsao_falta"), {"export": "csv"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/csv"))
        conteudo = response.content.decode("utf-8-sig")
        self.assertIn("Código;Nome;Consumo médio/dia;Dias até o mínimo", conteudo)
        self.assertIn("P002", conteudo)

    def test_export_nao_afeta_pagina_normal(self):
        """Sem ?export=csv, a página normal (HTML) continua funcionando."""
        response = self.client.get(reverse("relatorios:pecas_em_falta"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"].split(";")[0].strip(), "text/html")
