document.addEventListener('DOMContentLoaded', () => {
  // Base URL para recargar con distintos parámetros
  const card = document.querySelector('.card[data-base-url]');
  const baseUrl = card?.getAttribute('data-base-url') || window.location.pathname;

  // Sincronizar tamaño de página con la URL
  const params = new URLSearchParams(window.location.search);
  const pageSizeSel = document.getElementById('page-size') || document.querySelector('.toolbar-pagesize select');
  if (pageSizeSel) {
    const current = parseInt(params.get('per_page') || '20', 10);
    pageSizeSel.value = String(current);
    pageSizeSel.addEventListener('change', () => {
      params.set('per_page', pageSizeSel.value);
      params.set('page', '1'); // reset a primera página al cambiar tamaño
      window.location.href = `${baseUrl}?${params.toString()}`;
    });
  }

  // Búsqueda local dentro de la página
  const searchInput = document.querySelector('.toolbar-search input');
  const table = document.getElementById('polizasListTable');
  if (searchInput && table) {
    const rows = Array.from(table.querySelectorAll('tbody tr'));
    searchInput.addEventListener('input', () => {
      const q = searchInput.value.trim().toLowerCase();
      rows.forEach(tr => {
        tr.style.display = tr.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
    });
  }

  // Manejo de clicks en acciones (chips o dropdown items)
  const listTable = document.getElementById('polizasListTable');
  const cardContainer = document.querySelector('.card[data-base-url]'); // It has the urls

  if (listTable && cardContainer) {
    const primasUrl = cardContainer.getAttribute('data-primas-url');
    const cuotasUrl = cardContainer.getAttribute('data-cuotas-url');

    listTable.addEventListener('click', (e) => {
      // Modificado para aceptar cualquier elemento con data-action, no solo chips
      const target = e.target.closest('[data-action]');
      if (!target) return;

      const action = target.getAttribute('data-action');
      const row = target.closest('tr');
      const poliza = row?.getAttribute('data-poliza');

      console.log('Click en acción:', action, poliza, 'PrimasURL:', primasUrl);

      if (!poliza) {
        console.warn('No se encontró póliza en la fila');
        return;
      }

      if (action === 'primas' && primasUrl) {
        window.location.href = `${primasUrl}?poliza=${encodeURIComponent(poliza)}`;
      } else if (action === 'extracto' && cuotasUrl) {
         window.location.href = `${cuotasUrl}?poliza=${encodeURIComponent(poliza)}`;
      } else if (action === 'renovar') {
        // Handled by renovar-poliza.js
      } else if (action === 'editar' || action === 'editar-poliza') {
        // Si el elemento es un enlace <a> con href válido (que no sea #), dejamos que navegue
        const href = target.getAttribute('href');
        if (href && href !== '#' && !href.includes('javascript:')) {
            // Check if href has ID. If it's just '...?id=' (empty), we might want to intercept.
            if (href.includes('id=') && !href.endsWith('id=')) {
                return; // Let browser handle navigation
            }
        }

        // Fallback: usar data-id de la fila si el enlace falla o es una acción JS
        const id = row?.getAttribute('data-id');
        if (id) {
            window.location.href = `${baseUrl.replace('listado-poliza', 'editar-poliza')}?id=${id}`;
        } else {
            console.warn('No se encontró ID de póliza para editar');
            // If href exists but id is missing in row, maybe try following href anyway?
            if (href && href !== '#') return; 
            
            alert('No se puede editar: falta el ID de la póliza (asegúrese de actualizar la BD).');
        }
      } else {
        console.log('Acción no implementada:', action, poliza);
        // Implementar anular, siniestros, etc.
      }
    });
  }
});
