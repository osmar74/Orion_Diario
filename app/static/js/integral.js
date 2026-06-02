(function () {
    "use strict";

    function getTemplateHtml(templateId) {
        const template = document.getElementById(templateId);
        return template ? template.innerHTML : "";
    }

    async function manejarSubmitIntegral(event) {
        const form = event.target;

        if (!form || form.id !== "integral-validar-form") {
            return;
        }

        event.preventDefault();

        const resultadoContainer = document.getElementById("integral-resultado-container");

        if (!resultadoContainer) {
            return;
        }

        const formData = new FormData(form);
        resultadoContainer.innerHTML = getTemplateHtml("integral-loading-template");

        try {
            const response = await fetch("/integral/validar", {
                method: "POST",
                body: formData,
            });

            const html = await response.text();
            resultadoContainer.innerHTML = html;
        } catch (error) {
            resultadoContainer.innerHTML = getTemplateHtml("integral-error-comunicacion-template");
        }
    }

    function initIntegralModule() {
        // La inicialización queda disponible para cargas dinámicas del módulo.
        // El submit se maneja por delegación global para no duplicar eventos.
    }

    if (!window.__integralSubmitDelegadoV1) {
        document.addEventListener("submit", manejarSubmitIntegral);
        window.__integralSubmitDelegadoV1 = true;
    }

    window.initIntegralModule = initIntegralModule;
})();
