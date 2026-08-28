document.addEventListener('DOMContentLoaded', function () {
  const qInput = document.getElementById('search-q');
  const tbody = document.getElementById('mis-contactos-tbody');
  if (!qInput || !tbody) return;

  let timer = null;

  function escapeHtml(s){
    return s ? s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : '';
  }

  function cleanPhoneNumber(phone) {
    return (phone || '').replace(/\s|-|\(|\)/g, '');
  }

  function getInitials(name){
    const n = (name || 'C').trim();
    if (!n) return 'C';
    const words = n.split(/\s+/).filter(Boolean);
    if (words.length === 1) return words[0].substring(0,2).toUpperCase();
    return (words[0][0] + words[words.length-1][0]).toUpperCase().substring(0,2);
  }

  function getAvatarColor(name){
    const colors = ['#3b82f6','#6366f1','#8b5cf6','#ec4899','#f43f5e','#f59e0b','#10b981','#06b6d4','#0ea5e9','#14b8a6'];
    let hash = 0;
    for (let i=0; i<name.length; i++) hash = name.charCodeAt(i) + ((hash<<5)-hash);
    return colors[Math.abs(hash) % colors.length];
  }

  function render(rows, startIdx){
    startIdx = startIdx || 1;
    if (!rows || rows.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="6" class="mc-empty">' +
          '<i class="bi bi-inbox mc-empty-icon"></i>' +
          '<p class="mc-empty-text">No se encontraron contactos.</p>' +
          '<a href="/menu/mis-contactos" class="mc-empty-back">Ver todos los contactos</a>' +
        '</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map(function(r, i){
      const idx = startIdx + i;
      const nombre = escapeHtml(r.razon_social || 'Sin nombre');
      const tel = escapeHtml(r.telefono || '');
      const email = escapeHtml(r.email || '');
      const numero_documento = escapeHtml(r.numero_documento || '');
      const cleanTel = cleanPhoneNumber(r.telefono || '');
      const avColor = getAvatarColor(nombre);
      const avInitials = getInitials(nombre);

      const telCell = tel
        ? ('<a href="tel:' + escapeHtml(r.telefono || '') + '" class="mc-tel-link" title="Llamar">' +
             '<i class="bi bi-telephone-fill mc-tel-icon"></i>' + tel +
           '</a>')
        : '<span class="mc-muted">—</span>';

      const emailCell = email
        ? ('<a href="mailto:' + email + '" class="mc-contacto-email" title="Enviar correo">' + email + '</a>')
        : '<span class="mc-contacto-email mc-muted">Sin email</span>';

      const docCell = numero_documento
        ? ('<span class="mc-doc-val">' + numero_documento + '</span>')
        : '<span class="mc-muted">—</span>';

      let waBadge;
      if (cleanTel) {
        waBadge =
          '<a href="https://wa.me/' + cleanTel + '" target="_blank" class="mc-badge mc-badge-whatsapp" title="Contactar por WhatsApp">' +
            '<i class="bi bi-whatsapp mc-badge-dot"></i>Disponible' +
          '</a>';
      } else {
        waBadge =
          '<span class="mc-badge mc-badge-none">' +
            '<i class="bi bi-dash-circle mc-badge-dot"></i>Sin número' +
          '</span>';
      }

      let menuItems = '<li><h6 class="dropdown-header small text-muted p-0 px-3 mb-1 text-uppercase">' + nombre + '</h6></li>';
      let hasMenu = false;
      if (tel) {
        menuItems += '<li><a class="dropdown-item d-flex align-items-center gap-2" href="tel:' + escapeHtml(r.telefono || '') + '"><i class="bi bi-telephone-fill mc-menu-icon-tel"></i> Llamar</a></li>' +
                     '<li><a class="dropdown-item d-flex align-items-center gap-2" href="https://wa.me/' + cleanTel + '" target="_blank"><i class="bi bi-whatsapp mc-menu-icon-wa"></i> WhatsApp</a></li>';
        hasMenu = true;
      }
      if (email) {
        menuItems += '<li><a class="dropdown-item d-flex align-items-center gap-2" href="mailto:' + email + '"><i class="bi bi-envelope-fill mc-menu-icon-em"></i> Enviar email</a></li>';
        hasMenu = true;
      }
      if (!hasMenu) {
        menuItems += '<li><span class="dropdown-item text-muted small"><i class="bi bi-info-circle me-2"></i>Sin datos de contacto</span></li>';
      }

      return '' +
        '<tr class="mc-row" data-index="' + idx + '">' +
          '<td class="mc-td-check">' +
            '<input type="checkbox" class="mc-check mc-row-check" data-row="' + idx + '">' +
          '</td>' +
          '<td class="mc-td-contacto">' +
            '<div class="mc-contacto-cell">' +
              '<div class="mc-avatar" style="background-color:' + avColor + ';">' +
                '<span class="mc-avatar-text">' + avInitials + '</span>' +
              '</div>' +
              '<div class="mc-contacto-info">' +
                '<div class="mc-contacto-name">' + nombre + '</div>' +
                '<div class="mc-contacto-sub">' + emailCell + '</div>' +
              '</div>' +
            '</div>' +
          '</td>' +
          '<td class="mc-td-doc">' + docCell + '</td>' +
          '<td class="mc-td-tel">' + telCell + '</td>' +
          '<td class="mc-td-whatsapp">' + waBadge + '</td>' +
          '<td class="mc-td-actions">' +
            '<div class="dropdown">' +
              '<button class="mc-action-btn" type="button" data-bs-toggle="dropdown" aria-expanded="false">' +
                '<i class="bi bi-three-dots"></i>' +
              '</button>' +
              '<ul class="dropdown-menu dropdown-menu-end shadow border-0 py-2 mc-action-menu">' + menuItems + '</ul>' +
            '</div>' +
          '</td>' +
        '</tr>';
    }).join('');
  }

  function fetchData(q){
    const url = '/menu/mis-contactos/search?q=' + encodeURIComponent(q || '');
    fetch(url, { headers: { 'Accept': 'application/json' } })
      .then(function(resp){ return resp.ok ? resp.json() : Promise.reject('bad'); })
      .then(function(json){
        render(json || []);
        const master = document.getElementById('checkAll');
        if (master) master.checked = false;
      })
      .catch(function(){ render([]); });
  }

  qInput.addEventListener('input', function(e){
    clearTimeout(timer);
    timer = setTimeout(function(){ fetchData(e.target.value.trim()); }, 300);
  });

  if (qInput.value) {
    fetchData(qInput.value);
  }
});
