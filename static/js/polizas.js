(function () {
  document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('polizasSearch');
    const table = document.getElementById('polizasTable');
    const rows = table ? Array.from(table.querySelectorAll('tbody tr')) : [];

    function filterRows(term) {
      const q = term.trim().toLowerCase();
      rows.forEach(tr => {
        const text = tr.textContent.toLowerCase();
        tr.style.display = text.includes(q) ? '' : 'none';
      });
    }

    input?.addEventListener('input', (e) => filterRows(e.target.value));

    // Delegación de eventos para acciones en la tabla
    table?.addEventListener('click', (e) => {
      // Buscamos el elemento disparador que tenga data-action (chip, button, link)
      const actionEl = e.target.closest('[data-action]');
      
      // Si no hay acción, o si es un link con href válido que no sea #, dejamos que el navegador actúe
      if (!actionEl) return;
      if (actionEl.tagName === 'A' && actionEl.getAttribute('href') && actionEl.getAttribute('href') !== '#') {
        return;
      }

      // Prevenir comportamiento default para botones o links con href="#"
      e.preventDefault();

      const action = actionEl.dataset.action;
      const row = actionEl.closest('tr');
      if (!row) return;

      // Extraer datos de la fila
      // 1: Contratante, 2: Asegurado, 3: Cía, 4: Ram, 5: Prod, 6: Poliza,
      // 7: Moneda, 8: Vig Inicio, 9: Vig Fin, 10: Sub Agente, 11: M.Asegurada
      const pick = (n) => row.querySelector(`td:nth-child(${n})`)?.textContent?.trim() || '';

      const data = {
        contratante: pick(1),
        asegurado: pick(2),
        cia: pick(3),
        ramo: pick(4),
        producto: pick(5),
        poliza: pick(6),
        materiaAsegurada: pick(11),
        vig_inicio: pick(8),
        vig_fin: pick(9)
      };

      console.log(`Ejecutando acción: ${action}`, data);

      switch (action) {
        case 'primas':
          const primasUrl = table.getAttribute('data-primas-url');
          if (primasUrl && data.poliza) {
            window.location.href = `${primasUrl}?poliza=${encodeURIComponent(data.poliza)}`;
          }
          break;

        case 'renovar':
          if (typeof window.openRenovarPolizaModal === 'function') {
            window.openRenovarPolizaModal(data);
          } else {
            alert('El modal de renovación no está cargado correctamente.');
          }
          break;

        case 'extracto':
            alert(`Ver Extracto de Póliza: ${data.poliza}`);
            break;

        case 'siniestros':
          window.location.href = `/menu/siniestros-poliza?poliza=${encodeURIComponent(data.poliza)}`;
          break;

        default:
          alert(`Acción "${action.toUpperCase()}" para la póliza ${data.poliza}`);
          break;
      }
    });
  });
})();
