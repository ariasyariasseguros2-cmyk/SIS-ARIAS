document.addEventListener('DOMContentLoaded', function () {
    const modalEl = document.getElementById('modalAjustador');
    const modal = new bootstrap.Modal(modalEl);
    const btnNuevo = document.getElementById('btnNuevoAjustador');
    const btnGuardar = document.getElementById('btnGuardarAjustador');
    const perPageSelect = document.getElementById('per-page-select');
    const paginationEl = document.getElementById('pagination');
    const infoEl = document.getElementById('maestros-info');

    let currentPage = 1;

    function renderPagination(page, pages){
        paginationEl.innerHTML = '';
        if(pages <= 1) return;
        const ul = document.createElement('ul'); ul.className='pagination mb-0';
        function item(p,label,disabled){ const li=document.createElement('li'); li.className='page-item'+(p===page?' active':'')+(disabled?' disabled':''); const a=document.createElement('a'); a.className='page-link'; a.href='#'; a.textContent=label; a.addEventListener('click',(e)=>{ e.preventDefault(); if(!disabled){ currentPage=p; loadAjustadores(); } }); li.appendChild(a); return li; }
        ul.appendChild(item(Math.max(1,page-1),'«', page<=1));
        const start=Math.max(1,page-2); const end=Math.min(pages,page+2);
        for(let p=start;p<=end;p++) ul.appendChild(item(p,p,false));
        ul.appendChild(item(Math.min(pages,page+1),'»', page>=pages));
        paginationEl.appendChild(ul);
    }

    async function loadAjustadores(){
        try{
            const per = perPageSelect ? perPageSelect.value : '20';
            const perQuery = per === 'all' ? 'all' : per;
            const res = await fetch(`/ajustadores/list?page=${currentPage}&per_page=${perQuery}`);
            const data = await res.json();
            const rows = (data && data.rows) ? data.rows : (Array.isArray(data) ? data : []);
            const tbody = document.querySelector('#ajustadoresTable tbody');
            tbody.innerHTML = '';
            // Si la API devuelve rows dentro de data, úsalas; si devuelve un array, ya está en rows
            // Mostrar filas (sin botón eliminar porque no hay endpoint de delete específico)
            rows.forEach(r => {
                const codigo = (r.codigo && String(r.codigo).trim()) ? r.codigo : (r.abreviacion || '');
                const id = r.id || r.idAjustador || '';
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${escapeHtml(r.nombre || '')}</td><td>${escapeHtml(r.abreviacion || '')}</td><td>${escapeHtml(codigo || '')}</td><td><button class="btn btn-sm btn-danger btn-del" data-id="${id}">Eliminar</button></td>`;
                tbody.appendChild(tr);
            });

            // Manejo de info/paginación: si el API devuelve total/page/pages, usarlo; si no, calcular localmente
            if (data && data.ok !== undefined && (data.total !== undefined || data.page !== undefined)) {
                const total = data.total || 0; const page = data.page || 1; const pages = data.pages || 1;
                const perVal = data.per_page === 'all' ? total : Number(data.per_page || per);
                const startIndex = total === 0 ? 0 : ((page - 1) * perVal) + 1;
                const endIndex = Math.min(page * perVal, total);
                infoEl.textContent = `Mostrando ${startIndex} - ${endIndex} de ${total}`;
                renderPagination(page, pages);
            } else {
                // respuesta simple -> mostrar total sin paginación
                const total = (rows && rows.length) ? rows.length : 0;
                infoEl.textContent = total > 0 ? `Mostrando 1 - ${total} de ${total}` : '';
                paginationEl.innerHTML = '';
            }

            // attach delete handlers now
            document.querySelectorAll('.btn-del').forEach(b=>b.addEventListener('click', async (e)=>{
                if(!confirm('Eliminar este registro?')) return;
                const id = e.target.dataset.id;
                if(!id){ alert('No se puede eliminar: id no disponible'); return; }
                try{
                    const res = await fetch(`/api/maestros/ajustadores/${id}`, { method: 'DELETE' });
                    const js = await res.json();
                    if(!js.ok){ console.error('Error deleting ajustador', js); alert('No se pudo eliminar'); }
                    else if(typeof js.deleted !== 'undefined' && Number(js.deleted) === 0){
                        alert('No se eliminó: registro no encontrado o ya eliminado');
                    }
                }catch(err){ console.error('Error eliminando ajustador', err); }
                loadAjustadores();
            }));
        }catch(err){ console.error('Error cargando ajustadores', err); }
    }

    async function submitAjustador(){
        const nombre = document.getElementById('nombre').value.trim();
        const abreviacion = document.getElementById('abreviacion').value.trim();
        const codigo = document.getElementById('codigo').value.trim();
        if(!nombre){ alert('Nombre requerido'); return; }
        const payload = { nombre, abreviacion, codigo };
        try{
            const r = await fetch('/ajustadores/add', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
            const resp = await r.json();
            if(resp.ok){
                modal.hide();
                document.getElementById('nombre').value=''; document.getElementById('abreviacion').value=''; document.getElementById('codigo').value='';
                loadAjustadores();
            } else { console.error('Error guardando ajustador', resp); alert('Error guardando ajustador'); }
        }catch(e){ console.error('Error guardando ajustador', e); alert('Error guardando ajustador'); }
    }

    if(btnNuevo) btnNuevo.addEventListener('click', ()=>{ modal.show(); });
    if(btnGuardar) btnGuardar.addEventListener('click', submitAjustador);
    if(perPageSelect) perPageSelect.addEventListener('change', ()=>{ currentPage = 1; loadAjustadores(); });

    loadAjustadores();
});

function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/[&"'<>]/g, function (a) {
        return { '&': '&amp;', '"': '&quot;', "'": '&#39;', '<': '&lt;', '>': '&gt;' }[a];
    });
}
