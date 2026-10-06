from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404

from .models import Fornecedor
from .forms import FornecedorForm, HistoricoCompraForm


@login_required
def fornecedor_list(request):
    fornecedores = Fornecedor.objects.all()
    paginator = Paginator(fornecedores, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "fornecedores/fornecedor_list.html", {
        "fornecedores": page_obj, "page_obj": page_obj,
    })


@login_required
def fornecedor_form(request, pk=None):
    obj = get_object_or_404(Fornecedor, pk=pk) if pk else None
    if request.method == "POST":
        form = FornecedorForm(request.POST, instance=obj)
        if form.is_valid():
            fornecedor = form.save()
            messages.success(request, "Fornecedor salvo com sucesso.")
            if not obj:
                return redirect("fornecedores:editar", pk=fornecedor.pk)
            return redirect("fornecedores:list")
    else:
        form = FornecedorForm(instance=obj)

    historico = obj.historico.select_related("peca").all() if obj else []
    return render(request, "fornecedores/fornecedor_form.html", {
        "form": form, "fornecedor": obj, "historico": historico,
    })


@login_required
def historico_novo(request, fornecedor_id):
    fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_id)
    if request.method == "POST":
        form = HistoricoCompraForm(request.POST)
        if form.is_valid():
            historico = form.save(commit=False)
            historico.fornecedor = fornecedor
            historico.save()
            messages.success(request, "Registro de compra/cotação adicionado.")
            return redirect("fornecedores:editar", pk=fornecedor.pk)
    else:
        form = HistoricoCompraForm()
    return render(request, "fornecedores/historico_form.html", {
        "form": form, "fornecedor": fornecedor,
    })
