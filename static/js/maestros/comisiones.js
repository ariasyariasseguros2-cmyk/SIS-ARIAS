document.addEventListener('DOMContentLoaded', function(){
  try {
    const tbody = document.getElementById('comisiones-tbody');
    if (!tbody) return;

    const searchInput = document.getElementById('comisiones-search');
    const infoEl = document.getElementById('comisiones-info');
    const pagEl = document.getElementById('comisiones-pagination');

    const allRows = Array.from(tbody.querySelectorAll('tr'));
    // Guardar snapshot original
    const data = allRows.map(tr => ({
      html: tr.innerHTML,
      text: tr.textContent.toLowerCase().replace(/\s+/g, ' ').trim()
    }));

    let filtered = data.slice();
    const perPage = 20;
    let currentPage = 1;

    function renderPage(page){
      currentPage = page;
      const total = filtered.length;
      const pages = Math.max(1, Math.ceil(total / perPage));
      const p = Math.min(Math.max(1, page), pages);
      const start = (p - 1) * perPage;
      const end = Math.min(start + perPage, total);

      tbody.innerHTML = '';
      for (let i = start; i < end; i++){
        const tr = document.createElement('tr');
        tr.innerHTML = filtered[i].html;
        tbody.appendChild(tr);
      }

      // Info
      if (infoEl){
        if (total === 0){
          infoEl.textContent = 'Mostrando 0 - 0 de 0';
        } else {
          infoEl.textContent = `Mostrando ${start + 1} - ${end} de ${total}`;
        }
      }

      // Pagination
      if (pagEl){
        pagEl.innerHTML = '';
        if (pages <= 1) return;
        const ul = document.createElement('ul');
        ul.className = 'pagination pagination-sm mb-0';

        function addItem(label, pageNum, disabled, active){
          const li = document.createElement('li');
          li.className = 'page-item';
          if (disabled) li.classList.add('disabled');
          if (active) li.classList.add('active');
          const a = document.createElement('a');
          a.className = 'page-link';
          a.href = '#';
          a.textContent = label;
          a.addEventListener('click', (e)=>{
            e.preventDefault();
            if (!disabled && !active){
              renderPage(pageNum);
            }
          });
          li.appendChild(a);
          ul.appendChild(li);
        }

        addItem('«', Math.max(1, p - 1), p <= 1, false);

        const windowSize = 5;
        let startPage = Math.max(1, p - Math.floor(windowSize/2));
        let endPage = Math.min(pages, startPage + windowSize - 1);
        if (endPage - startPage + 1 < windowSize){
          startPage = Math.max(1, endPage - windowSize + 1);
        }

        for (let i = startPage; i <= endPage; i++){
          addItem(String(i), i, false, i === p);
        }

        addItem('»', Math.min(pages, p + 1), p >= pages, false);
        pagEl.appendChild(ul);
      }
    }

    function applyFilter(query){
      const q = (query || '').toLowerCase().trim();
      if (!q){
        filtered = data.slice();
      } else {
        filtered = data.filter(r => r.text.includes(q));
      }
      renderPage(1);
    }

    // Debounce para el buscador
    let t = null;
    if (searchInput){
      searchInput.addEventListener('input', (e)=>{
        const val = e.target.value;
        if (t) clearTimeout(t);
        t = setTimeout(()=>applyFilter(val), 180);
      });
    }

    // Inicio
    renderPage(1);
  } catch (err){
    console.error('comisiones.js error', err);
  }
});

