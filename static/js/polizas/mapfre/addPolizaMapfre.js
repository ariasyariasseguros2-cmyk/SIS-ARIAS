(function () {
    console.log('[addPolizaMapfre] script cargado');

    const fileEl = document.getElementById('pdfFile');
    const issuerEl = document.getElementById('issuer');

    if (!fileEl || !issuerEl) {
        console.warn('[addPolizaMapfre] Elementos necesarios no encontrados');
        return;
    }

    fileEl.addEventListener('change', () => {
        const f = fileEl.files && fileEl.files[0];
        if (!f) return;

        const name = (f.name || '').toLowerCase();
        
        // Lógica específica para Mapfre Equipo de Contratistas
        // Se activa si el nombre del archivo sugiere este tipo de póliza
        if (name.includes('mapfre') && (name.includes('equipo') || name.includes('contratista'))) {
            console.log('[addPolizaMapfre] Detectado posible Mapfre Equipo de Contratistas');

            // 1. Pre-seleccionar "Mapfre" en el listado de aseguradoras
            const mapfreOpt = Array.from(issuerEl.options).find(o => 
                (o.value || '').toLowerCase().includes('mapfre')
            );

            if (mapfreOpt) {
                if (issuerEl.value !== mapfreOpt.value) {
                    issuerEl.value = mapfreOpt.value;
                    // Disparar evento change para que otros scripts reaccionen
                    issuerEl.dispatchEvent(new Event('change'));
                }
            }
        }
    });
})();
