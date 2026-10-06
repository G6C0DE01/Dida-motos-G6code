"""
Gera os dados prontos para o gráfico "Entradas x Saídas" do dashboard.

O SVG é montado inteiramente aqui (server-side, sem biblioteca de
gráficos): a view calcula posições, alturas e o "d" de cada barra, e o
template só interpola esses valores. JavaScript só entra depois, para a
camada de interação (tooltip ao passar o mouse) — sem ele, o gráfico já
aparece completo, e a tabela em texto (sempre presente, dentro de um
<details>) garante que os mesmos números continuam acessíveis.

Paleta: duas cores categóricas (Entradas / Saídas) validadas com o
script de acessibilidade do skill de dataviz (CVD deuteranopia/protanopia
e contraste) — não o verde/vermelho usados nos badges do app, que falham
a checagem de separação para daltonismo (vermelho-verde é justamente o
par mais comum de se confundir). Ver core/static.../dashboard não existe;
as cores estão como custom properties no próprio template.
"""
import math
from datetime import timedelta

from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from movimentacoes.models import Movimentacao

# Layout do SVG (unidades do viewBox, não pixels de tela — o <svg> escala
# via CSS width:100%).
_SLOT_W = 40          # largura reservada para cada dia (par de barras + respiro)
_BAR_W = 15            # largura de cada barra (<= 24px do spec)
_BAR_GAP = 2           # respiro (surface gap) entre as duas barras do mesmo dia
_TOP_PAD = 14          # espaço acima da barra mais alta
_BARS_H = 140          # altura útil das barras (do topo até a baseline)
_BOTTOM_PAD = 28       # espaço para o rótulo do eixo X
_LEFT_PAD = 34         # espaço para os rótulos do eixo Y


def _nice_ceiling(value):
    """Arredonda `value` para cima até um número "redondo" (1/2/5 x 10^n),
    para os rótulos do eixo Y saírem limpos (0, 25, 50... e não 0, 23, 46...)."""
    if value <= 0:
        return 5
    exp = math.floor(math.log10(value))
    frac = value / (10 ** exp)
    if frac <= 1:
        nice = 1
    elif frac <= 2:
        nice = 2
    elif frac <= 5:
        nice = 5
    else:
        nice = 10
    return int(nice * (10 ** exp))


def _bar_path(x, width, height, baseline, radius=4):
    """
    Caminho SVG de uma barra com topo arredondado e base quadrada (spec:
    "4px rounded data-end, square at the baseline"). Um <rect> com rx
    arredondaria os 4 cantos; por isso é desenhado como <path>.
    """
    if height <= 0:
        return ""
    r = min(radius, height / 2, width / 2)
    top = baseline - height
    x0, x1 = x, x + width
    return (
        f"M{x0:.1f},{baseline:.1f} "
        f"L{x0:.1f},{top + r:.1f} "
        f"Q{x0:.1f},{top:.1f} {x0 + r:.1f},{top:.1f} "
        f"L{x1 - r:.1f},{top:.1f} "
        f"Q{x1:.1f},{top:.1f} {x1:.1f},{top + r:.1f} "
        f"L{x1:.1f},{baseline:.1f} "
        f"Z"
    )


def entradas_saidas_chart(dias=14):
    """Retorna o dicionário de contexto para o gráfico de Entradas x Saídas
    dos últimos `dias` dias (incluindo hoje)."""
    hoje = timezone.localdate()
    inicio = hoje - timedelta(days=dias - 1)

    totais = (
        Movimentacao.objects
        .filter(
            tipo__in=[Movimentacao.Tipo.ENTRADA, Movimentacao.Tipo.SAIDA],
            data__date__gte=inicio,
        )
        .annotate(dia=TruncDate("data"))
        .values("dia", "tipo")
        .annotate(total=Sum("quantidade"))
    )
    por_dia = {}
    for row in totais:
        por_dia.setdefault(row["dia"], {}).update({row["tipo"]: row["total"]})

    dias_lista = [inicio + timedelta(days=i) for i in range(dias)]
    valores = [
        {
            "data": d,
            "entrada": por_dia.get(d, {}).get(Movimentacao.Tipo.ENTRADA, 0),
            "saida": por_dia.get(d, {}).get(Movimentacao.Tipo.SAIDA, 0),
        }
        for d in dias_lista
    ]

    total_entradas = sum(v["entrada"] for v in valores)
    total_saidas = sum(v["saida"] for v in valores)

    if total_entradas == 0 and total_saidas == 0:
        return {"tem_dados": False, "dias": dias}

    maior_valor = max(max(v["entrada"], v["saida"]) for v in valores)
    teto = _nice_ceiling(maior_valor)
    baseline = _TOP_PAD + _BARS_H

    largura_total = _LEFT_PAD + len(valores) * _SLOT_W + 8
    altura_total = _TOP_PAD + _BARS_H + _BOTTOM_PAD

    barras = []
    for i, v in enumerate(valores):
        slot_x = _LEFT_PAD + i * _SLOT_W
        par_w = _BAR_W * 2 + _BAR_GAP
        offset = (_SLOT_W - par_w) / 2
        x_entrada = slot_x + offset
        x_saida = x_entrada + _BAR_W + _BAR_GAP
        # ints puros nos atributos SVG (ver comentário em "mid_y" acima).
        x_label_pos = slot_x + _SLOT_W // 2

        h_entrada = (v["entrada"] / teto) * _BARS_H if teto else 0
        h_saida = (v["saida"] / teto) * _BARS_H if teto else 0

        # Só mostra o dia (ex.: "18/09") a cada poucos rótulos, para não
        # amontoar texto em 14+ colunas — o valor exato de cada dia
        # continua disponível via tooltip e na tabela.
        mostrar_rotulo = (i % max(1, len(valores) // 7) == 0) or i == len(valores) - 1

        barras.append({
            "data": v["data"],
            "data_label": v["data"].strftime("%d/%m"),
            "mostrar_rotulo": mostrar_rotulo,
            "x_label": x_label_pos,
            "entrada": v["entrada"],
            "saida": v["saida"],
            "path_entrada": _bar_path(x_entrada, _BAR_W, h_entrada, baseline),
            "path_saida": _bar_path(x_saida, _BAR_W, h_saida, baseline),
            "hit_x": slot_x,
        })

    return {
        "tem_dados": True,
        "dias": dias,
        "barras": barras,
        "total_entradas": total_entradas,
        "total_saidas": total_saidas,
        "teto_label": round(teto),
        "meio_label": round(teto / 2),
        "svg_w": largura_total,
        "svg_h": altura_total,
        "baseline": baseline,
        "top_y": _TOP_PAD,
        # Divisão inteira (não "/") de propósito: qualquer valor float que
        # cair aqui seria renderizado pelo template com vírgula decimal
        # (LANGUAGE_CODE="pt-br" + USE_I18N=True), o que quebra o atributo
        # numérico do SVG (ex.: y="84,0" em vez de "84").
        "mid_y": _TOP_PAD + _BARS_H // 2,
        "left_pad": _LEFT_PAD,
        "label_y": baseline + 16,
        "slot_w": _SLOT_W,
        "hit_h": _BARS_H,
    }
