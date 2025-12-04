(function () {
  if (window.currentPage !== "anadir-poliza") return;

  const issuerSel = document.getElementById("issuer");
  const pdfInput = document.getElementById("pdfFile");

  // Heurística simple: si el nombre del archivo sugiere Sanitas/PF-SCTR, selecciona proveedor
  pdfInput?.addEventListener("change", () => {
    const f = pdfInput.files && pdfInput.files[0];
    const name = (f?.name || "").toLowerCase();
    if (name.includes("sanitas") || name.includes("pf-sctr")) {
      const opt = [...issuerSel.options].find(o => (o.value || "").toLowerCase() === "sanitas");
      if (opt) issuerSel.value = opt.value;
      // Prellenar ramo producto si aplica
      const ramoTop = document.getElementById("ramoProductoTop");
      if (ramoTop && !ramoTop.value) ramoTop.value = "SCTR Salud";
    }
  });
})();