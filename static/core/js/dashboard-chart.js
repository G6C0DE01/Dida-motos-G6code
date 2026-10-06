/*
 * Camada de interação do gráfico "Entradas x Saídas" do dashboard
 * (core/templates/core/dashboard.html). O gráfico (barras, eixos,
 * rótulos) já é renderizado inteiro pelo servidor em SVG; este script só
 * adiciona o tooltip ao passar o mouse/focar com teclado em cada coluna
 * de dia — é puramente progressive enhancement, os mesmos números já
 * estão nos atributos aria-label de cada barra e na tabela (<details>)
 * logo abaixo do gráfico.
 */
(function () {
    "use strict";

    function row(name, value, color) {
        var r = document.createElement("div");
        r.className = "viz-tooltip-row";
        var key = document.createElement("span");
        key.className = "key";
        key.style.background = color;
        var name_el = document.createElement("span");
        name_el.className = "name";
        name_el.textContent = name + ":";
        var val_el = document.createElement("span");
        val_el.className = "value";
        val_el.textContent = value;
        r.appendChild(key);
        r.appendChild(name_el);
        r.appendChild(val_el);
        return r;
    }

    function initChart(wrap) {
        var tooltip = wrap.querySelector(".viz-tooltip");
        var hits = wrap.querySelectorAll(".viz-hit");
        if (!tooltip || !hits.length) return;

        function fill(hit) {
            tooltip.innerHTML = "";
            var title = document.createElement("div");
            title.className = "viz-tooltip-title";
            title.textContent = hit.dataset.label || "";
            tooltip.appendChild(title);
            tooltip.appendChild(row("Entradas", hit.dataset.entrada || "0", "var(--viz-entrada)"));
            tooltip.appendChild(row("Saídas", hit.dataset.saida || "0", "var(--viz-saida)"));
        }

        function position(hit, evt) {
            var wrapRect = wrap.getBoundingClientRect();
            var x, y;
            if (evt && typeof evt.clientX === "number" && evt.clientX !== 0) {
                x = evt.clientX - wrapRect.left;
                y = evt.clientY - wrapRect.top;
            } else {
                var hitRect = hit.getBoundingClientRect();
                x = hitRect.left + hitRect.width / 2 - wrapRect.left;
                y = hitRect.top - wrapRect.top;
            }
            var maxLeft = Math.max(4, wrapRect.width - tooltip.offsetWidth - 4);
            tooltip.style.left = Math.max(4, Math.min(x + 12, maxLeft)) + "px";
            tooltip.style.top = Math.max(4, y - tooltip.offsetHeight - 12) + "px";
        }

        function show(hit, evt) {
            fill(hit);
            tooltip.style.display = "block";
            position(hit, evt);
        }

        function hide() {
            tooltip.style.display = "none";
        }

        hits.forEach(function (hit) {
            hit.addEventListener("mouseenter", function (e) { show(hit, e); });
            hit.addEventListener("mousemove", function (e) { position(hit, e); });
            hit.addEventListener("mouseleave", hide);
            hit.addEventListener("focus", function (e) { show(hit, e); });
            hit.addEventListener("blur", hide);
        });
    }

    function initAll() {
        document.querySelectorAll(".viz-chart-wrap").forEach(initChart);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initAll);
    } else {
        initAll();
    }
})();
