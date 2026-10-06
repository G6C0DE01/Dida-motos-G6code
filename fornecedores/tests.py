from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from pecas.models import Categoria, Peca
from .models import Fornecedor, HistoricoCompra


class FornecedorTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin_forn", "a@a.com", "SenhaForte123!")
        self.client.force_login(self.admin)
        cat = Categoria.objects.create(nome="Consumíveis QA")
        self.peca = Peca.objects.create(
            codigo="F-P1", nome="Óleo", categoria=cat,
            quantidade_estoque=5, quantidade_minima=1,
        )

    def test_lista_requer_login(self):
        self.client.logout()
        resp = self.client.get(reverse("fornecedores:list"))
        self.assertEqual(resp.status_code, 302)

    def test_criar_fornecedor(self):
        resp = self.client.post(reverse("fornecedores:novo"), {
            "nome": "Distribuidora QA", "contato_nome": "", "telefone": "",
            "email": "", "localizacao": "", "prazo_entrega_dias": "",
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Fornecedor.objects.filter(nome="Distribuidora QA").exists())

    def test_criar_historico_compra(self):
        fornecedor = Fornecedor.objects.create(nome="Distribuidora QA 2")
        resp = self.client.post(
            reverse("fornecedores:historico_novo", args=[fornecedor.pk]),
            {
                "peca": self.peca.pk, "tipo": "compra",
                "quantidade": "10", "preco_unitario": "15.00",
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(
            HistoricoCompra.objects.filter(fornecedor=fornecedor, peca=self.peca).exists()
        )
