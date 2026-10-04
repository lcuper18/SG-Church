// Evita el doble envío: desactiva el botón de submit al enviar un formulario.
document.addEventListener('submit', function (event) {
    const form = event.target;
    if (form.method.toLowerCase() !== 'post' || form.dataset.allowResubmit !== undefined) {
        return;
    }
    // Esperar un tick: si el envío fue cancelado (validación), no se desactiva nada.
    setTimeout(function () {
        if (event.defaultPrevented) {
            return;
        }
        form.querySelectorAll('button[type="submit"], input[type="submit"]').forEach(function (btn) {
            btn.disabled = true;
        });
    }, 0);
});

// Al volver con el botón "atrás" el navegador restaura la página con los botones desactivados.
window.addEventListener('pageshow', function (event) {
    if (event.persisted) {
        document.querySelectorAll('button[type="submit"]:disabled, input[type="submit"]:disabled').forEach(function (btn) {
            btn.disabled = false;
        });
    }
});
