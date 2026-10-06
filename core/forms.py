from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group


class FuncionarioForm(forms.Form):
    """
    Cadastro de funcionário — só o gerente/admin preenche (ver
    core.decorators.gerente_required), substituindo o autocadastro
    público de antes. Sem e-mail (não é usado no sistema) e sem pedir
    pra escolher usuário/senha: o sistema gera os dois automaticamente
    (core.utils.gerar_username / gerar_senha_temporaria), com senha
    temporária que precisa ser trocada no primeiro login.
    """
    nome = forms.CharField(label="Nome completo", max_length=150)
    grupo = forms.ChoiceField(
        label="Função",
        choices=[("Gerentes", "Gerente"), ("Mecânicos", "Mecânico")],
        initial="Mecânicos",
    )

    def clean_nome(self):
        nome = self.cleaned_data["nome"].strip()
        if not nome:
            raise forms.ValidationError("Informe o nome completo.")
        return nome

    def salvar(self):
        from django.contrib.auth.models import User
        from .models import PerfilUsuario
        from .utils import gerar_senha_temporaria, gerar_username

        nome = self.cleaned_data["nome"]
        username = gerar_username(nome)
        senha = gerar_senha_temporaria()

        user = User.objects.create_user(username=username, password=senha)
        user.first_name = nome
        user.is_active = True
        user.save()

        grupo, _ = Group.objects.get_or_create(name=self.cleaned_data["grupo"])
        user.groups.add(grupo)

        PerfilUsuario.objects.create(user=user, deve_trocar_senha=True)

        return {"username": username, "senha": senha, "nome": nome}


class LoginForm(AuthenticationForm):
    """
    Formulário de login que avisa de forma clara quando a conta está
    desativada (is_active=False) — hoje isso só acontece quando um
    gerente revoga o acesso de alguém em core.views.funcionario_list.

    O ModelBackend padrão do Django já filtra usuários inativos dentro
    de authenticate() (via user_can_authenticate), então nesse caso
    confirm_login_allowed() nunca chega a ser chamado e o usuário só
    veria o erro genérico de "usuário/senha incorretos". Por isso aqui
    a senha é conferida manualmente antes, só para poder distinguir
    "conta desativada" de "usuário ou senha incorretos".
    """

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username is not None and password:
            UserModel = get_user_model()
            try:
                candidato = UserModel._default_manager.get_by_natural_key(username)
            except UserModel.DoesNotExist:
                candidato = None

            if candidato is not None and candidato.check_password(password) and not candidato.is_active:
                raise forms.ValidationError(
                    "Sua conta está desativada. Fale com um administrador para reativar o acesso.",
                    code="inactive",
                )

            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data
