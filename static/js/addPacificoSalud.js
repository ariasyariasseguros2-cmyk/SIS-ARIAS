const issuerSel = document.getElementById("issuer");
const pdfInput = document.getElementById("pdfFile");

pdfInput?.addEventListener("change", () => {
  const f = pdfInput.files && pdfInput.files[0];
  const name = (f?.name || "").toLowerCase();

  const looksPacifico =
    name.includes("pacifico") ||
    /(^|\b)pf[-_ ]?sctr/.test(name); // NUEVO: detectar patrón típico de Pacífico SCTR

  if (looksPacifico) {
    const opt = [...issuerSel.options].find(o => (o.value || "").toLowerCase() === "pacifico");
    if (opt) issuerSel.value = opt.value;
    const ramoTop = document.getElementById("ramoProductoTop");
    if (ramoTop && !ramoTop.value) ramoTop.value = "SCTR";
  }
});
