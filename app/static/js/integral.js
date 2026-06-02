document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("integral-validar-form");
    const resultadoContainer = document.getElementById("integral-resultado-container");

    if (!form || !resultadoContainer) {
        return;
    }

    form.addEventListener("submit", async function (event) {
        event.preventDefault();

        const formData = new FormData(form);

        resultadoContainer.innerHTML = `
            <div class="alert alert-info mt-3">
                Procesando solicitud Integral...
            </div>
        `;

        try {
            const response = await fetch("/integral/validar", {
                method: "POST",
                body: formData
            });

            const html = await response.text();

            if (!response.ok) {
                resultadoContainer.innerHTML = html;
                return;
            }

            resultadoContainer.innerHTML = html;

        } catch (error) {
            resultadoContainer.innerHTML = `
                <div class="alert alert-danger mt-3">
                    Error de comunicación con el servidor.
                </div>
            `;
        }
    });
});