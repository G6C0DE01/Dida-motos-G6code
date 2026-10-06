/*
 * Cadastro combinado de veículo + cliente (ordens_servico/motocicleta_form.html,
 * cadastro novo). Faz duas coisas, sem depender de nenhuma biblioteca externa:
 *
 * 1. Alterna entre "cliente já cadastrado" (select com busca) e "novo
 *    cliente" (nome/CPF/telefone), mostrando só o painel relevante.
 * 2. Ao digitar um CPF no painel "novo cliente", valida o dígito
 *    verificador na hora (sem custo, sem chamada de rede) e, se o CPF
 *    já pertencer a um cliente cadastrado, busca os dados dele
 *    (GET .../clientes/buscar-cpf/?cpf=...) e troca automaticamente
 *    para o painel "cliente já cadastrado" com ele selecionado — evita
 *    duplicar o cadastro de quem já é cliente.
 */
(function () {
    "use strict";

    function apenasDigitos(valor) {
        return (valor || "").replace(/\D/g, "");
    }

    function formatarCpf(digitos) {
        return digitos
            .replace(/(\d{3})(\d)/, "$1.$2")
            .replace(/(\d{3})(\d)/, "$1.$2")
            .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
    }

    function cpfValido(valor) {
        var cpf = apenasDigitos(valor);
        if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) return false;

        for (var pos = 9; pos <= 10; pos++) {
            var soma = 0;
            for (var i = 0; i < pos; i++) {
                soma += parseInt(cpf.charAt(i), 10) * ((pos + 1) - i);
            }
            var digito = ((soma * 10) % 11) % 10;
            if (digito !== parseInt(cpf.charAt(pos), 10)) return false;
        }
        return true;
    }

    function initToggle(form) {
        var radios = form.querySelectorAll('input[name="cliente_modo"]');
        var paineis = form.querySelectorAll(".cliente-modo-painel");
        if (!radios.length) return;

        function aplicar() {
            var modoAtivo = form.querySelector('input[name="cliente_modo"]:checked').value;
            paineis.forEach(function (painel) {
                painel.hidden = painel.dataset.modo !== modoAtivo;
            });
        }

        radios.forEach(function (radio) {
            radio.addEventListener("change", aplicar);
        });
        aplicar();

        return {
            irParaExistente: function () {
                var radioExistente = form.querySelector('input[name="cliente_modo"][value="existente"]');
                if (radioExistente) {
                    radioExistente.checked = true;
                    aplicar();
                }
            },
        };
    }

    function initCpfLookup(form, toggle) {
        var buscarUrl = form.dataset.buscarCpfUrl;
        var cpfInput = form.querySelector(".cpf-input");
        if (!buscarUrl || !cpfInput) return;

        var feedback = cpfInput.parentNode.querySelector(".cpf-feedback");
        var clienteSelect = form.querySelector('select[name="cliente_existente"]');
        var nomeInput = form.querySelector('[name="cliente_nome"]');
        var telefoneInput = form.querySelector('[name="cliente_telefone"]');
        var timer = null;

        function limparFeedback() {
            if (!feedback) return;
            feedback.textContent = "";
            feedback.classList.remove("valido", "invalido");
        }

        function buscar(cpfDigitos) {
            fetch(buscarUrl + "?cpf=" + encodeURIComponent(cpfDigitos), {
                headers: { "X-Requested-With": "XMLHttpRequest" },
            })
                .then(function (resp) { return resp.ok ? resp.json() : null; })
                .then(function (dados) {
                    if (!dados) return;
                    if (dados.encontrado) {
                        if (feedback) {
                            feedback.textContent = "Cliente encontrado: " + dados.nome + " (dados preenchidos automaticamente).";
                            feedback.classList.add("valido");
                            feedback.classList.remove("invalido");
                        }
                        if (clienteSelect) {
                            clienteSelect.value = String(dados.id);
                            clienteSelect.dispatchEvent(new Event("change", { bubbles: true }));
                        }
                        if (toggle) toggle.irParaExistente();
                    } else if (feedback) {
                        feedback.textContent = "CPF válido — nenhum cliente encontrado, será cadastrado um novo.";
                        feedback.classList.add("valido");
                        feedback.classList.remove("invalido");
                    }
                })
                .catch(function () { /* sem internet/erro de rede: só não autopreenche */ });
        }

        cpfInput.addEventListener("input", function () {
            var digitos = apenasDigitos(cpfInput.value).slice(0, 11);
            var posicaoCursor = cpfInput.selectionStart;
            var tamanhoAntes = cpfInput.value.length;
            cpfInput.value = formatarCpf(digitos);
            var diferenca = cpfInput.value.length - tamanhoAntes;
            if (posicaoCursor != null) {
                cpfInput.setSelectionRange(posicaoCursor + diferenca, posicaoCursor + diferenca);
            }

            clearTimeout(timer);
            if (digitos.length < 11) {
                limparFeedback();
                return;
            }
            if (!cpfValido(digitos)) {
                if (feedback) {
                    feedback.textContent = "CPF inválido — confira os números digitados.";
                    feedback.classList.add("invalido");
                    feedback.classList.remove("valido");
                }
                return;
            }
            limparFeedback();
            timer = setTimeout(function () { buscar(digitos); }, 300);
        });
    }

    function initForm(form) {
        var toggle = initToggle(form);
        initCpfLookup(form, toggle);
    }

    function initAll() {
        document.querySelectorAll(".veiculo-cliente-form").forEach(initForm);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initAll);
    } else {
        initAll();
    }
})();
