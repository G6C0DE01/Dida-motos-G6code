from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.db.models import Sum, F
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from pecas.models import Peca
from movimentacoes.models import Movimentacao
from ordens_servico.models import OrdemServico

from .charts import entradas_saidas_chart
from .decorators import gerente_required
from .forms import FuncionarioForm
from .models import PerfilUsuario


@login_required
def dashboard(request):
    """
    Tela inicial (Dashboard) equivalente à primeira tela do protótipo:
    KPIs gerais, alertas de estoque baixo, movimentações recentes e
    ordens de serviço abertas.
    """
    hoje = timezone.localdate()

    pecas_qs = Peca.objects.filter(ativo=True)
    total_itens_estoque = pecas_qs.aggregate(total=Sum("quantidade_estoque"))["total"] or 0
    total_categorias = pecas_qs.values("categoria").distinct().count()

    pecas_abaixo_minimo = pecas_qs.filter(
        quantidade_estoque__lt=F("quantidade_minima")
    ).select_related("categoria").order_by("quantidade_estoque")

    valor_total_estoque = sum(p.valor_total_estoque for p in pecas_qs)

    os_abertas_hoje = OrdemServico.objects.filter(data_abertura__date=hoje)
    os_em_andamento = os_abertas_hoje.filter(status=OrdemServico.Status.EM_ANDAMENTO).count()

    movimentacoes_recentes = (
        Movimentacao.objects.select_related("peca", "usuario").order_by("-data")[:5]
    )

    ordens_abertas = (
        OrdemServico.objects.exclude(status=OrdemServico.Status.ENTREGUE)
        .select_related("cliente", "motocicleta", "mecanico")
        .order_by("-data_abertura")[:10]
    )

    context = {
        "total_itens_estoque": total_itens_estoque,
        "total_categorias": total_categorias,
        "pecas_abaixo_minimo": pecas_abaixo_minimo,
        "qtd_pecas_abaixo_minimo": pecas_abaixo_minimo.count(),
        "valor_total_estoque": valor_total_estoque,
        "os_abertas_hoje": os_abertas_hoje.count(),
        "os_em_andamento": os_em_andamento,
        "movimentacoes_recentes": movimentacoes_recentes,
        "ordens_abertas": ordens_abertas,
        "grafico": entradas_saidas_chart(),
    }
    return render(request, "core/dashboard.html", context)


@login_required
def trocar_senha(request):
    """
    Troca de senha obrigatória: para onde o ForcarTrocaSenhaMiddleware
    redireciona enquanto perfil.deve_trocar_senha=True (conta recém
    criada pelo admin com senha temporária). Também funciona como troca
    de senha "normal" pra quem acessar por vontade própria.
    """
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # mantém a sessão logada após trocar a senha
            perfil, _ = PerfilUsuario.objects.get_or_create(user=user)
            if perfil.deve_trocar_senha:
                perfil.deve_trocar_senha = False
                perfil.save(update_fields=["deve_trocar_senha"])
            messages.success(request, "Senha alterada com sucesso.")
            return redirect("core:dashboard")
    else:
        form = PasswordChangeForm(request.user)

    precisa_trocar = bool(getattr(request.user, "perfil", None) and request.user.perfil.deve_trocar_senha)
    return render(request, "core/trocar_senha.html", {"form": form, "precisa_trocar": precisa_trocar})


@gerente_required
def funcionario_list(request):
    """Lista de funcionários com ação de revogar/reativar acesso — substitui a necessidade do Django Admin."""
    funcionarios = User.objects.exclude(is_superuser=True).order_by("first_name", "username")
    return render(request, "core/funcionario_list.html", {"funcionarios": funcionarios})


@gerente_required
def funcionario_form(request):
    """
    Cadastro de funcionário pelo admin/gerente (substitui o autocadastro
    público): gera usuário e senha temporária automaticamente e mostra
    as credenciais uma única vez, para repassar ao novo funcionário.
    """
    credenciais = None
    if request.method == "POST":
        form = FuncionarioForm(request.POST)
        if form.is_valid():
            credenciais = form.salvar()
            messages.success(request, "Funcionário cadastrado com sucesso.")
            form = FuncionarioForm()
    else:
        form = FuncionarioForm()
    return render(request, "core/funcionario_form.html", {"form": form, "credenciais": credenciais})


@require_POST
@gerente_required
def funcionario_alternar_acesso(request, pk):
    """Ativa/desativa o acesso de um funcionário — substitui as ações "Aprovar"/"Revogar" do Django Admin."""
    funcionario = get_object_or_404(User, pk=pk)
    if funcionario == request.user:
        messages.error(request, "Você não pode alterar o próprio acesso.")
    else:
        funcionario.is_active = not funcionario.is_active
        funcionario.save(update_fields=["is_active"])
        acao = "reativado" if funcionario.is_active else "revogado"
        messages.success(request, f"Acesso de {funcionario.first_name or funcionario.username} {acao}.")
    return redirect("core:funcionario_list")
