(function () {
    "use strict";

    function onReady(callback) {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", callback);
            return;
        }

        callback();
    }

    function templateHtml(id) {
        const template = document.getElementById(id);
        return template ? template.innerHTML : "";
    }

    function initIntegralV2() {
        const form = document.getElementById("integral-v2-validar-form");
        const resultado = document.getElementById("integral-v2-resultado");

        if (!form || !resultado) {
            return;
        }

        form.addEventListener("submit", async function (event) {
            event.preventDefault();

            resultado.innerHTML = templateHtml("integral-v2-loading-template");

            try {
                const response = await fetch(form.action, {
                    method: "POST",
                    body: new FormData(form),
                });

                resultado.innerHTML = await response.text();
            } catch (error) {
                resultado.innerHTML = templateHtml("integral-v2-error-comunicacion-template");
            }
        });
    }

    onReady(initIntegralV2);
})();
