addEventListener('DOMContentLoaded', function() {
    // NUEVO: LPV Vida Ley
    if (document.getElementById('poliza_proveedor').value === 'lpv-vida-ley') {
        // Asegúrate de que el campo 'vigencia_hasta' exista
        if (!document.getElementById('vigencia_hasta')) {
            console.error('Campo "vigencia_hasta" no encontrado');
            return;
        }
        // Asigna la función al evento 'change'
        document.getElementById('vigencia_hasta').addEventListener('change', function() {
            // Obtén la fecha seleccionada
            const selectedDate = this.value;
            // Actualiza el campo 'hasta' con la misma fecha
            document.getElementById('hasta').value = selectedDate;
        });
    }
});

