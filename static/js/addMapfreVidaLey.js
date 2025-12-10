document.getElementById("pdfFile")?.addEventListener("change", () => {
  const input = document.getElementById("pdfFile");
  const issuerSel = document.getElementById("issuer");
  const f = input?.files && input.files[0];
  const name = (f?.name || "").toLowerCase();

  // Ampliar heurística: “vida ley” en nombre (con espacio/guion/underscore)
  const isVidaLey = /vida[\s\-_]?ley/.test(name);

  if (isVidaLey || name.includes("vmapfre-vida-ley")) {
    const opt = [...(issuerSel?.options || [])].find(
      o => (o.value || "").toLowerCase() === "mapfre-vida-ley"
    );
    if (opt && issuerSel) issuerSel.value = opt.value;
    // Prellenar ramo producto si aplica
    const ramoTop = document.getElementById("ramoProductoTop");
    if (ramoTop && !ramoTop.value) ramoTop.value = "Seguro de Vida";
  }
});