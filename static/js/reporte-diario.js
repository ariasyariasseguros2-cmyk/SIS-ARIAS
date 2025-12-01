function reporteDiario() {
    const form = document.getElementById('formReporteDiario');
    if (!form) return;

    form.addEventListener('submit', (ev) => {
        ev.preventDefault();
        const data = Object.fromEntries(new FormData(form).entries());
        console.log('[Reporte Diario] Filtros seleccionados:', data);
        // Aquí puedes llamar a tu endpoint para generar/recolectar el reporte:
        // fetch('/api/reporte-diario', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) })
        //   .then(r => r.json()).then(console.log).catch(console.error);
        alert('Filtros listos. Conéctalo a tu backend para procesar.');
    });
}

reporteDiario();