(function () {
  if (window.currentPage !== "anadir-poliza") return;

  const issuerSel = document.getElementById("issuer");
  const pdfInput = document.getElementById("pdfFile");
  const ramoTop = document.getElementById("ramosProductoTop");

  pdfInput?.addEventListener("change", () => {
    const f = pdfInput.files && pdfInput.files[0];
    const name = (f?.name || "").toLowerCase();

    const looksPositiva = name.includes("positiva") || name.includes("lpv");
    const looksSalud = /sctr|eps|salud/.test(name);

    if (!issuerSel) return;
    const opts = Array.from(issuerSel.options);
    // Preferir slug dedicado si existe
    const optLPVSalud = opts.find(o => (o.value || "").toLowerCase() === "lpv-salud");
    const optPositiva = opts.find(o => (o.value || "").toLowerCase() === "positiva");

    if (optLPVSalud) {
      issuerSel.value = optLPVSalud.value;
    } else if (looksPositiva || looksSalud) {
      if (optPositiva) issuerSel.value = optPositiva.value;
    }

    if (ramoTop && !ramoTop.value) ramoTop.value = "SCTR SALUD";
  });
})();