document.addEventListener('DOMContentLoaded', () => {
    const { months = [], totals = [], title = 'Total Pólizas' } = window.chartData || {};

    const ctx = document.getElementById('renewalsChart');
    if (!window.currentPage && ctx && months.length && totals.length) {
         new Chart(ctx, {
             type: 'bar',
             data: {
                 labels: months,
                 datasets: [{
                     label: 'Total Pólizas',
                     data: totals,
                     backgroundColor: '#7bd2c6',
                     borderColor: '#54b6a9',
                     borderWidth: 1,
                     borderRadius: 6,
                 }]
             },
             options: {
                 responsive: true,
                 scales: { y: { beginAtZero: true, ticks: { stepSize: 200 } } },
                 plugins: { legend: { display: true }, title: { display: true, text: title } }
             }
         });
    }

    // Toggle de submenús en sidebar
    document.querySelectorAll('.group-toggle').forEach(btn => {
        btn.addEventListener('click', () => {
            const group = btn.closest('.nav-group');
            if (group) group.classList.toggle('open');
        });
    });

    // Marcar activo y abrir grupo según currentPage
    (function markActive() {
        const page = window.currentPage || '';
        if (!page) return;
        // Buscar en todo el sidebar, no solo submenús
        const link = document.querySelector(`.sidebar a[data-page="${page}"]`);
        if (link) {
            link.classList.add('active');
            // El LI directo (puede ser item de lista principal o de submenu)
            const li = link.closest('li');
            if (li) li.classList.add('active');
            
            // Si está dentro de un submenú, activar el grupo padre
            const group = link.closest('.nav-group');
            if (group) {
                group.classList.add('open');
                group.classList.add('active-group');
            }
        }
    })();
});