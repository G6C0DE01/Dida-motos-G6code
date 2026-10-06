from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def gerente_required(view_func):
    """
    Restringe a view a usuários staff/superusuário ou pertencentes ao
    grupo "Gerentes" (veja core/migrations/0001_seed_grupos.py).

    Usado em ações sensíveis e difíceis de desfazer — hoje, excluir uma
    movimentação de estoque já registrada. Mecânicos continuam podendo
    registrar e editar movimentações normalmente; só a exclusão exige o
    papel de gerente.
    """
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if user.is_staff or user.groups.filter(name="Gerentes").exists():
            return view_func(request, *args, **kwargs)
        messages.error(request, "Essa ação é restrita a gerentes.")
        return redirect("core:dashboard")
    return _wrapped
