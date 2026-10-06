from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from .models import Cliente, Motocicleta, OrdemServico
from .forms import (
    ClienteForm, MotocicletaForm, MotocicletaComClienteForm,
    OrdemServicoForm, ItemOrdemServicoFormSet,
)
from .validators import apenas_digitos


@login_required
def os_list(request):
    ordens = OrdemServico.objects.select_related("cliente", "motocicleta", "mecanico").all()
    status = request.GET.get("status", "")
    if status:
        ordens = ordens.filter(status=status)

    paginator = Paginator(ordens, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "ordens": page_obj,
        "page_obj": page_obj,
        "status": status,
        "status_choices": OrdemServico.Status.choices,
    }
    return render(request, "ordens_servico/os_list.html", context)


@login_required
def os_form(request, pk=None):
    os_obj = get_object_or_404(OrdemServico, pk=pk) if pk else None

    if request.method == "POST":
        form = OrdemServicoForm(request.POST, instance=os_obj)
        formset = ItemOrdemServicoFormSet(request.POST, instance=os_obj)
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    novo_os = form.save()
                    formset.instance = novo_os
                    # commit=False: dá controle para setar o usuário em cada
                    # item (usado na Movimentacao gerada automaticamente) e
                    # para capturar erro de validação (ex.: estoque
                    # insuficiente) antes de qualquer coisa ser persistida.
                    itens = formset.save(commit=False)
                    for item in itens:
                        item._usuario_evento = request.user
                        item.full_clean()
                        item.save()
                    for obj in formset.deleted_objects:
                        obj.delete()
            except ValidationError as e:
                for msg in e.messages:
                    form.add_error(None, msg)
            else:
                os_obj = novo_os
                messages.success(request, f"Ordem de serviço {os_obj.numero} salva com sucesso.")
                return redirect("ordens_servico:list")
    else:
        form = OrdemServicoForm(instance=os_obj)
        formset = ItemOrdemServicoFormSet(instance=os_obj)

    return render(request, "ordens_servico/os_form.html", {
        "form": form, "formset": formset, "os_obj": os_obj,
    })


# --- Clientes e motocicletas ---

@login_required
def cliente_list(request):
    clientes = Cliente.objects.prefetch_related("motocicletas").all()
    paginator = Paginator(clientes, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "ordens_servico/cliente_list.html", {
        "clientes": page_obj, "page_obj": page_obj,
    })


@login_required
def cliente_form(request, pk=None):
    obj = get_object_or_404(Cliente, pk=pk) if pk else None
    if request.method == "POST":
        form = ClienteForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Cliente salvo com sucesso.")
            return redirect("ordens_servico:cliente_list")
    else:
        form = ClienteForm(instance=obj)
    return render(request, "ordens_servico/cliente_form.html", {"form": form})


@login_required
def motocicleta_form(request, pk=None):
    obj = get_object_or_404(Motocicleta, pk=pk) if pk else None

    if obj:
        # Edição: o cliente já está definido, formulário simples de sempre.
        if request.method == "POST":
            form = MotocicletaForm(request.POST, instance=obj)
            if form.is_valid():
                form.save()
                messages.success(request, "Veículo salvo com sucesso.")
                return redirect("ordens_servico:cliente_list")
        else:
            form = MotocicletaForm(instance=obj)
        return render(request, "ordens_servico/motocicleta_form.html", {"form": form, "obj": obj})

    # Cadastro novo: o veículo é a prioridade (placa/marca/modelo primeiro);
    # o cliente é resolvido em seguida (reaproveitando um já cadastrado ou
    # criando um novo com os dados básicos), ver MotocicletaComClienteForm.
    if request.method == "POST":
        form = MotocicletaComClienteForm(request.POST)
        if form.is_valid():
            cliente = form.resolver_cliente()
            Motocicleta.objects.create(
                cliente=cliente,
                placa=form.cleaned_data.get("placa", ""),
                marca=form.cleaned_data["marca"],
                modelo=form.cleaned_data["modelo"],
                ano=form.cleaned_data.get("ano"),
            )
            messages.success(request, f"Veículo cadastrado para {cliente.nome}.")
            return redirect("ordens_servico:cliente_list")
    else:
        form = MotocicletaComClienteForm()
    return render(request, "ordens_servico/motocicleta_form.html", {"form": form, "obj": None})


@login_required
def cliente_buscar_cpf(request):
    """
    Endpoint JSON usado pelo cadastro de veículo para autopreencher os
    dados de um cliente já existente a partir do CPF digitado — evita
    cadastro duplicado quando um cliente antigo traz outra moto.
    """
    cpf = apenas_digitos(request.GET.get("cpf", ""))
    if len(cpf) != 11:
        return JsonResponse({"encontrado": False})
    cliente = Cliente.objects.filter(cpf=cpf).first()
    if not cliente:
        return JsonResponse({"encontrado": False})
    return JsonResponse({
        "encontrado": True,
        "id": cliente.pk,
        "nome": cliente.nome,
        "telefone": cliente.telefone,
    })
