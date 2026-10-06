from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from .models import Peca, Categoria, Fabricante, ModeloMoto, Localizacao
from .forms import PecaForm, CategoriaForm, FabricanteForm, ModeloMotoForm, LocalizacaoForm


@login_required
def peca_list(request):
    pecas = Peca.objects.select_related("categoria", "fabricante").all()

    busca = request.GET.get("busca", "").strip()
    categoria_id = request.GET.get("categoria", "")
    apenas_abaixo_minimo = request.GET.get("abaixo_minimo") == "1"

    if busca:
        pecas = pecas.filter(Q(codigo__icontains=busca) | Q(nome__icontains=busca))
    if categoria_id:
        pecas = pecas.filter(categoria_id=categoria_id)
    if apenas_abaixo_minimo:
        pecas = [p for p in pecas if p.abaixo_do_minimo]

    paginator = Paginator(pecas, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "pecas": page_obj,
        "page_obj": page_obj,
        "categorias": Categoria.objects.all(),
        "busca": busca,
        "categoria_id": categoria_id,
        "apenas_abaixo_minimo": apenas_abaixo_minimo,
    }
    return render(request, "pecas/peca_list.html", context)


@login_required
def peca_form(request, pk=None):
    peca = get_object_or_404(Peca, pk=pk) if pk else None
    if request.method == "POST":
        form = PecaForm(request.POST, instance=peca)
        if form.is_valid():
            form.save()
            messages.success(request, f"Peça \"{form.instance.nome}\" salva com sucesso.")
            return redirect("pecas:list")
    else:
        form = PecaForm(instance=peca)
    return render(request, "pecas/peca_form.html", {"form": form, "peca": peca})


@login_required
def peca_toggle_ativo(request, pk):
    peca = get_object_or_404(Peca, pk=pk)
    peca.ativo = not peca.ativo
    peca.save(update_fields=["ativo"])
    messages.success(
        request,
        f"Peça \"{peca.nome}\" {'ativada' if peca.ativo else 'desativada'}."
    )
    return redirect("pecas:list")


# --- Cadastros auxiliares (categoria, fabricante, modelo de moto, localização) ---
#
# Os formulários de fabricante, modelo de moto e localização também podem
# ser abertos em popup (?popup=1&field=<nome_do_campo>) a partir do próprio
# formulário de Peça, através do botão "+" ao lado do campo — assim dá para
# cadastrar um fabricante/localização/modelo novo sem sair da tela e sem
# precisar do admin do Django. Ao salvar em modo popup, a janela se fecha
# sozinha e avisa a tela que abriu (via postMessage) para adicionar a nova
# opção no <select> correspondente.

def _popup_response(request, obj):
    field = request.GET.get("field", "")
    return render(request, "pecas/_popup_close.html", {
        "obj_id": obj.pk,
        "obj_label": str(obj),
        "field": field,
    })

@login_required
def categoria_list(request):
    return render(request, "pecas/auxiliares_list.html", {
        "titulo": "Categorias",
        "itens": Categoria.objects.all(),
        "url_novo": "pecas:categoria_novo",
        "url_editar": "pecas:categoria_editar",
    })


@login_required
def categoria_form(request, pk=None):
    obj = get_object_or_404(Categoria, pk=pk) if pk else None
    if request.method == "POST":
        form = CategoriaForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoria salva com sucesso.")
            return redirect("pecas:categoria_list")
    else:
        form = CategoriaForm(instance=obj)
    return render(request, "pecas/auxiliar_form.html", {"form": form, "titulo": "Categoria"})


@login_required
def fabricante_list(request):
    return render(request, "pecas/auxiliares_list.html", {
        "titulo": "Fabricantes",
        "itens": Fabricante.objects.all(),
        "url_novo": "pecas:fabricante_novo",
        "url_editar": "pecas:fabricante_editar",
    })


@login_required
def fabricante_form(request, pk=None):
    obj = get_object_or_404(Fabricante, pk=pk) if pk else None
    is_popup = request.GET.get("popup") == "1"
    if request.method == "POST":
        form = FabricanteForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            if is_popup:
                return _popup_response(request, form.instance)
            messages.success(request, "Fabricante salvo com sucesso.")
            return redirect("pecas:fabricante_list")
    else:
        form = FabricanteForm(instance=obj)
    template = "pecas/auxiliar_form_popup.html" if is_popup else "pecas/auxiliar_form.html"
    return render(request, template, {"form": form, "titulo": "Fabricante"})


@login_required
def modelo_moto_list(request):
    return render(request, "pecas/auxiliares_list.html", {
        "titulo": "Modelos de Moto",
        "itens": ModeloMoto.objects.all(),
        "url_novo": "pecas:modelo_novo",
        "url_editar": "pecas:modelo_editar",
    })


@login_required
def modelo_moto_form(request, pk=None):
    obj = get_object_or_404(ModeloMoto, pk=pk) if pk else None
    is_popup = request.GET.get("popup") == "1"
    if request.method == "POST":
        form = ModeloMotoForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            if is_popup:
                return _popup_response(request, form.instance)
            messages.success(request, "Modelo de moto salvo com sucesso.")
            return redirect("pecas:modelo_list")
    else:
        form = ModeloMotoForm(instance=obj)
    template = "pecas/auxiliar_form_popup.html" if is_popup else "pecas/auxiliar_form.html"
    return render(request, template, {"form": form, "titulo": "Modelo de Moto"})


@login_required
def localizacao_list(request):
    return render(request, "pecas/auxiliares_list.html", {
        "titulo": "Localizações",
        "itens": Localizacao.objects.all(),
        "url_novo": "pecas:localizacao_novo",
        "url_editar": "pecas:localizacao_editar",
    })


@login_required
def localizacao_form(request, pk=None):
    obj = get_object_or_404(Localizacao, pk=pk) if pk else None
    is_popup = request.GET.get("popup") == "1"
    if request.method == "POST":
        form = LocalizacaoForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            if is_popup:
                return _popup_response(request, form.instance)
            messages.success(request, "Localização salva com sucesso.")
            return redirect("pecas:localizacao_list")
    else:
        form = LocalizacaoForm(instance=obj)
    template = "pecas/auxiliar_form_popup.html" if is_popup else "pecas/auxiliar_form.html"
    return render(request, template, {"form": form, "titulo": "Localização"})
