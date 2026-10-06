from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from pecas.models import Categoria, Peca
from movimentacoes.models import Movimentacao
from .forms import ClienteForm
from .models import Cliente, Motocicleta, OrdemServico, ItemOrdemServico
from .validators import validar_cpf


class OrdemServicoEstoqueTests(TestCase):
    """
    Cobre a geração do número da OS (a partir do PK real, sem corrida) e
    a sincronização automática entre itens da OS e Movimentacao (a OS
    desconta/devolve estoque sozinha, sem passo manual em Movimentações).
    """

    def setUp(self):
        self.admin = User.objects.create_superuser("admin_os", "a@a.com", "SenhaForte123!")
        cat = Categoria.objects.create(nome="Transmissão QA")
        self.peca = Peca.objects.create(
            codigo="OS-P1", nome="Kit Relação", categoria=cat,
            quantidade_estoque=10, quantidade_minima=2,
        )
        self.cliente = Cliente.objects.create(nome="Cliente OS", telefone="16999999999")
        self.moto = Motocicleta.objects.create(
            cliente=self.cliente, marca="Honda", modelo="CG 160", ano=2022,
        )
        self.client.force_login(self.admin)
        self.management_novo = {
            "itens-TOTAL_FORMS": "3", "itens-INITIAL_FORMS": "0",
            "itens-MIN_NUM_FORMS": "0", "itens-MAX_NUM_FORMS": "1000",
        }

    def _criar_os(self, quantidade):
        data = {
            "cliente": self.cliente.pk, "motocicleta": self.moto.pk, "mecanico": "",
            "status": "aberta", "descricao_problema": "Troca", "valor_servico": "50",
            "itens-0-peca": self.peca.pk, "itens-0-quantidade": str(quantidade),
            "itens-0-preco_unitario": "20",
            "itens-1-peca": "", "itens-1-quantidade": "1", "itens-1-preco_unitario": "",
            "itens-2-peca": "", "itens-2-quantidade": "1", "itens-2-preco_unitario": "",
            **self.management_novo,
        }
        return self.client.post(reverse("ordens_servico:nova"), data, follow=True)

    def test_numero_gerado_a_partir_do_pk(self):
        resp = self._criar_os(1)
        self.assertEqual(resp.status_code, 200)
        os_obj = OrdemServico.objects.get()
        self.assertEqual(os_obj.numero, f"OS-{os_obj.pk:04d}")

    def test_criar_os_com_item_desconta_estoque(self):
        self._criar_os(3)
        self.peca.refresh_from_db()
        self.assertEqual(self.peca.quantidade_estoque, 7)

        item = ItemOrdemServico.objects.get()
        self.assertIsNotNone(item.movimentacao_id)
        mov = item.movimentacao
        self.assertEqual(mov.tipo, "saida")
        self.assertEqual(mov.motivo, "uso_reparo")
        self.assertEqual(mov.quantidade, 3)
        self.assertEqual(mov.ordem_servico_id, item.ordem_servico_id)
        self.assertEqual(mov.usuario_id, self.admin.pk)

    def test_editar_item_ajusta_estoque(self):
        self._criar_os(3)
        os_obj = OrdemServico.objects.get()
        item = ItemOrdemServico.objects.get()

        management_edit = {
            "itens-TOTAL_FORMS": "4", "itens-INITIAL_FORMS": "1",
            "itens-MIN_NUM_FORMS": "0", "itens-MAX_NUM_FORMS": "1000",
        }
        data = {
            "cliente": self.cliente.pk, "motocicleta": self.moto.pk, "mecanico": "",
            "status": "em_andamento", "descricao_problema": "Troca", "valor_servico": "50",
            "itens-0-id": item.pk, "itens-0-peca": self.peca.pk,
            "itens-0-quantidade": "5", "itens-0-preco_unitario": "20",
            "itens-1-peca": "", "itens-1-quantidade": "1", "itens-1-preco_unitario": "",
            "itens-2-peca": "", "itens-2-quantidade": "1", "itens-2-preco_unitario": "",
            "itens-3-peca": "", "itens-3-quantidade": "1", "itens-3-preco_unitario": "",
            **management_edit,
        }
        resp = self.client.post(reverse("ordens_servico:editar", args=[os_obj.pk]), data, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.peca.refresh_from_db()
        self.assertEqual(self.peca.quantidade_estoque, 5)  # 10 - 5

    def test_remover_item_devolve_estoque(self):
        self._criar_os(3)
        os_obj = OrdemServico.objects.get()
        item = ItemOrdemServico.objects.get()
        mov_id = item.movimentacao_id

        management_edit = {
            "itens-TOTAL_FORMS": "4", "itens-INITIAL_FORMS": "1",
            "itens-MIN_NUM_FORMS": "0", "itens-MAX_NUM_FORMS": "1000",
        }
        data = {
            "cliente": self.cliente.pk, "motocicleta": self.moto.pk, "mecanico": "",
            "status": "em_andamento", "descricao_problema": "Troca", "valor_servico": "50",
            "itens-0-id": item.pk, "itens-0-peca": self.peca.pk,
            "itens-0-quantidade": "3", "itens-0-preco_unitario": "20", "itens-0-DELETE": "on",
            "itens-1-peca": "", "itens-1-quantidade": "1", "itens-1-preco_unitario": "",
            "itens-2-peca": "", "itens-2-quantidade": "1", "itens-2-preco_unitario": "",
            "itens-3-peca": "", "itens-3-quantidade": "1", "itens-3-preco_unitario": "",
            **management_edit,
        }
        resp = self.client.post(reverse("ordens_servico:editar", args=[os_obj.pk]), data, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.peca.refresh_from_db()
        self.assertEqual(self.peca.quantidade_estoque, 10)
        self.assertFalse(ItemOrdemServico.objects.filter(pk=item.pk).exists())
        self.assertFalse(Movimentacao.objects.filter(pk=mov_id).exists())

    def test_estoque_insuficiente_bloqueia_criacao_da_os_inteira(self):
        resp = self._criar_os(999)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("estoque insuficiente", resp.content.decode().lower())
        self.assertEqual(OrdemServico.objects.count(), 0)
        self.peca.refresh_from_db()
        self.assertEqual(self.peca.quantidade_estoque, 10)

    def test_form_tem_combobox_com_busca_para_cliente_motocicleta_e_peca(self):
        """Cliente, Motocicleta e os itens (Peça) usam o widget searchable."""
        resp = self.client.get(reverse("ordens_servico:nova"))
        # 1x cliente + 1x motocicleta + 3x itens (extra=3) = 5 selects searchable.
        self.assertEqual(resp.content.decode().count('class="searchable"'), 5)
        self.assertContains(resp, "core/js/searchable-select.js")


class ClienteCpfTests(TestCase):
    """
    CPF do cliente: validação do dígito verificador (algoritmo módulo
    11, sem depender de nenhuma API externa) e unicidade.
    """

    def test_validador_aceita_cpf_valido(self):
        # CPFs sintéticos com dígitos verificadores corretos.
        validar_cpf("111.444.777-35")
        validar_cpf("52998224725")

    def test_validador_rejeita_cpf_com_digito_verificador_errado(self):
        with self.assertRaises(ValidationError):
            validar_cpf("123.456.789-00")

    def test_validador_rejeita_todos_os_digitos_iguais(self):
        with self.assertRaises(ValidationError):
            validar_cpf("111.111.111-11")

    def test_cliente_com_cpf_invalido_nao_passa_no_full_clean(self):
        cliente = Cliente(nome="Cliente Ruim", cpf="12345678900")
        with self.assertRaises(ValidationError):
            cliente.full_clean()

    def test_formulario_bloqueia_cpf_duplicado(self):
        Cliente.objects.create(nome="Primeiro", cpf="11144477735")
        form = ClienteForm(data={
            "nome": "Segundo", "cpf": "111.444.777-35", "telefone": "", "email": "",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("cpf", form.errors)

    def test_formulario_aceita_cpf_em_branco(self):
        form = ClienteForm(data={"nome": "Sem CPF", "cpf": "", "telefone": "", "email": ""})
        self.assertTrue(form.is_valid())
        cliente = form.save()
        self.assertIsNone(cliente.cpf)


class ClienteBuscarCpfViewTests(TestCase):
    """Endpoint JSON usado pelo cadastro de veículo para autopreencher um cliente já existente."""

    def setUp(self):
        self.admin = User.objects.create_superuser("admin_cpf", "a@a.com", "SenhaForte123!")
        self.client.force_login(self.admin)

    def test_busca_requer_login(self):
        self.client.logout()
        resp = self.client.get(reverse("ordens_servico:cliente_buscar_cpf"), {"cpf": "11144477735"})
        self.assertEqual(resp.status_code, 302)

    def test_encontra_cliente_existente_por_cpf_formatado(self):
        cliente = Cliente.objects.create(nome="Cliente Encontrado", cpf="11144477735", telefone="16999998888")
        resp = self.client.get(reverse("ordens_servico:cliente_buscar_cpf"), {"cpf": "111.444.777-35"})
        dados = resp.json()
        self.assertTrue(dados["encontrado"])
        self.assertEqual(dados["id"], cliente.pk)
        self.assertEqual(dados["nome"], "Cliente Encontrado")
        self.assertEqual(dados["telefone"], "16999998888")

    def test_cpf_nao_cadastrado_retorna_nao_encontrado(self):
        resp = self.client.get(reverse("ordens_servico:cliente_buscar_cpf"), {"cpf": "52998224725"})
        self.assertFalse(resp.json()["encontrado"])

    def test_cpf_incompleto_retorna_nao_encontrado_sem_consultar_banco(self):
        resp = self.client.get(reverse("ordens_servico:cliente_buscar_cpf"), {"cpf": "123"})
        self.assertFalse(resp.json()["encontrado"])


class VeiculoComClienteCadastroTests(TestCase):
    """
    Cadastro combinado (veículo em primeiro plano): cria cliente novo
    junto com o veículo, ou reaproveita um cliente já cadastrado — seja
    pelo select de busca, seja pelo CPF batendo com alguém já existente.
    """

    def setUp(self):
        self.admin = User.objects.create_superuser("admin_vc", "a@a.com", "SenhaForte123!")
        self.client.force_login(self.admin)

    def test_cadastro_com_cliente_novo_cria_cliente_e_moto(self):
        resp = self.client.post(reverse("ordens_servico:motocicleta_novo"), {
            "placa": "ABC1D23", "marca": "Honda", "modelo": "CG 160", "ano": "2023",
            "cliente_existente": "", "cliente_nome": "Cliente Novo",
            "cliente_cpf": "111.444.777-35", "cliente_telefone": "16988887777",
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        cliente = Cliente.objects.get(cpf="11144477735")
        self.assertEqual(cliente.nome, "Cliente Novo")
        moto = Motocicleta.objects.get(placa="ABC1D23")
        self.assertEqual(moto.cliente, cliente)

    def test_cadastro_reaproveita_cliente_existente_selecionado(self):
        cliente = Cliente.objects.create(nome="Cliente Existente", telefone="16977776666")
        resp = self.client.post(reverse("ordens_servico:motocicleta_novo"), {
            "placa": "XYZ9A88", "marca": "Yamaha", "modelo": "Factor 125", "ano": "2021",
            "cliente_existente": str(cliente.pk),
            "cliente_nome": "", "cliente_cpf": "", "cliente_telefone": "",
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Cliente.objects.count(), 1)
        moto = Motocicleta.objects.get(placa="XYZ9A88")
        self.assertEqual(moto.cliente, cliente)

    def test_cpf_batendo_com_cliente_existente_evita_duplicar(self):
        cliente = Cliente.objects.create(nome="Já Existe", cpf="52998224725", telefone="16911112222")
        resp = self.client.post(reverse("ordens_servico:motocicleta_novo"), {
            "placa": "QQQ1Z11", "marca": "Honda", "modelo": "Biz 125", "ano": "2020",
            "cliente_existente": "", "cliente_nome": "Nome Digitado Errado",
            "cliente_cpf": "529.982.247-25", "cliente_telefone": "",
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Cliente.objects.count(), 1)
        moto = Motocicleta.objects.get(placa="QQQ1Z11")
        self.assertEqual(moto.cliente, cliente)
        self.assertEqual(moto.cliente.nome, "Já Existe")

    def test_sem_cliente_existente_nem_nome_novo_da_erro(self):
        resp = self.client.post(reverse("ordens_servico:motocicleta_novo"), {
            "placa": "", "marca": "Honda", "modelo": "CG 160", "ano": "",
            "cliente_existente": "", "cliente_nome": "", "cliente_cpf": "", "cliente_telefone": "",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Motocicleta.objects.count(), 0)

    def test_pagina_de_cadastro_novo_tem_toggle_e_js(self):
        resp = self.client.get(reverse("ordens_servico:motocicleta_novo"))
        self.assertContains(resp, "cliente_modo")
        self.assertContains(resp, "core/js/veiculo-cliente-form.js")

    def test_edicao_de_veiculo_existente_usa_formulario_simples(self):
        cliente = Cliente.objects.create(nome="Dono", telefone="16955554444")
        moto = Motocicleta.objects.create(cliente=cliente, marca="Honda", modelo="CG 160", ano=2019)
        resp = self.client.post(reverse("ordens_servico:motocicleta_editar", args=[moto.pk]), {
            "cliente": cliente.pk, "marca": "Honda", "modelo": "CG 160 Titan", "ano": "2019", "placa": "AAA1B11",
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        moto.refresh_from_db()
        self.assertEqual(moto.modelo, "CG 160 Titan")
        self.assertEqual(moto.placa, "AAA1B11")
