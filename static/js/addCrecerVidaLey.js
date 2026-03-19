document.getElementById("pdfFile")?.addEventListener("change", () => {
  const input = document.getElementById("pdfFile");
  const issuerSel = document.getElementById("issuer");
  const f = input?.files && input.files[0];
  const name = (f?.name || "").toLowerCase();

  // Ampliar heurística: “vida ley” en nombre (con espacio/guion/underscore)
  const isVidaLey = /vida[\s\-_]?ley/.test(name);

  if (isVidaLey || name.includes("vida-ley-crecer")) {
    const opt = [...(issuerSel?.options || [])].find(o => {
      const v = (o.value || "").toLowerCase();
      return v === "crecer";
    });
    if (opt && issuerSel) issuerSel.value = opt.value;
    // Prellenar ramo producto si aplica (id correcto en la UI)
    const ramoTop = document.getElementById("ramosProductoTop") || document.getElementById("ramoProductoTop");
    if (ramoTop && !ramoTop.value) ramoTop.value = "Seguro de Vida";
  }
});
