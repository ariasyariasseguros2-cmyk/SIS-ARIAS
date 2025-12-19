(function () {
  if (window.currentPage !== "anadir-poliza") return;

  const issuerSel = document.getElementById("issuer");
  const pdfInput = document.getElementById("pdfFile");

  // Heurística simple: si el nombre sugiere Protecta/Pensión/AC-SCTR, selecciona proveedor
  pdfInput?.addEventListener("change", () => {
    const f = pdfInput.files && pdfInput.files[0];
    const name = (f?.name || "").toLowerCase();
    const looksProtecta =
      name.includes("proctecta") ||
      name.includes("protecta") ||
      name.includes("pension") ||
      /(^|\\b)ac[-_ ]?sctr/.test(name);

    if (looksProtecta) {
      const opt = [...issuerSel.options].find(o => (o.value || "").toLowerCase() === "proctecta");
      if (opt) issuerSel.value = opt.value;
      // Prellenar ramo producto si aplica
      const ramoTop = document.getElementById("ramoProductoTop");
      if (ramoTop && !ramoTop.value) ramoTop.value = "Pensión";
    }
  });
})();
