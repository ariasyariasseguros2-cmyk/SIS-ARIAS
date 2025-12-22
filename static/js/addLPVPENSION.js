(function () {
  if (window.currentPage !== "anadir-poliza") return;

  function addLPVSALUDPENSION() {
    const issuerSel = document.getElementById("issuer");
    const pdfInput = document.getElementById("pdfFile");
    const ramoTop = document.getElementById("ramosProductoTop");

    if (!issuerSel || !pdfInput) return;

    pdfInput.addEventListener("change", () => {
      const f = pdfInput.files && pdfInput.files[0];
      const name = (f?.name || "").toLowerCase();

      // Heurística: PDFs de La Positiva EPS / SCTR Salud/Pensión
      const looksPositiva = name.includes("positiva") || name.includes("lpv");
      const looksSCTR = name.includes("sctr") || name.includes("eps") || name.includes("pension") || name.includes("salud");

      if (looksPositiva || looksSCTR) {
        // Preselecciona "positiva" en el selector (si existe)
        const optPositiva = [...issuerSel.options].find(o => (o.value || "").toLowerCase() === "positiva");
        if (optPositiva) issuerSel.value = optPositiva.value;

        // Prellenar ramo/producto
        if (ramoTop && !ramoTop.value) ramoTop.value = "SCTR";
      }
    });
  }

  // Exponer y ejecutar
  window.addLPVSALUDPENSION = addLPVSALUDPENSION;
  addLPVSALUDPENSION();
})();