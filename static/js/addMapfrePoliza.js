(function () {
    console.log('[addMapfrePoliza] script cargado');

    const fileEl = document.getElementById('pdfFile');
    const issuerEl = document.getElementById('issuer');

    if (!fileEl || !issuerEl) {
      console.warn('[addMapfrePoliza] elementos faltan', { hasFileEl: !!fileEl, hasIssuerEl: !!issuerEl });
      return;
    }

    // Log cuando cambias el archivo PDF
    fileEl.addEventListener('change', () => {
      const f = fileEl.files && fileEl.files[0];
      console.log('[addMapfrePoliza] cambio de archivo', f ? { name: f.name, size: f.size, type: f.type } : 'sin archivo');
      if (!f) return;

      const name = (f.name || '').toLowerCase();
      if (!issuerEl.value && name.includes('mapfre')) {
        issuerEl.value = 'mapfre';
        issuerEl.dispatchEvent(new Event('change'));
        console.log('[addMapfrePoliza] proveedor preseleccionado: mapfre');
      }
    });

    // Log cuando cambia el proveedor (issuer)
    issuerEl.addEventListener('change', () => {
      console.log('[addMapfrePoliza] issuer actual:', issuerEl.value);
    });
})();