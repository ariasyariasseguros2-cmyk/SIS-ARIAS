(function () {
  if (window.currentPage !== "anadir-poliza") return;

  const fileEl = document.getElementById('pdfFile');
  const issuerEl = document.getElementById('issuer');

  if (!fileEl || !issuerEl) return;

  fileEl.addEventListener('change', () => {
    const f = fileEl.files && fileEl.files[0];
    if (!f) return;
    const name = (f.name || '').toLowerCase();
    if (name.includes('rimac')) {
      const rimacOpt = Array.from(issuerEl.options).find(o => (o.value || '').toLowerCase().includes('rimac'));
      if (rimacOpt) {
        issuerEl.value = rimacOpt.value;
        issuerEl.dispatchEvent(new Event('change'));
      }
    }
  });
})();
