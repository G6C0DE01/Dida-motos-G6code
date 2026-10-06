import csv
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F, Q
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from pecas.models import Peca, Categoria
from movimentacoes.models import Movimentacao


def _csv_response(filename, header, rows):
    """
    Gera a resposta de download CSV usada por todos os relatórios (botão
    "Exportar CSV"). BOM + delimitador ";" para abrir certinho, com
    acentos, no Excel em português.
    """
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("﻿")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(header)
    writer.writerows(rows)
    return response


@login_required
def estoque_por_categoria(request):
    """Estoque por categoria (quantidade e valor de custo)."""
    categorias = (
        Categoria.objects.annotate(
            total_itens=Sum("pecas__quantidade_estoque"),
            total_pecas_cadastradas=Count("pecas"),
        ).order_by("nome")
    )
    # valor de custo por categoria não dá para fazer só com annotate porque
    # é quantidade * preço (dois campos), então calculamos em Python.
    dados = []
    for cat in categorias:
        pecas = cat.pecas.filter(ativo=True)
        valor_custo = sum(p.valor_total_estoque for p in pecas)
        dados.append({
            "categoria": cat,
            "total_itens": cat.total_itens or 0,
            "total_pecas_cadastradas": cat.total_pecas_cadastradas,
            "valor_custo": valor_custo,
        })

    if request.GET.get("export") == "csv":
        return _csv_response(
            "estoque_por_categoria.csv",
            ["Categoria", "Peças cadastradas", "Itens em estoque", "Valor de custo (R$)"],
            [
                [d["categoria"].nome, d["total_pecas_cadastradas"], d["total_itens"], f'{d["valor_custo"]:.2f}']
                for d in dados
            ],
        )
    return render(request, "relatorios/estoque_por_categoria.html", {"dados": dados})


@login_required
def pecas_em_falta(request):
    """Peças com estoque abaixo (ou igual a zero) do mínimo cadastrado."""
    pecas = (
        Peca.objects.filter(ativo=True, quantidade_estoque__lt=F("quantidade_minima"))
        .select_related("categoria", "fabricante")
        .order_by("quantidade_estoque")
    )

    if request.GET.get("export") == "csv":
        return _csv_response(
            "pecas_em_falta.csv",
            ["Código", "Nome", "Categoria", "Fabricante", "Estoque", "Mínimo"],
            [
                [p.codigo, p.nome, p.categoria.nome, p.fabricante.nome if p.fabricante else "-",
                 p.quantidade_estoque, p.quantidade_minima]
                for p in pecas
            ],
        )
    return render(request, "relatorios/pecas_em_falta.html", {"pecas": pecas})


@login_required
def pecas_paradas(request, dias=60):
    """Peças sem nenhuma movimentação nos últimos `dias` dias."""
    limite = timezone.now() - timedelta(days=dias)
    pecas = (
        Peca.objects.filter(ativo=True)
        .filter(
            Q(movimentacoes__isnull=True) |
            ~Q(movimentacoes__data__gte=limite)
        )
        .distinct()
        .select_related("categoria")
        .order_by("nome")
    )

    if request.GET.get("export") == "csv":
        return _csv_response(
            f"pecas_paradas_{dias}dias.csv",
            ["Código", "Nome", "Categoria", "Estoque atual"],
            [[p.codigo, p.nome, p.categoria.nome, p.quantidade_estoque] for p in pecas],
        )
    return render(request, "relatorios/pecas_paradas.html", {"pecas": pecas, "dias": dias})


@login_required
def custo_total_estoque(request):
    """Custo total do estoque, geral e por categoria."""
    pecas = Peca.objects.filter(ativo=True).select_related("categoria")
    total = sum(p.valor_total_estoque for p in pecas)

    if request.GET.get("export") == "csv":
        return _csv_response(
            "custo_total_estoque.csv",
            ["Código", "Nome", "Categoria", "Quantidade", "Preço de custo (R$)", "Valor total (R$)"],
            [
                [p.codigo, p.nome, p.categoria.nome, p.quantidade_estoque,
                 f"{p.preco_custo:.2f}", f"{p.valor_total_estoque:.2f}"]
                for p in pecas
            ],
        )
    return render(request, "relatorios/custo_total_estoque.html", {"total": total, "pecas": pecas})


@login_required
def rotatividade_pecas(request, dias=30):
    """
    Rotatividade: total de unidades que saíram (venda/uso em reparo) de
    cada peça nos últimos `dias` dias — ajuda a identificar as peças de
    maior giro.
    """
    limite = timezone.now() - timedelta(days=dias)
    ranking = (
        Movimentacao.objects.filter(tipo=Movimentacao.Tipo.SAIDA, data__gte=limite)
        .values("peca__id", "peca__codigo", "peca__nome")
        .annotate(total_saida=Sum("quantidade"))
        .order_by("-total_saida")
    )

    if request.GET.get("export") == "csv":
        return _csv_response(
            f"rotatividade_{dias}dias.csv",
            ["Código", "Nome", f"Total de saída ({dias} dias)"],
            [[r["peca__codigo"], r["peca__nome"], r["total_saida"]] for r in ranking],
        )
    return render(request, "relatorios/rotatividade.html", {"ranking": ranking, "dias": dias})


@login_required
def previsao_falta(request, dias_analise=30):
    """
    Previsão simples de quando cada peça vai atingir o mínimo, baseada no
    consumo médio diário dos últimos `dias_analise` dias (saídas / dias).
    Peças sem consumo no período não entram na lista (não há como prever).
    """
    limite = timezone.now() - timedelta(days=dias_analise)
    consumo = (
        Movimentacao.objects.filter(tipo=Movimentacao.Tipo.SAIDA, data__gte=limite)
        .values("peca")
        .annotate(total_saida=Sum("quantidade"))
    )
    consumo_por_peca = {c["peca"]: c["total_saida"] for c in consumo}

    previsoes = []
    for peca in Peca.objects.filter(ativo=True, id__in=consumo_por_peca.keys()):
        total_saida = consumo_por_peca[peca.id]
        consumo_medio_dia = total_saida / dias_analise
        if consumo_medio_dia <= 0:
            continue
        unidades_ate_minimo = max(peca.quantidade_estoque - peca.quantidade_minima, 0)
        dias_para_minimo = round(unidades_ate_minimo / consumo_medio_dia, 1)
        previsoes.append({
            "peca": peca,
            "consumo_medio_dia": round(consumo_medio_dia, 2),
            "dias_para_minimo": dias_para_minimo,
        })
    previsoes.sort(key=lambda p: p["dias_para_minimo"])

    if request.GET.get("export") == "csv":
        return _csv_response(
            "previsao_falta.csv",
            ["Código", "Nome", "Consumo médio/dia", "Dias até o mínimo"],
            [
                [p["peca"].codigo, p["peca"].nome, p["consumo_medio_dia"], p["dias_para_minimo"]]
                for p in previsoes
            ],
        )
    return render(
        request, "relatorios/previsao_falta.html",
        {"previsoes": previsoes, "dias_analise": dias_analise},
    )
