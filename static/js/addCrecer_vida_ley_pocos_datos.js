// Helper para Crecer Vida Ley (Variante Pocos Datos)
// La lógica de detección de archivo ya está cubierta mayormente en addCrecerVidaLey.js
// Este script se mantiene para futuras extensiones específicas de esta variante.

console.log("Cargado helper: addCrecer_vida_ley_pocos_datos.js");

// Si se requiriera lógica específica de UI al seleccionar el archivo:
document.getElementById("pdfFile")?.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const name = file.name.toLowerCase();
    
    // Si el nombre sugiere esta variante específica, podríamos hacer algo extra
    // Por ahora, el backend maneja la distinción de extracción.
});
 