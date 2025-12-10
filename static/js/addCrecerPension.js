const fileEl = document.getElementById('pdfFile');
const issuerEl = document.getElementById('issuer');

if (fileEl && issuerEl) {
  fileEl.addEventListener('change', () => {
    const f = fileEl.files && fileEl.files[0];
    const name = (f?.name || '').toLowerCase();
    if (name.includes('crecer') || name.includes('cs-sctr')) {
      const opt = [...issuerEl.options].find(o => (o.value || '').toLowerCase() === 'crecer');
      if (opt) issuerEl.value = opt.value;
      // Prellenar ramo producto si aplica
      const ramoTop = document.getElementById('ramoProductoTop');
      if (ramoTop && !ramoTop.value) ramoTop.value = 'Seguro de Pensión';
    }
  });
}
