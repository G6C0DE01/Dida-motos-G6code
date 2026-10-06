from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404

from core.decorators import gerente_required

from .models import Movimentacao
from .forms import MovimentacaoForm


@login_required
def movimentacao_list(request):
    movimentacoes = Movimentacao.objects.select_related("peca", "usuario", "ordem_servico").all()

    tipo = request.GET.get("tipo", "")
    busca = request.GET.get("busca", "").strip()
    if tipo:
        movimentacoes = movimentacoes.filter(tipo=tipo)
    if busca:
        movimentacoes = movimentacoes.filter(peca__nome__icontains=busca)

    paginator = Paginator(movimentacoes, 30)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "movimentacoes": page_obj,
        "page_obj": page_obj,
        "tipo": tipo,
        "busca": busca,
        "tipos": Movimentacao.Tipo.choices,
    }
    return render(request, "movimentacoes/movimentacao_list.html", context)


@login_required
def movimentacao_form(request, pk=None):
    """Cria uma nova movimentação (pk=None) ou edita uma existente."""
    movimentacao = get_object_or_404(Movimentacao, pk=pk) if pk else None

    if request.method == "POST":
        form = MovimentacaoForm(request.POST, instance=movimentacao)
        if form.is_valid():
            obj = form.save(commit=False)
            if movimentacao is None:
                obj.usuario = request.user
            try:
                obj.full_clean()
                obj.save()
            except ValidationError as e:
                for msg in e.messages:
                    form.add_error(None, msg)
            else:
                messages.success(
                    request,
                    "Movimentação atualizada com sucesso." if movimentacao
                    else "Movimentação registrada com sucesso."
                )
                return redirect("movimentacoes:list")
    else:
        form = MovimentacaoForm(instance=movimentacao)

    return render(request, "movimentacoes/movimentacao_form.html", {
        "form": form,
        "movimentacao": movimentacao,
    })


@gerente_required
def movimentacao_excluir(request, pk):
    movimentacao = get_object_or_404(Movimentacao, pk=pk)
    if request.method == "POST":
        try:
            movimentacao.delete()
        except ValidationError as e:
            messages.error(request, " ".join(e.messages))
        else:
            messages.success(request, "Movimentação excluída e o estoque foi ajustado de volta.")
    return redirect("movimentacoes:list")
