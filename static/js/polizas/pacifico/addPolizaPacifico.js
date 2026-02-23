(function () {
  console.log('[addPolizaPacifico] script cargado');

  if (window.currentPage !== 'anadir-poliza') return;

  const fileEl = document.getElementById('pdfFile');
  const issuerEl = document.getElementById('issuer');

  if (!fileEl || !issuerEl) {
    console.warn('[addPolizaPacifico] Elementos necesarios no encontrados');
    return;
  }

  fileEl.addEventListener('change', () => {
    const f = fileEl.files && fileEl.files[0];
    if (!f) return;

    const name = (f.name || '').toLowerCase();

    const looksPacifico =
      name.includes('pacifico') ||
      name.includes('pacífico') ||
      name.includes('pf-sctr') ||
      name.includes('vida ley') ||
      name.includes('condicionado');

    if (!looksPacifico) return;

    const pacificoOpt = Array.from(issuerEl.options).find(o =>
      (o.value || '').toLowerCase().includes('pacifico')
    );

    if (pacificoOpt && issuerEl.value !== pacificoOpt.value) {
      issuerEl.value = pacificoOpt.value;
      issuerEl.dispatchEvent(new Event('change'));
    }
  });
})();
