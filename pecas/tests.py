from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Categoria, Fabricante, Localizacao, ModeloMoto, Peca


class PecaPropriedadesTests(TestCase):
    def setUp(self):
        self.cat = Categoria.objects.create(nome="Motor QA")

    def test_abaixo_do_minimo(self):
        peca = Peca.objects.create(
            codigo="P-BAIXO", nome="Peça baixa", categoria=self.cat,
            quantidade_estoque=1, quantidade_minima=5,
        )
        self.assertTrue(peca.abaixo_do_minimo)

    def test_nao_abaixo_do_minimo(self):
        peca = Peca.objects.create(
            codigo="P-OK", nome="Peça ok", categoria=self.cat,
            quantidade_estoque=10, quantidade_minima=5,
        )
        self.assertFalse(peca.abaixo_do_minimo)

    def test_valor_total_estoque(self):
        peca = Peca.objects.create(
            codigo="P-VAL", nome="Peça valor", categoria=self.cat,
            quantidade_estoque=4, quantidade_minima=1, preco_custo=Decimal("12.50"),
        )
        self.assertEqual(peca.valor_total_estoque, 50)


class PecaListaPaginacaoTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin_pag", "a@a.com", "SenhaForte123!")
        self.client.force_login(self.admin)
        cat = Categoria.objects.create(nome="Paginação QA")
        for i in range(30):
            Peca.objects.create(
                codigo=f"PAG-{i:03d}", nome=f"Peça {i}", categoria=cat,
                quantidade_estoque=1, quantidade_minima=0,
            )

    def test_primeira_pagina_tem_25_itens_e_link_proxima(self):
        resp = self.client.get(reverse("pecas:list"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["page_obj"]), 25)
        self.assertContains(resp, "Próxima")

    def test_segunda_pagina_tem_o_restante(self):
        resp = self.client.get(reverse("pecas:list") + "?page=2")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["page_obj"]), 5)


class PopupCadastroAuxiliarTests(TestCase):
    """
    Os botões "+" do formulário de Peça abrem estes cadastros em popup
    (?popup=1&field=...) sem precisar do admin do Django. Confirma que o
    popup salva e devolve o script que fecha a janela e repassa o novo
    item para o <select> da tela que abriu.
    """

    def setUp(self):
        self.admin = User.objects.create_superuser("admin_pecas", "a@a.com", "SenhaForte123!")
        self.client.force_login(self.admin)

    def test_popup_fabricante_salva_e_fecha(self):
        resp = self.client.post(
            reverse("pecas:fabricante_novo") + "?popup=1&field=fabricante",
            {"nome": "Marca QA"},
        )
        self.assertEqual(resp.status_code, 200)
        fab = Fabricante.objects.get(nome="Marca QA")
        body = resp.content.decode()
        self.assertIn("dida-motos-popup", body)
        self.assertIn(f"id: {fab.pk}", body)

    def test_popup_localizacao_salva(self):
        resp = self.client.post(
            reverse("pecas:localizacao_novo") + "?popup=1&field=localizacao",
            {"setor": "Setor QA", "prateleira": "", "caixa": ""},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Localizacao.objects.filter(setor="Setor QA").exists())
        self.assertIn("dida-motos-popup", resp.content.decode())

    def test_popup_modelo_moto_salva(self):
        resp = self.client.post(
            reverse("pecas:modelo_novo") + "?popup=1&field=modelos_compativeis",
            {"marca": "Yamaha", "modelo": "Factor 125"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(ModeloMoto.objects.filter(marca="Yamaha", modelo="Factor 125").exists())
        self.assertIn("dida-motos-popup", resp.content.decode())

    def test_fluxo_normal_sem_popup_redireciona_para_lista(self):
        resp = self.client.post(reverse("pecas:fabricante_novo"), {"nome": "Marca Normal QA"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("pecas:fabricante_list"), resp.url)

    def test_peca_form_inclui_botoes_popup(self):
        resp = self.client.get(reverse("pecas:novo"))
        self.assertContains(resp, "popup-add")
        self.assertContains(resp, "dida-motos-popup")
