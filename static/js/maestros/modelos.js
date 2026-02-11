document.addEventListener('DOMContentLoaded', function(){
    const tableBody = document.querySelector('#table-modelos tbody');
    if(!tableBody) return;
    const modal = new bootstrap.Modal(document.getElementById('modalAdd'));
    const perPageSelect = document.getElementById('per-page-select');
    const paginationEl = document.getElementById('pagination');
    const infoEl = document.getElementById('maestros-info');
    let currentPage = 1;

    function renderPagination(page, pages){
        paginationEl.innerHTML = '';
        if(pages <= 1) return;
        const ul = document.createElement('ul'); ul.className='pagination mb-0';
        function item(p,label,disabled){ const li=document.createElement('li'); li.className='page-item'+(p===page?' active':'')+(disabled?' disabled':''); const a=document.createElement('a'); a.className='page-link'; a.href='#'; a.textContent=label; a.addEventListener('click',(e)=>{ e.preventDefault(); if(!disabled){ currentPage=p; load(); } }); li.appendChild(a); return li; }
        ul.appendChild(item(Math.max(1,page-1),'«', page<=1));
        const start=Math.max(1,page-2); const end=Math.min(pages,page+2);
        for(let p=start;p<=end;p++) ul.appendChild(item(p,p,false));
        ul.appendChild(item(Math.min(pages,page+1),'»', page>=pages));
        paginationEl.appendChild(ul);
    }

    async function load(){
        const per = perPageSelect.value || '20';
        const perQuery = per === 'all' ? 'all' : per;
        const res = await fetch(`/api/maestros/modelos?page=${currentPage}&per_page=${perQuery}`);
        const data = await res.json();
        const rows = (data && data.rows) || data || [];
        tableBody.innerHTML = '';
        rows.forEach(r => {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td>${r.id}</td><td>${r.marca_nombre}</td><td>${r.nombre}</td><td>${r.estado}</td><td><button class="btn btn-sm btn-danger btn-del" data-id="${r.id}">Eliminar</button></td>`;
            tableBody.appendChild(tr);
        });
        document.querySelectorAll('.btn-del').forEach(b=>b.addEventListener('click', async (e)=>{
            if(!confirm('Eliminar este registro?')) return;
            const id = e.target.dataset.id;
            await fetch('/api/maestros/modelos/'+id, { method: 'DELETE' });
            load();
        }));

        if(data && data.ok !== undefined){
            const total = data.total || 0;
            const page = data.page || 1;
            const pages = data.pages || 1;
            const perVal = data.per_page === 'all' ? total : Number(data.per_page || per);
            const startIndex = total === 0 ? 0 : ((page - 1) * perVal) + 1;
            const endIndex = Math.min(page * perVal, total);
            infoEl.textContent = `Mostrando ${startIndex} - ${endIndex} de ${total}`;
            renderPagination(page,pages);
        } else { infoEl.textContent=''; paginationEl.innerHTML=''; }
    }

    async function loadMarcas(){
        const r = await fetch('/api/maestros/marcas?per_page=all');
        const js = await r.json();
        const marcas = (js && js.rows) ? js.rows : (Array.isArray(js) ? js : []);
        const sel = document.getElementById('select-marca');
        sel.innerHTML = '';
        marcas.forEach(m=>{ const o = document.createElement('option'); o.value = m.id; o.textContent = m.nombre; sel.appendChild(o); });
    }

    document.getElementById('btn-add').addEventListener('click', async ()=>{ await loadMarcas(); modal.show(); });
    document.getElementById('save-btn').addEventListener('click', async ()=>{
        const marca = document.getElementById('select-marca').value;
        const nombre = document.getElementById('input-nombre').value;
        if(!nombre.trim()){ alert('Nombre requerido'); return; }
        await fetch('/api/maestros/modelos', { method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ marca_id: marca, nombre }) });
        modal.hide();
        load();
    });

    perPageSelect.addEventListener('change', ()=>{ currentPage = 1; load(); });

    load();
});
