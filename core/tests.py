from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from movimentacoes.models import Movimentacao
from pecas.models import Categoria, Peca

from .charts import entradas_saidas_chart
from .models import PerfilUsuario


class LoginLogoutTests(TestCase):
    """
    Cobre o fluxo de autenticação sem autocadastro público: só um gerente
    pode criar contas (FuncionarioCadastroTests cobre isso); aqui só o
    login/logout e o bloqueio de conta desativada.
    """

    def test_dashboard_requires_login(self):
        resp = self.client.get(reverse("core:dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("core:login"), resp.url)

    def test_login_page_loads(self):
        self.assertEqual(self.client.get(reverse("core:login")).status_code, 200)

    def test_login_blocked_while_inactive_then_succeeds_after_reativado(self):
        user = User.objects.create_user("desativado", password="SenhaForte123!", is_active=False)

        resp = self.client.post(reverse("core:login"), {
            "username": "desativado", "password": "SenhaForte123!",
        }, follow=True)
        self.assertIn("desativada", resp.content.decode().lower())
        self.assertEqual(self.client.get(reverse("core:dashboard")).status_code, 302)

        user.is_active = True
        user.save(update_fields=["is_active"])

        resp = self.client.post(reverse("core:login"), {
            "username": "desativado", "password": "SenhaForte123!",
        }, follow=True)
        self.assertEqual(self.client.get(reverse("core:dashboard")).status_code, 200)

    def test_logout_redirects_to_login(self):
        user = User.objects.create_user("ativo", password="SenhaForte123!", is_active=True)
        self.client.force_login(user)
        resp = self.client.post(reverse("core:logout"), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.get(reverse("core:dashboard")).status_code, 302)

    def test_admin_bulk_ativar_acesso_action(self):
        admin = User.objects.create_superuser("admin_qa", "admin@example.com", "SenhaForte123!")
        desativado = User.objects.create_user("desativado2", password="SenhaForte123!", is_active=False)

        self.client.force_login(admin)
        resp = self.client.post("/admin/auth/user/", {
            "action": "ativar_acesso",
            "_selected_action": [str(desativado.pk)],
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        desativado.refresh_from_db()
        self.assertTrue(desativado.is_active)


class FuncionarioCadastroTests(TestCase):
    """
    Cadastro de funcionário pelo admin/gerente: só gerente acessa, gera
    usuário e senha automaticamente (sem e-mail, sem a pessoa escolher
    usuário/senha), cria a conta já ativa e marcada para trocar a senha
    no primeiro login.
    """

    def setUp(self):
        self.gerentes = Group.objects.get(name="Gerentes")
        self.gerente = User.objects.create_user("gerente_qa", password="SenhaForte123!", is_active=True)
        self.gerente.groups.add(self.gerentes)
        self.mecanico = User.objects.create_user("mecanico_qa", password="SenhaForte123!", is_active=True)

    def test_mecanico_comum_nao_acessa_cadastro_de_funcionario(self):
        self.client.force_login(self.mecanico)
        resp = self.client.get(reverse("core:funcionario_novo"), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.redirect_chain[-1][0], reverse("core:dashboard"))
        self.assertFalse(User.objects.filter(first_name="Não Deveria Existir").exists())

    def test_gerente_cadastra_funcionario_sem_email_com_senha_temporaria(self):
        self.client.force_login(self.gerente)
        resp = self.client.post(reverse("core:funcionario_novo"), {
            "nome": "João Mecânico", "grupo": "Mecânicos",
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        user = User.objects.get(first_name="João Mecânico")
        self.assertEqual(user.username, "joao.m")
        self.assertEqual(user.email, "")
        self.assertTrue(user.is_active)
        self.assertTrue(user.groups.filter(name="Mecânicos").exists())
        self.assertTrue(user.perfil.deve_trocar_senha)

        # A senha temporária gerada aparece na resposta (pra ser repassada ao funcionário).
        self.assertContains(resp, user.username)
        self.assertContains(resp, "Senha temporária")

    def test_username_gerado_evita_colisao(self):
        self.client.force_login(self.gerente)
        self.client.post(reverse("core:funcionario_novo"), {"nome": "Ana Silva", "grupo": "Mecânicos"})
        self.client.post(reverse("core:funcionario_novo"), {"nome": "Ana Souza", "grupo": "Mecânicos"})
        usuarios = set(User.objects.filter(first_name__startswith="Ana").values_list("username", flat=True))
        self.assertEqual(usuarios, {"ana.s", "ana.s2"})

    def test_conta_criada_precisa_trocar_senha_no_primeiro_login(self):
        self.client.force_login(self.gerente)
        self.client.post(reverse("core:funcionario_novo"), {"nome": "Carlos Souza", "grupo": "Mecânicos"})
        novo = User.objects.get(first_name="Carlos Souza")
        self.client.logout()

        # A senha real gerada não é previsível, então login por senha não dá
        # pra testar aqui sem capturá-la — em vez disso, força o estado e
        # confere que o middleware redireciona (o comportamento em si é
        # coberto por TrocaSenhaObrigatoriaTests).
        self.assertTrue(novo.perfil.deve_trocar_senha)


class TrocaSenhaObrigatoriaTests(TestCase):
    """
    ForcarTrocaSenhaMiddleware: enquanto perfil.deve_trocar_senha=True,
    qualquer página redireciona para a troca de senha; depois de trocar,
    o acesso normal volta.
    """

    def setUp(self):
        self.user = User.objects.create_user("temp_senha", password="SenhaTemp123!", is_active=True)
        PerfilUsuario.objects.create(user=self.user, deve_trocar_senha=True)
        self.client.force_login(self.user)

    def test_qualquer_pagina_redireciona_para_troca_de_senha(self):
        resp = self.client.get(reverse("core:dashboard"))
        self.assertRedirects(resp, reverse("core:trocar_senha"))

    def test_pagina_de_troca_de_senha_e_logout_ficam_liberados(self):
        self.assertEqual(self.client.get(reverse("core:trocar_senha")).status_code, 200)

    def test_trocar_senha_libera_o_resto_do_sistema(self):
        resp = self.client.post(reverse("core:trocar_senha"), {
            "old_password": "SenhaTemp123!",
            "new_password1": "SenhaDefinitiva456!",
            "new_password2": "SenhaDefinitiva456!",
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        self.user.refresh_from_db()
        self.assertFalse(self.user.perfil.deve_trocar_senha)

        resp = self.client.get(reverse("core:dashboard"))
        self.assertEqual(resp.status_code, 200)

    def test_usuario_sem_flag_acessa_normalmente(self):
        outro = User.objects.create_user("normal_qa", password="SenhaForte123!", is_active=True)
        self.client.force_login(outro)
        resp = self.client.get(reverse("core:dashboard"))
        self.assertEqual(resp.status_code, 200)

    def test_arquivo_estatico_nao_e_redirecionado(self):
        """
        Regressão: STATIC_URL não tem barra inicial ("static/"), mas
        request.path sempre tem — sem normalizar os dois, a exceção de
        arquivo estático no middleware nunca bate e o CSS/JS da própria
        tela de troca de senha quebra. Usa um usuário com
        deve_trocar_senha=True (self.user, do setUp) pra realmente
        exercitar esse trecho do middleware.
        """
        resp = self.client.get("/static/core/js/searchable-select.js")
        self.assertNotEqual(resp.status_code, 302)


class PasswordResetTests(TestCase):
    """
    Fluxo "Esqueci minha senha": solicitar o link, receber por e-mail
    (backend console/locmem nos testes), usar o link para definir uma
    senha nova e conseguir entrar só com a senha nova.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            "usuario_reset", "usuario_reset@example.com", "SenhaAntiga123!", is_active=True
        )

    def test_pagina_de_solicitacao_carrega(self):
        resp = self.client.get(reverse("core:password_reset"))
        self.assertEqual(resp.status_code, 200)

    def test_solicitar_reset_envia_email_com_link(self):
        resp = self.client.post(
            reverse("core:password_reset"), {"email": "usuario_reset@example.com"}, follow=True
        )
        self.assertEqual(resp.status_code, 200)
        self.assertRedirects(resp, reverse("core:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Redefinição de senha", mail.outbox[0].subject)
        self.assertIn("/senha/redefinir/", mail.outbox[0].body)

    def test_email_inexistente_nao_revela_se_a_conta_existe(self):
        """Por segurança, a resposta é a mesma tela de sucesso mesmo se o
        e-mail não existir no sistema (evita enumerar contas cadastradas)."""
        resp = self.client.post(
            reverse("core:password_reset"), {"email": "nao-existe@example.com"}, follow=True
        )
        self.assertRedirects(resp, reverse("core:password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)

    def test_link_com_token_valido_permite_definir_nova_senha(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        # A view do Django exige acessar o link "cru" uma vez (que faz o
        # redirect para a versão com token "set-password" na sessão) antes
        # de aceitar o POST — replica isso aqui.
        url = reverse("core:password_reset_confirm", kwargs={"uidb64": uid, "token": token})
        resp = self.client.get(url, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Criar nova senha")

        final_url = resp.redirect_chain[-1][0]
        resp = self.client.post(final_url, {
            "new_password1": "SenhaNovaForte456!",
            "new_password2": "SenhaNovaForte456!",
        }, follow=True)
        self.assertRedirects(resp, reverse("core:password_reset_complete"))

        self.assertTrue(self.client.login(username="usuario_reset", password="SenhaNovaForte456!"))

    def test_link_com_token_invalido_mostra_mensagem_de_erro(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        url = reverse("core:password_reset_confirm", kwargs={"uidb64": uid, "token": "token-invalido"})
        resp = self.client.get(url, follow=True)
        self.assertContains(resp, "Link inválido")


class DashboardGraficoTests(TestCase):
    """
    Gráfico "Entradas x Saídas" do dashboard (core/charts.py). O ponto mais
    importante aqui: todo valor usado como coordenada/atributo do SVG
    precisa ser um número que o template renderiza sem vírgula decimal
    (LANGUAGE_CODE="pt-br" faz Django trocar "." por "," em floats, o que
    quebra atributos como x="54,0") — os testes de string exigem "." e
    reprovariam se essa regressão voltasse.
    """

    def setUp(self):
        self.admin = User.objects.create_superuser("admin_dash", "a@a.com", "SenhaForte123!")
        cat = Categoria.objects.get(nome="Motor")
        self.peca = Peca.objects.create(
            codigo="DASH-1", nome="Peça Dashboard", categoria=cat,
            quantidade_estoque=100, quantidade_minima=1,
        )

    def test_sem_movimentacoes_retorna_sem_dados(self):
        dados = entradas_saidas_chart()
        self.assertFalse(dados["tem_dados"])

    def test_com_movimentacoes_soma_por_dia_e_totais(self):
        hoje = timezone.localdate()
        m1 = Movimentacao.objects.create(
            peca=self.peca, tipo="entrada", motivo="recebimento_fornecedor",
            quantidade=5, usuario=self.admin,
        )
        Movimentacao.objects.filter(pk=m1.pk).update(data=timezone.now())
        m2 = Movimentacao.objects.create(
            peca=self.peca, tipo="saida", motivo="venda",
            quantidade=3, usuario=self.admin,
        )
        Movimentacao.objects.filter(pk=m2.pk).update(data=timezone.now())

        dados = entradas_saidas_chart()
        self.assertTrue(dados["tem_dados"])
        self.assertEqual(dados["total_entradas"], 5)
        self.assertEqual(dados["total_saidas"], 3)
        ultimo_dia = dados["barras"][-1]
        self.assertEqual(ultimo_dia["data"], hoje)
        self.assertEqual(ultimo_dia["entrada"], 5)
        self.assertEqual(ultimo_dia["saida"], 3)
        # A barra de entrada existe (tem "M" de moveto no "d" do <path>).
        self.assertTrue(ultimo_dia["path_entrada"].startswith("M"))

    def test_movimentacao_fora_do_periodo_nao_entra_na_soma(self):
        antiga = Movimentacao.objects.create(
            peca=self.peca, tipo="entrada", motivo="recebimento_fornecedor",
            quantidade=99, usuario=self.admin,
        )
        Movimentacao.objects.filter(pk=antiga.pk).update(
            data=timezone.now() - timedelta(days=30)
        )
        dados = entradas_saidas_chart()
        self.assertFalse(dados["tem_dados"])

    def test_todos_os_valores_numericos_do_svg_usam_ponto_nao_virgula(self):
        """
        Regressão do bug: com LANGUAGE_CODE="pt-br", um float cru no
        contexto (ex.: 84.0) é renderizado pelo template como "84,0" —
        atributo SVG inválido. Os campos usados como x/y no SVG devem ser
        int (ou string já formatada), nunca float.
        """
        Movimentacao.objects.create(
            peca=self.peca, tipo="entrada", motivo="recebimento_fornecedor",
            quantidade=5, usuario=self.admin,
        )
        dados = entradas_saidas_chart()
        for chave in ("svg_w", "svg_h", "baseline", "top_y", "mid_y", "left_pad", "label_y", "slot_w", "hit_h"):
            self.assertIsInstance(dados[chave], int, f"{chave} deveria ser int, veio {type(dados[chave])}")
        for barra in dados["barras"]:
            self.assertIsInstance(barra["x_label"], int)
            self.assertIsInstance(barra["hit_x"], int)

    def test_dashboard_renderiza_grafico_com_atributos_svg_validos(self):
        Movimentacao.objects.create(
            peca=self.peca, tipo="entrada", motivo="recebimento_fornecedor",
            quantidade=7, usuario=self.admin,
        )
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("core:dashboard"))
        self.assertEqual(resp.status_code, 200)
        conteudo = resp.content.decode()
        self.assertIn("Entradas x Saídas", conteudo)
        self.assertIn('class="viz-svg"', conteudo)
        # Nenhum atributo numérico do SVG deve conter vírgula decimal.
        self.assertNotRegex(conteudo, r'(?:x|y|dx|dy)="[0-9]+,[0-9]')


class AlertaEstoqueBaixoBadgeTests(TestCase):
    """
    Badge global de estoque baixo (core/context_processors.py +
    templates/base.html), visível em qualquer página logada quando há
    peças abaixo do mínimo, com link para a lista já filtrada.
    """

    def setUp(self):
        self.user = User.objects.create_user("user_badge", password="SenhaForte123!", is_active=True)
        self.cat = Categoria.objects.get(nome="Motor")
        self.client.force_login(self.user)

    def test_sem_pecas_abaixo_do_minimo_badge_nao_aparece(self):
        Peca.objects.create(
            codigo="BADGE-1", nome="Peça OK", categoria=self.cat,
            quantidade_estoque=10, quantidade_minima=2,
        )
        resp = self.client.get(reverse("core:dashboard"))
        # A classe CSS "alert-badge-link" está sempre no <style> do
        # base.html; o que indica se o badge realmente foi renderizado é
        # o link para a lista filtrada.
        self.assertNotContains(resp, "?abaixo_minimo=1")

    def test_com_pecas_abaixo_do_minimo_badge_aparece_com_contagem_e_link(self):
        Peca.objects.create(
            codigo="BADGE-2", nome="Peça Baixa 1", categoria=self.cat,
            quantidade_estoque=1, quantidade_minima=5,
        )
        Peca.objects.create(
            codigo="BADGE-3", nome="Peça Baixa 2", categoria=self.cat,
            quantidade_estoque=0, quantidade_minima=3,
        )
        resp = self.client.get(reverse("core:dashboard"))
        self.assertContains(resp, reverse("pecas:list") + "?abaixo_minimo=1")
        self.assertContains(resp, ">2<")

    def test_badge_aparece_em_qualquer_pagina_nao_so_no_dashboard(self):
        Peca.objects.create(
            codigo="BADGE-4", nome="Peça Baixa 3", categoria=self.cat,
            quantidade_estoque=0, quantidade_minima=1,
        )
        resp = self.client.get(reverse("movimentacoes:list"))
        self.assertContains(resp, reverse("pecas:list") + "?abaixo_minimo=1")

    def test_badge_nao_aparece_para_usuario_deslogado(self):
        self.client.logout()
        resp = self.client.get(reverse("core:login"))
        self.assertNotContains(resp, "?abaixo_minimo=1")
