document.addEventListener('DOMContentLoaded', function(){
    try{
        const tableBody = document.querySelector('#table-usos tbody');
        if(!tableBody) return;
        const modalEl = document.getElementById('modalAdd');
        const modal = new bootstrap.Modal(modalEl);
        const perPageSelect = document.getElementById('per-page-select');
        const paginationEl = document.getElementById('pagination');
        const infoEl = document.getElementById('maestros-info');
        let currentPage = 1;

        function renderPagination(page, pages){
            paginationEl.innerHTML = '';
            if(pages <= 1) return;
            const ul = document.createElement('ul'); ul.className = 'pagination mb-0';
            function item(p, label, disabled){
                const li = document.createElement('li'); li.className = 'page-item' + (p===page? ' active':'') + (disabled? ' disabled':'');
                const a = document.createElement('a'); a.className='page-link'; a.href='#'; a.textContent = label; a.addEventListener('click', (e)=>{ e.preventDefault(); if(!disabled){ currentPage = p; load(); } }); li.appendChild(a); return li;
            }
            ul.appendChild(item(Math.max(1,page-1), '«', page<=1));
            const start = Math.max(1, page-2); const end = Math.min(pages, page+2);
            for(let p=start;p<=end;p++) ul.appendChild(item(p, p, false));
            ul.appendChild(item(Math.min(pages,page+1), '»', page>=pages));
            paginationEl.appendChild(ul);
        }

        async function load(){
            try{
                const per = perPageSelect.value || '20';
                const perQuery = per === 'all' ? 'all' : per;
                const res = await fetch(`/api/maestros/usos?page=${currentPage}&per_page=${perQuery}`);
                const data = await res.json();
                const rows = (data && data.rows) || data || [];
                tableBody.innerHTML = '';
                (rows||[]).forEach(r=>{ const tr = document.createElement('tr'); tr.innerHTML = `<td>${r.id}</td><td>${r.nombre}</td><td>${r.estado}</td><td><button class="btn btn-sm btn-danger btn-del" data-id="${r.id}">Eliminar</button></td>`; tableBody.appendChild(tr); });
                document.querySelectorAll('.btn-del').forEach(b=>b.addEventListener('click', async (e)=>{ try{ if(!confirm('Eliminar este registro?')) return; const id = e.target.dataset.id; await fetch('/api/maestros/usos/'+id, { method: 'DELETE' }); load(); }catch(err){ console.error(err); alert('Error eliminando'); } }));

                if(data && data.ok !== undefined){
                    const total = data.total || 0;
                    const page = data.page || 1;
                    const pages = data.pages || 1;
                    const perVal = data.per_page === 'all' ? total : Number(data.per_page || per);
                    const startIndex = total === 0 ? 0 : ((page - 1) * perVal) + 1;
                    const endIndex = Math.min(page * perVal, total);
                    infoEl.textContent = `Mostrando ${startIndex} - ${endIndex} de ${total}`;
                    renderPagination(page, pages);
                } else { infoEl.textContent = ''; paginationEl.innerHTML = ''; }
            }catch(err){ console.error('load usos error', err); }
        }

        perPageSelect.addEventListener('change', ()=>{ currentPage = 1; load(); });

        const btnAdd = document.getElementById('btn-add');
        const saveBtn = document.getElementById('save-btn');
        if(btnAdd) btnAdd.addEventListener('click', ()=>{ modal.show(); });
        if(saveBtn) saveBtn.addEventListener('click', async ()=>{
            try{
                const nombre = (document.getElementById('input-nombre')||{}).value || '';
                if(!nombre.trim()){ alert('Nombre requerido'); return; }
                await fetch('/api/maestros/usos', { method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ nombre }) });
                modal.hide(); load();
            }catch(err){ console.error(err); alert('Error guardando'); }
        });

        load();
    }catch(e){ console.error('usos.js init error', e); }
});
