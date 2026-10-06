import re
import secrets
import string
import unicodedata

from django.contrib.auth.models import User


def _somente_letras_minusculas(texto):
    """Remove acentos e qualquer caractere que não seja letra, em minúsculo."""
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z]", "", texto).lower()


def gerar_username(nome_completo):
    """
    Gera um nome de usuário a partir do nome completo, em vez de pedir
    pra pessoa inventar um (o campo padrão do Django, com sua ajuda
    sobre caracteres permitidos, confunde quem não é da área).

    Ex.: "Guilherme Silva" -> "guilherme.s"; "Ana" -> "ana". Se já
    existir alguém com esse username, acrescenta um número no final
    ("guilherme.s2", "guilherme.s3", ...) até achar um livre.
    """
    partes = [p for p in (nome_completo or "").strip().split() if p]
    primeiro = _somente_letras_minusculas(partes[0]) if partes else ""
    inicial = _somente_letras_minusculas(partes[-1])[:1] if len(partes) > 1 else ""
    base = f"{primeiro}.{inicial}" if inicial else primeiro
    base = base or "usuario"

    username = base
    contador = 2
    while User.objects.filter(username=username).exists():
        username = f"{base}{contador}"
        contador += 1
    return username


def gerar_senha_temporaria(tamanho=10):
    """
    Senha temporária aleatória para uma conta recém-criada pelo admin.
    Não precisa ser memorável: o funcionário é obrigado a trocá-la no
    primeiro login (ver core.models.PerfilUsuario.deve_trocar_senha).
    """
    alfabeto = string.ascii_letters + string.digits
    return "".join(secrets.choice(alfabeto) for _ in range(tamanho))
