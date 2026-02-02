(function () {
    if (window.currentPage !== "anadir-poliza") return;
  
    // Helper para detectar Protecta Pensión Emisión en el frontend
    function AddProctectaPensionEmisionHelper() {
      const issuerSel = document.getElementById("issuer");
      const pdfInput = document.getElementById("pdfFile");
  
      if (!issuerSel || !pdfInput) return;
  
      pdfInput.addEventListener("change", () => {
        const f = pdfInput.files && pdfInput.files[0];
        const name = (f?.name || "").toLowerCase();
        
        // Heurística: si el nombre del archivo contiene "condiciones particulares" y "pension", 
        // o si detectamos que es Protecta por otros medios.
        // NOTA: El backend hace la detección fuerte por contenido, pero aquí ayudamos a la UI.
        const looksLikeProtecta = name.includes("protecta") || name.includes("proctecta");
        const looksLikePension = name.includes("pension");
        const looksLikeEmision = name.includes("condiciones") || name.includes("particulares");
  
        if (looksLikeProtecta) {
            // Seleccionar Protecta en el dropdown
            const opt = [...issuerSel.options].find(o => (o.value || "").toLowerCase() === "protecta" || (o.value || "").toLowerCase() === "proctecta");
            if (opt) issuerSel.value = opt.value;
            
            // Si parece ser pensión, pre-llenar ramo
            const ramoTop = document.getElementById("ramoProductoTop");
            if (ramoTop && !ramoTop.value && looksLikePension) {
                ramoTop.value = "SCTR PENSIÓN";
            }
        }
      });
    }
  
    // Exponer al scope global por si acaso
    window.AddProctectaPensionEmisionHelper = AddProctectaPensionEmisionHelper;
    
    // Inicializar
    new AddProctectaPensionEmisionHelper();
  })();
