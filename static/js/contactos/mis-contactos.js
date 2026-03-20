document.addEventListener('DOMContentLoaded', function () {
  const qInput = document.getElementById('search-q');
  const tbody = document.getElementById('mis-contactos-tbody');
  if (!qInput || !tbody) return;

  let timer = null;
  
  function escapeHtml(s){
    return s ? s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : '';
  }

  function cleanPhoneNumber(phone) {
    // Elimina espacios, guiones, paréntesis para usar en WhatsApp
    return (phone || '').replace(/\s|-|\(|\)/g, '');
  }

  function render(rows){
    if (!rows || rows.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center py-4"><i class="bi bi-inbox text-muted" style="font-size: 2rem;"></i><p class="text-muted mt-2">No se encontraron contactos.</p></td></tr>';
      return;
    }
    tbody.innerHTML = rows.map(function(r){
      var nombre = escapeHtml(r.razon_social || '');
      var tel = escapeHtml(r.telefono || '');
      var email = escapeHtml(r.email || '');
      var numero_documento = escapeHtml(r.numero_documento || '');
      
      // Teléfono como hipervínculo
      var telCell = tel ? '<a href="tel:' + escapeHtml(r.telefono || '') + '" class="link-phone" title="Llamar">' + tel + '</a>' : '<span class="text-muted">—</span>';
      
      // Email como hipervínculo
      var emailCell = email ? '<a href="mailto:' + escapeHtml(r.email || '') + '" class="link-email" title="Enviar correo">' + email + '</a>' : '<span class="text-muted">—</span>';
      
      // Botón de WhatsApp solo en Acciones
      var whatsappBtn = '';
      if (r.telefono) {
        var cleanPhone = cleanPhoneNumber(r.telefono);
        whatsappBtn = '<a href="https://wa.me/' + cleanPhone + '" target="_blank" class="whatsapp-chip" title="Contactar por WhatsApp"><i class="bi bi-whatsapp"></i> WhatsApp</a>';
      }
      
      return '<tr>' +
               '<td class="text-start fw-500">' + nombre + '</td>' +
               '<td class="text-center text-muted small">' + numero_documento + '</td>' +
               '<td class="text-center">' + telCell + '</td>' +
               '<td class="text-center">' + emailCell + '</td>' +
               '<td class="text-center">' + whatsappBtn + '</td>' +
             '</tr>';
    }).join('');
  }

  function fetchData(q){
    var url = '/menu/mis-contactos/search?q=' + encodeURIComponent(q || '');
    fetch(url, { headers: { 'Accept': 'application/json' } })
      .then(function(resp){ return resp.ok ? resp.json() : Promise.reject('bad'); })
      .then(function(json){ render(json || []); })
      .catch(function(){ render([]); });
  }

  qInput.addEventListener('input', function(e){
    clearTimeout(timer);
    timer = setTimeout(function(){ fetchData(e.target.value.trim()); }, 300);
  });

  // Carga inicial de búsqueda dinámica (solo si hay query o siempre hacer refresh)
  if (qInput.value) {
    fetchData(qInput.value);
  }
});

