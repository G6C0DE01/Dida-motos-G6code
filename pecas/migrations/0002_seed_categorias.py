# Popula as categorias padrão descritas no escopo do projeto:
# Motor, Transmissão, Suspensão, Freios, Pneus, Acessórios, Eletrônicos,
# Consumíveis. O grupo pode adicionar/editar categorias depois pelo admin
# normalmente — essa migration só garante que o sistema já nasce com elas.

from django.db import migrations

CATEGORIAS = [
    "Motor",
    "Transmissão",
    "Suspensão",
    "Freios",
    "Pneus",
    "Acessórios",
    "Eletrônicos",
    "Consumíveis",
]


def criar_categorias(apps, schema_editor):
    Categoria = apps.get_model("pecas", "Categoria")
    for nome in CATEGORIAS:
        Categoria.objects.get_or_create(nome=nome)


def remover_categorias(apps, schema_editor):
    Categoria = apps.get_model("pecas", "Categoria")
    Categoria.objects.filter(nome__in=CATEGORIAS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("pecas", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(criar_categorias, remover_categorias),
    ]
