/*
 * Combobox com busca (progressive enhancement).
 *
 * Transforma qualquer <select class="searchable"> num campo de texto com
 * autocomplete/filtro, sem depender de nenhuma biblioteca externa. O
 * <select> original continua no DOM (só fica visualmente escondido) e
 * segue sendo a fonte da verdade: é ele quem é enviado no submit do
 * formulário, então nada muda no lado do servidor.
 *
 * Uso: adicione a classe "searchable" (e opcionalmente um atributo
 * data-placeholder) no widget do campo, no forms.py:
 *
 *   peca = forms.ModelChoiceField(
 *       widget=forms.Select(attrs={"class": "searchable", "data-placeholder": "Buscar peça..."})
 *   )
 *
 * Funciona também dentro de formsets (várias linhas com o mesmo campo) e
 * se mantém sincronizado se outro script inserir novas <option> no select
 * (ex.: o popup de cadastro auxiliar em peca_form.html).
 */
(function () {
    "use strict";

    function normalize(str) {
        return (str || "")
            .toString()
            .normalize("NFD")
            .replace(/[̀-ͯ]/g, "")
            .toLowerCase();
    }

    function enhance(select) {
        if (select.dataset.searchableReady) return;
        select.dataset.searchableReady = "1";

        var wrap = document.createElement("div");
        wrap.className = "searchable-wrap";
        select.parentNode.insertBefore(wrap, select);
        wrap.appendChild(select);
        select.classList.add("searchable-native");
        select.setAttribute("tabindex", "-1");
        select.setAttribute("aria-hidden", "true");

        var input = document.createElement("input");
        input.type = "text";
        input.className = "searchable-input";
        input.setAttribute("autocomplete", "off");
        input.setAttribute("role", "combobox");
        input.placeholder = select.dataset.placeholder || "Digite para buscar...";
        if (select.disabled) input.disabled = true;
        wrap.appendChild(input);

        var list = document.createElement("div");
        list.className = "searchable-list";
        wrap.appendChild(list);

        var activeIndex = -1;
        var filtered = [];

        function optionsSnapshot() {
            return Array.prototype.map.call(select.options, function (opt) {
                return { value: opt.value, label: opt.textContent };
            });
        }

        function displayLabel(o) {
            return o.value ? o.label : "";
        }

        function syncInputFromSelect() {
            var opt = select.options[select.selectedIndex];
            input.value = opt ? displayLabel({ value: opt.value, label: opt.textContent }) : "";
        }

        function closeList() {
            list.classList.remove("open");
            activeIndex = -1;
        }

        function selectOption(o) {
            select.value = o.value;
            input.value = displayLabel(o);
            closeList();
            select.dispatchEvent(new Event("change", { bubbles: true }));
        }

        function renderList(query) {
            var all = optionsSnapshot();
            var q = normalize(query);
            filtered = q
                ? all.filter(function (o) { return o.value && normalize(o.label).indexOf(q) !== -1; })
                : all.slice();

            list.innerHTML = "";
            if (!filtered.length) {
                var empty = document.createElement("div");
                empty.className = "searchable-option empty";
                empty.textContent = "Nenhum resultado encontrado.";
                list.appendChild(empty);
            } else {
                filtered.forEach(function (o) {
                    var item = document.createElement("div");
                    item.className = "searchable-option";
                    item.textContent = o.value ? o.label : "— nenhum —";
                    item.dataset.value = o.value;
                    item.addEventListener("mousedown", function (e) {
                        // preventDefault evita que o input perca o foco (blur)
                        // antes do clique ser processado.
                        e.preventDefault();
                        selectOption(o);
                    });
                    list.appendChild(item);
                });
            }
            activeIndex = -1;
            list.classList.add("open");
        }

        function highlight(idx) {
            var items = list.querySelectorAll(".searchable-option[data-value]");
            items.forEach(function (el) { el.classList.remove("active"); });
            if (items[idx]) {
                items[idx].classList.add("active");
                items[idx].scrollIntoView({ block: "nearest" });
            }
        }

        input.addEventListener("focus", function () {
            // Blur sempre resincroniza o input com o valor selecionado, então
            // ao focar de novo o texto é sempre o rótulo atual (ou vazio) —
            // mostra a lista completa em vez de filtrar por ele.
            renderList("");
            input.select();
        });
        input.addEventListener("input", function () { renderList(input.value); });
        input.addEventListener("keydown", function (e) {
            if (e.key === "ArrowDown") {
                e.preventDefault();
                if (!list.classList.contains("open")) { renderList(""); return; }
                activeIndex = Math.min(activeIndex + 1, filtered.length - 1);
                highlight(activeIndex);
            } else if (e.key === "ArrowUp") {
                e.preventDefault();
                activeIndex = Math.max(activeIndex - 1, 0);
                highlight(activeIndex);
            } else if (e.key === "Enter") {
                if (list.classList.contains("open") && activeIndex >= 0 && filtered[activeIndex]) {
                    e.preventDefault();
                    selectOption(filtered[activeIndex]);
                }
            } else if (e.key === "Escape") {
                closeList();
                syncInputFromSelect();
            }
        });
        document.addEventListener("click", function (e) {
            if (!wrap.contains(e.target)) {
                closeList();
                syncInputFromSelect();
            }
        });

        // Mantém sincronizado se novas <option> forem inseridas no select por
        // outro script (ex.: popup de cadastro auxiliar via postMessage).
        new MutationObserver(syncInputFromSelect).observe(select, { childList: true });
        select.addEventListener("change", syncInputFromSelect);

        syncInputFromSelect();
    }

    function enhanceAll() {
        document.querySelectorAll("select.searchable").forEach(enhance);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", enhanceAll);
    } else {
        enhanceAll();
    }
})();
