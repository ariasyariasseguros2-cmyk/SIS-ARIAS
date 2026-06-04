document.addEventListener('DOMContentLoaded', function(){
  try {
    const tbody = document.getElementById('comisiones-tbody');
    if (!tbody) return;

    const searchInput = document.getElementById('comisiones-search');
    const infoEl = document.getElementById('comisiones-info');
    const pagEl = document.getElementById('comisiones-pagination');
    const modalEl = document.getElementById('comisiones-modal');
    const modal = modalEl && window.bootstrap ? new bootstrap.Modal(modalEl) : null;
    const modalTitleEl = document.getElementById('comisiones-modal-title');
    const saveBtn = document.getElementById('comisiones-save-btn');
    const addBtn = document.getElementById('comisiones-add-btn');

    let currentMode = null;
    let currentId = null;

    const fields = {
      ramo_nombre: document.getElementById('com-ramo-nombre'),
      ramo_abreviacion: document.getElementById('com-ramo-abrev'),
      ramo_codigo: document.getElementById('com-ramo-codigo'),
      ramo_grupo: document.getElementById('com-ramo-grupo'),
      producto: document.getElementById('com-producto'),
      producto_abrev: document.getElementById('com-producto-abrev'),
      producto_codigo: document.getElementById('com-producto-codigo'),
      producto_grupo: document.getElementById('com-producto-grupo'),
      pos_eps: document.getElementById('com-pos-eps'),
      pos_vsr: document.getElementById('com-pos-vsr'),
      pos_sr: document.getElementById('com-pos-sr'),
      pacifico: document.getElementById('com-pacifico'),
      sanitas: document.getElementById('com-sanitas'),
      protecta: document.getElementById('com-protecta'),
      mapfre: document.getElementById('com-mapfre'),
      crecer: document.getElementById('com-crecer'),
      ohio_natural: document.getElementById('com-ohio-natural'),
      grandia_eps: document.getElementById('com-grandia-eps'),
      qualitas: document.getElementById('com-qualitas'),
      factor: document.getElementById('com-factor')
    };

    const allRows = Array.from(tbody.querySelectorAll('tr'));
    const data = allRows.map(tr => ({
      html: tr.innerHTML,
      text: tr.textContent.toLowerCase().replace(/\s+/g, ' ').trim(),
      id: tr.getAttribute('data-id') || null
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
        if (filtered[i].id) tr.setAttribute('data-id', filtered[i].id);
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

    function fillFormFromRow(tr, mode){
      const cells = Array.from(tr.querySelectorAll('td'));
      if (!cells.length) return;
      if (fields.ramo_nombre) fields.ramo_nombre.value = cells[0] ? cells[0].textContent.trim() : '';
      if (fields.ramo_abreviacion) fields.ramo_abreviacion.value = cells[1] ? cells[1].textContent.trim() : '';
      if (fields.ramo_codigo) fields.ramo_codigo.value = cells[2] ? cells[2].textContent.trim() : '';
      if (fields.ramo_grupo) fields.ramo_grupo.value = cells[3] ? cells[3].textContent.trim() : '';
      if (fields.producto) fields.producto.value = cells[4] ? cells[4].textContent.trim() : '';
      if (fields.producto_abrev) fields.producto_abrev.value = cells[5] ? cells[5].textContent.trim() : '';
      if (fields.producto_codigo) fields.producto_codigo.value = cells[6] ? cells[6].textContent.trim() : '';
      if (fields.producto_grupo) fields.producto_grupo.value = cells[7] ? cells[7].textContent.trim() : '';
      if (fields.pos_eps) fields.pos_eps.value = cells[8] ? cells[8].textContent.trim() : '';
      if (fields.pos_vsr) fields.pos_vsr.value = cells[9] ? cells[9].textContent.trim() : '';
      if (fields.pos_sr) fields.pos_sr.value = cells[10] ? cells[10].textContent.trim() : '';
      if (fields.pacifico) fields.pacifico.value = cells[11] ? cells[11].textContent.trim() : '';
      if (fields.sanitas) fields.sanitas.value = cells[12] ? cells[12].textContent.trim() : '';
      if (fields.protecta) fields.protecta.value = cells[13] ? cells[13].textContent.trim() : '';
      if (fields.mapfre) fields.mapfre.value = cells[14] ? cells[14].textContent.trim() : '';
      if (fields.crecer) fields.crecer.value = cells[15] ? cells[15].textContent.trim() : '';
      if (fields.ohio_natural) fields.ohio_natural.value = cells[16] ? cells[16].textContent.trim() : '';
      if (fields.grandia_eps) fields.grandia_eps.value = cells[17] ? cells[17].textContent.trim() : '';
      if (fields.qualitas) fields.qualitas.value = cells[18] ? cells[18].textContent.trim() : '';
      if (fields.factor) fields.factor.value = cells[19] ? cells[19].textContent.trim() : '';
    }

    function clearForm(){
      Object.keys(fields).forEach(k => {
        if (fields[k]) fields[k].value = '';
      });
    }

    if (tbody && modal){
      tbody.addEventListener('click', function(e){
        const btn = e.target.closest('button');
        if (!btn) return;
        const tr = btn.closest('tr');
        if (!tr) return;
        if (btn.classList.contains('com-edit')){
          currentMode = 'editar';
          currentId = tr.getAttribute('data-id') || null;
          fillFormFromRow(tr, 'editar');
          if (modalTitleEl) modalTitleEl.textContent = 'Editar comisión';
          modal.show();
        }
      });
    }

    if (addBtn && modal){
      addBtn.addEventListener('click', function(){
        currentMode = 'insertar';
        currentId = null;
        clearForm();
        if (modalTitleEl) modalTitleEl.textContent = 'Agregar comisión';
        modal.show();
      });
    }

    async function saveComision(){
      if (!currentMode) return;
      const payload = {
          mode: currentMode,
          id: currentId,
          ramo_nombre: fields.ramo_nombre ? fields.ramo_nombre.value : '',
          ramo_abreviacion: fields.ramo_abreviacion ? fields.ramo_abreviacion.value : '',
          ramo_codigo: fields.ramo_codigo ? fields.ramo_codigo.value : '',
          ramo_grupo: fields.ramo_grupo ? fields.ramo_grupo.value : '',
          producto: fields.producto ? fields.producto.value : '',
          producto_abrev: fields.producto_abrev ? fields.producto_abrev.value : '',
          producto_codigo: fields.producto_codigo ? fields.producto_codigo.value : '',
          producto_grupo: fields.producto_grupo ? fields.producto_grupo.value : '',
          pos_eps: fields.pos_eps ? fields.pos_eps.value : '',
          pos_vsr: fields.pos_vsr ? fields.pos_vsr.value : '',
          pos_sr: fields.pos_sr ? fields.pos_sr.value : '',
          pacifico: fields.pacifico ? fields.pacifico.value : '',
          sanitas: fields.sanitas ? fields.sanitas.value : '',
          protecta: fields.protecta ? fields.protecta.value : '',
          mapfre: fields.mapfre ? fields.mapfre.value : '',
          crecer: fields.crecer ? fields.crecer.value : '',
          ohio_natural: fields.ohio_natural ? fields.ohio_natural.value : '',
          grandia_eps: fields.grandia_eps ? fields.grandia_eps.value : '',
          qualitas: fields.qualitas ? fields.qualitas.value : '',
          factor: fields.factor ? fields.factor.value : ''
        };
      try{
        const res = await fetch('/api/maestros/comisiones', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!data || data.ok !== true){
          const msg = data && data.error ? data.error : 'Error guardando comisión';
          alert(msg);
          return;
        }
        if (modal) modal.hide();
        clearForm();
        currentMode = null;
        currentId = null;
        window.location.reload();
      } catch(err){
        console.error('save comision error', err);
        alert('Error guardando comisión');
      }
    }

    if (saveBtn && modal){
      saveBtn.addEventListener('click', function(){
        saveComision();
      });
    }
  } catch (err){
    console.error('comisiones.js error', err);
  }
});

