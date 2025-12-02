(function () {
  const fileEl = document.getElementById('pdfFile');
  const issuerEl = document.getElementById('issuer');
  if (!fileEl || !issuerEl) return;

  // Si el nombre del archivo contiene "mapfre", preselecciona el proveedor
  fileEl.addEventListener('change', () => {
    const f = fileEl.files && fileEl.files[0];
    if (!f) return;
    const name = (f.name || '').toLowerCase();
    if (!issuerEl.value && name.includes('mapfre')) {
      issuerEl.value = 'mapfre';
    }
  });
})();