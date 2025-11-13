document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const exportBtn = document.getElementById('exportPdfBtn');
    const statusEl = document.getElementById('uploadStatus');
    const section = document.getElementById('extractedDataSection');

    function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value && value.trim() ? value : '-';
    }

    uploadBtn?.addEventListener('click', async () => {
        const file = fileInput?.files?.[0];
        if (!file) {
            statusEl.textContent = 'Selecciona un archivo.';
            statusEl.className = 'text-danger mt-2';
            return;
        }

        statusEl.textContent = 'Subiendo...';
        statusEl.className = 'text-muted mt-2';

        try {
            const formData = new FormData();
            formData.append('file', file);

            const resp = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const data = await resp.json();
            if (resp.ok) {
                statusEl.textContent = `OK: ${data.filename}`;
                statusEl.className = 'text-success mt-2';
                fileInput.value = '';

                // Tolerar ambos esquemas: 'extracted' y 'fields'
                const ex = (data.extracted ?? data.fields ?? {});

                setText('valPoliza', ex.poliza);
                setText('valRamo', ex.ramo);
                setText('valVigencia', ex.vigencia_desde);
                setText('valVigenciaHasta', ex.vigencia_hasta);
                setText('valSede', ex.sede);
                setText('valContratante', ex.contratante);
                setText('valDireccion', ex.direccion);
                setText('valCodigoSbs', ex.codigo_sbs);

                // Mostrar la sección si al menos uno tiene valor
                const hasValue = Object.values(ex).some(v => typeof v === 'string' && v.trim().length > 0);
                if (hasValue) {
                    section?.classList.remove('d-none');
                }
            } else {
                statusEl.textContent = `Error: ${data.error || 'Error al subir'}`;
                statusEl.className = 'text-danger mt-2';
            }
        } catch (err) {
            statusEl.textContent = 'Error de red al subir.';
            statusEl.className = 'text-danger mt-2';
        }
    });

    exportBtn?.addEventListener('click', () => {
        // Exporta con "Imprimir" del navegador (elige "Guardar como PDF")
        window.print();
    });
});