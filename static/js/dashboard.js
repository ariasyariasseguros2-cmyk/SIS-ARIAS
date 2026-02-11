// Guardar estado previo en caso de errores
window.addEventListener('error', function(ev){
    console.error('Global JS error caught:', ev.error || ev.message, ev);
});
window.addEventListener('unhandledrejection', function(ev){
    console.error('Unhandled promise rejection:', ev.reason);
});

document.addEventListener('DOMContentLoaded', () => {
    try {
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
            const li = btn.closest('.nav-group');
            // Si el grupo ya viene marcado como open en el DOM, no lo cerramos
            btn.addEventListener('click', () => {
                const isOpen = li.classList.contains('open');
                if (isOpen) {
                    li.classList.remove('open', 'active-group');
                } else {
                    // cerrar otros grupos (si se desea comportamiento acordeón)
                    document.querySelectorAll('.nav-group.open').forEach(g => {
                        g.classList.remove('open', 'active-group');
                    });
                    li.classList.add('open', 'active-group');
                }
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

        document.addEventListener('click', (e) => {
            try {
                const a = e.target.closest('a[data-page]');
                if (!a) return;
                const href = a.href;
                if (!href) return;

                e.preventDefault();

                if (location.href === href) return;

                location.href = href;
            } catch (err) {
                console.error('nav fallback error', err);
            }
        });

    } catch (err) {
        console.error('dashboard init error', err);
    }
});