(function () {
  console.log('[addMapfreVidaLey] script cargado');

  const fileEl = document.getElementById('pdfFile');
  const issuerEl = document.getElementById('issuer');
  if (!fileEl || !issuerEl) return;

  fileEl.addEventListener('change', () => {
    const f = fileEl.files && fileEl.files[0];
    if (!f) return;
    const name = (f.name || '').toLowerCase();
    const looksVidaLey = name.includes('vida') || name.includes('ley') || name.includes('vidaley');

    if (!issuerEl.value && looksVidaLey) {
      const opt = [...issuerEl.options].find(o => (o.value || '').toLowerCase() === 'mapfre');
      if (opt) {
        issuerEl.value = opt.value;
        issuerEl.dispatchEvent(new Event('change'));
        console.log('[addMapfreVidaLey] proveedor preseleccionado: mapfre (vida ley)');
      } else {
        console.warn('[addMapfreVidaLey] opción "mapfre" no encontrada en <select id="issuer">');
      }
    }
  });
})();