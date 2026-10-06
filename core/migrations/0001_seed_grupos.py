# Cria os grupos de permissão usados pelo sistema:
# - "Gerentes": acesso a ações sensíveis (ex.: excluir movimentações de
#   estoque já registradas).
# - "Mecânicos": grupo padrão para quem só registra/edita o dia a dia
#   (Ordens de Serviço, Movimentações), sem poder de exclusão.
# Um superusuário (is_staff/is_superuser) sempre tem acesso, independente
# de grupo — os grupos servem para dar esse mesmo acesso a alguém que não
# é superusuário.

from django.db import migrations

GRUPOS = ["Gerentes", "Mecânicos"]


def criar_grupos(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for nome in GRUPOS:
        Group.objects.get_or_create(name=nome)


def remover_grupos(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=GRUPOS).delete()


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(criar_grupos, remover_grupos),
    ]
