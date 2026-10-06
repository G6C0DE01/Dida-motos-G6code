import re

from django.core.exceptions import ValidationError


def apenas_digitos(valor):
    """Remove tudo que não for dígito (pontos, traço etc. de um CPF digitado formatado)."""
    return re.sub(r"\D", "", valor or "")


def validar_cpf(valor):
    """
    Valida um CPF pelo algoritmo oficial dos dígitos verificadores
    (módulo 11). Não confirma que o número existe de verdade — a Receita
    Federal não oferece uma API pública e gratuita pra isso (ver
    conversa do projeto) — só garante que é um número bem formado, o que
    já evita a maioria dos erros de digitação.
    """
    cpf = apenas_digitos(valor)

    if len(cpf) != 11 or cpf == cpf[0] * 11:
        raise ValidationError("CPF inválido.", code="cpf_invalido")

    for pos in (9, 10):
        soma = sum(int(cpf[i]) * ((pos + 1) - i) for i in range(pos))
        digito = ((soma * 10) % 11) % 10
        if digito != int(cpf[pos]):
            raise ValidationError("CPF inválido.", code="cpf_invalido")
