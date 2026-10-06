from django import forms
from django.forms import inlineformset_factory

from .models import Cliente, Motocicleta, OrdemServico, ItemOrdemServico
from .validators import apenas_digitos, validar_cpf


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ["nome", "cpf", "telefone", "email"]
        widgets = {
            "cpf": forms.TextInput(attrs={"class": "cpf-input", "placeholder": "000.000.000-00", "maxlength": "14"}),
        }

    def clean_cpf(self):
        cpf = apenas_digitos(self.cleaned_data.get("cpf"))
        if not cpf:
            return None
        validar_cpf(cpf)
        conflito = Cliente.objects.filter(cpf=cpf)
        if self.instance.pk:
            conflito = conflito.exclude(pk=self.instance.pk)
        if conflito.exists():
            raise forms.ValidationError("Já existe um cliente cadastrado com esse CPF.")
        return cpf


class MotocicletaForm(forms.ModelForm):
    """
    Cadastro de veículo com o cliente já vinculado — usada só na edição de
    uma motocicleta existente (o pk já define o cliente). Para cadastrar
    um veículo novo, veja MotocicletaComClienteForm: lá o veículo vem
    primeiro e o cliente (existente ou novo) é resolvido junto.
    """
    class Meta:
        model = Motocicleta
        fields = ["cliente", "marca", "modelo", "ano", "placa"]
        widgets = {
            "cliente": forms.Select(attrs={"class": "searchable", "data-placeholder": "Buscar cliente..."}),
        }


class MotocicletaComClienteForm(forms.Form):
    """
    Cadastro combinado: o veículo é a prioridade (placa/marca/modelo
    primeiro) e o cliente é resolvido em seguida — reaproveitando um
    cliente já cadastrado (por CPF ou pela busca) ou criando um novo com
    só os dados básicos (nome, CPF, telefone).
    """
    placa = forms.CharField(label="Placa", max_length=10, required=False)
    marca = forms.CharField(label="Marca", max_length=50)
    modelo = forms.CharField(label="Modelo", max_length=50)
    ano = forms.IntegerField(label="Ano", required=False)

    cliente_existente = forms.ModelChoiceField(
        label="Cliente já cadastrado",
        queryset=Cliente.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            "class": "searchable", "data-placeholder": "Buscar cliente por nome...",
        }),
    )

    cliente_nome = forms.CharField(label="Nome do cliente", max_length=150, required=False)
    cliente_cpf = forms.CharField(
        label="CPF do cliente", max_length=14, required=False,
        widget=forms.TextInput(attrs={"class": "cpf-input", "placeholder": "000.000.000-00", "maxlength": "14"}),
    )
    cliente_telefone = forms.CharField(label="Telefone do cliente", max_length=20, required=False)

    def clean_cliente_cpf(self):
        cpf = apenas_digitos(self.cleaned_data.get("cliente_cpf"))
        if not cpf:
            return ""
        validar_cpf(cpf)
        return cpf

    def clean(self):
        cleaned = super().clean()
        cliente_existente = cleaned.get("cliente_existente")
        nome = (cleaned.get("cliente_nome") or "").strip()
        if not cliente_existente and not nome:
            raise forms.ValidationError(
                "Selecione um cliente já cadastrado ou informe ao menos o nome do novo cliente."
            )
        return cleaned

    def resolver_cliente(self):
        """
        Retorna o Cliente a usar: o selecionado explicitamente, ou um já
        existente com o mesmo CPF informado (evita duplicar cadastro de
        quem já é cliente), ou um novo criado com os dados básicos.
        """
        cliente = self.cleaned_data.get("cliente_existente")
        if cliente:
            return cliente

        cpf = self.cleaned_data.get("cliente_cpf") or None
        if cpf:
            existente = Cliente.objects.filter(cpf=cpf).first()
            if existente:
                return existente

        return Cliente.objects.create(
            nome=self.cleaned_data["cliente_nome"].strip(),
            cpf=cpf,
            telefone=self.cleaned_data.get("cliente_telefone", "").strip(),
        )


class OrdemServicoForm(forms.ModelForm):
    class Meta:
        model = OrdemServico
        fields = [
            "cliente", "motocicleta", "mecanico", "status",
            "descricao_problema", "valor_servico",
        ]
        widgets = {
            "descricao_problema": forms.Textarea(attrs={"rows": 3}),
            "cliente": forms.Select(attrs={"class": "searchable", "data-placeholder": "Buscar cliente..."}),
            "motocicleta": forms.Select(attrs={"class": "searchable", "data-placeholder": "Buscar motocicleta..."}),
        }


ItemOrdemServicoFormSet = inlineformset_factory(
    OrdemServico,
    ItemOrdemServico,
    fields=["peca", "quantidade", "preco_unitario"],
    widgets={
        "peca": forms.Select(attrs={"class": "searchable", "data-placeholder": "Buscar peça..."}),
    },
    extra=3,
    can_delete=True,
)
