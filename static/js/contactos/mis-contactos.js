document.addEventListener('DOMContentLoaded', function () {
  const qInput = document.getElementById('search-q');
  const tbody = document.getElementById('mis-contactos-tbody');
  if (!qInput || !tbody) return;

  let timer = null;
  function escapeHtml(s){
    return s ? s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : '';
  }
  function render(rows){
    if (!rows || rows.length === 0) {
      tbody.innerHTML = '<tr><td colspan="3" class="text-center">No se encontraron contactos.</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map(function(r){
      var nombre = escapeHtml(r.razon_social || '');
      var tel = escapeHtml(r.telefono || '');
      var email = escapeHtml(r.email || '');
      var mailto = '<a href="mailto:' + encodeURIComponent(r.email || '') + '">' + email + '</a>';
      return '<tr>' +
               '<td>' + nombre + '</td>' +
               '<td>' + tel + '</td>' +
               '<td>' + mailto + '</td>' +
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

  // carga inicial
  fetchData(qInput.value || '');
});

