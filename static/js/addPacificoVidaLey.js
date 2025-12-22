const issuerSel = document.getElementById("issuer");
const pdfInput = document.getElementById("pdfFile");

pdfInput?.addEventListener("change", () => {
  const f = pdfInput.files && pdfInput.files[0];
  const name = (f?.name || "").toLowerCase();

  // Detectar Pacífico en archivos de Vida Ley: "pacifico", "vida ley", "condicionado"
  const looksPacificoVidaLey =
    name.includes("pacifico") ||
    name.includes("pacífico") ||
    /vida[ _-]?ley/.test(name) ||
    /condicionado/.test(name);

  if (looksPacificoVidaLey) {
    const opt = [...issuerSel.options].find(o => (o.value || "").toLowerCase() === "pacifico");
    if (opt) issuerSel.value = opt.value;
    // Prellenar ramo producto si aplica
    const ramoTop = document.getElementById("ramoProductoTop");
    if (ramoTop && !ramoTop.value) ramoTop.value = "Seguro de Vida";
  }
});