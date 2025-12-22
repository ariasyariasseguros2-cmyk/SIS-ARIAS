const issuerSel = document.getElementById("issuer");
const pdfInput = document.getElementById("pdfFile");

pdfInput?.addEventListener("change", () => {
  const f = pdfInput.files && pdfInput.files[0];
  const name = (f?.name || "").toLowerCase();

  // Ajuste: no usar PF-SCTR para decidir Pacífico (también aparece en Sanitas)
  const looksPacifico =
    name.includes("pacifico");
    //name.includes("pacífico");

  if (looksPacifico) {
    const opt = [...issuerSel.options].find(o => (o.value || "").toLowerCase() === "pacifico");
    if (opt) issuerSel.value = opt.value;
    const ramoTop = document.getElementById("ramoProductoTop");
    if (ramoTop && !ramoTop.value) ramoTop.value = "SCTR";
  }
});
