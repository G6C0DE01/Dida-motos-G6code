from pecas.models import Peca


def papel_usuario(request):
    """
    Disponibiliza `is_gerente` em todos os templates, para esconder ações
    restritas (ex.: botão "Excluir" de movimentação) de quem não tem esse
    papel. Mantido em sincronia com core.decorators.gerente_required, que
    faz a checagem de verdade no lado do servidor — isso aqui é só para a
    interface, nunca a única proteção.
    """
    user = getattr(request, "user", None)
    is_gerente = bool(
        user and user.is_authenticated
        and (user.is_staff or user.groups.filter(name="Gerentes").exists())
    )
    return {"is_gerente": is_gerente}


def alerta_estoque_baixo(request):
    """
    Disponibiliza a contagem de peças abaixo do mínimo em todas as
    páginas, para o badge de alerta no topo (menu lateral/topbar).
    """
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated):
        return {"pecas_abaixo_minimo_count": 0}
    from django.db.models import F
    count = Peca.objects.filter(ativo=True, quantidade_estoque__lt=F("quantidade_minima")).count()
    return {"pecas_abaixo_minimo_count": count}
