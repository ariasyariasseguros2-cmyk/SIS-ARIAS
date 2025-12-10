const issuerSel = document.getElementById("issuer");
const pdfInput = document.getElementById("pdfFile");

pdfInput?.addEventListener("change", () => {
  const f = pdfInput.files && pdfInput.files[0];
  const name = (f?.name || "").toLowerCase();
  if (name.includes("pacifico")) {
    const opt = [...issuerSel.options].find(o => (o.value || "").toLowerCase() === "pacifico");
    if (opt) issuerSel.value = opt.value;
    // Prellenar ramo producto si aplica
    const ramoTop = document.getElementById("ramoProductoTop");
    if (ramoTop && !ramoTop.value) ramoTop.value = "SCTR";
  }
});
