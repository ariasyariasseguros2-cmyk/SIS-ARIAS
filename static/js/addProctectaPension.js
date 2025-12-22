(function () {
  if (window.currentPage !== "anadir-poliza") return;

  const issuerSel = document.getElementById("issuer");
  const pdfInput = document.getElementById("pdfFile");

  // Heurística simple: SOLO si el nombre sugiere Protecta, selecciona proveedor
  pdfInput?.addEventListener("change", () => {
    const f = pdfInput.files && pdfInput.files[0];
    const name = (f?.name || "").toLowerCase();
    const looksProtecta =
      name.includes("proctecta") ||
      name.includes("protecta") ||
      /(^|\b)ac[-_ ]?sctr/.test(name); // opcional: si AC-SCTR es propio de Protecta

    if (looksProtecta) {
      const opt = [...issuerSel.options].find(o => (o.value || "").toLowerCase() === "proctecta");
      if (opt) issuerSel.value = opt.value;
      const ramoTop = document.getElementById("ramoProductoTop");
      if (ramoTop && !ramoTop.value) ramoTop.value = "Pensión";
    }
  });
})();
