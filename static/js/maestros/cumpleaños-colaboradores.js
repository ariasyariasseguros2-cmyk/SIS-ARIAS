document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('birthday-form');
    const tbody = document.getElementById('birthday-rows');
    if (!form || !tbody) return;

    const saveButton = form.querySelector('button[type="submit"]');
    const nameInput = document.getElementById('birthday-name');
    const areaInput = document.getElementById('birthday-area');
    const dateInput = document.getElementById('birthday-date');
    const datePreview = document.getElementById('birthday-date-preview');
    const searchInput = document.getElementById('birthday-search');
    const clearSearchButton = document.getElementById('birthday-clear-search');
    const monthSelect = document.getElementById('birthday-month');
    const emptyState = document.getElementById('birthday-empty-state');
    const emptyTitle = document.getElementById('birthday-empty-title');
    const emptyCopy = document.getElementById('birthday-empty-copy');
    const noResults = document.getElementById('birthday-no-results');
    const tableWrap = document.querySelector('.birthday-table-wrap');
    const toast = document.getElementById('birthday-toast');
    const today = new Date();
    const dateFormatter = new Intl.DateTimeFormat('es-PE', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
    });
    let toastTimer;

    const todayIso = [
        today.getFullYear(),
        String(today.getMonth() + 1).padStart(2, '0'),
        String(today.getDate()).padStart(2, '0')
    ].join('-');
    dateInput.max = todayIso;

    function parseDate(value) {
        const match = /^(\d{4})-(\d{2})-(\d{2})/.exec((value || '').trim());
        if (match) {
            return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
        }

        const parsed = new Date(value);
        return Number.isNaN(parsed.getTime()) ? null : parsed;
    }

    function initials(name) {
        return name
            .trim()
            .split(/\s+/)
            .filter(Boolean)
            .slice(0, 2)
            .map(function (part) { return part.charAt(0).toLocaleUpperCase('es'); })
            .join('') || '?';
    }

    function nextBirthday(date) {
        if (!date) return null;

        const month = date.getMonth();
        const day = date.getDate();
        let next = new Date(today.getFullYear(), month, day);
        const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate());
        if (next < todayStart) {
            next = new Date(today.getFullYear() + 1, month, day);
        }
        return next;
    }

    function daysUntil(date) {
        const next = nextBirthday(date);
        if (!next) return null;
        const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate());
        return Math.round((next - todayStart) / 86400000);
    }

    function updateRow(row) {
        const name = row.querySelector('.birthday-person-name');
        const area = row.querySelector('.birthday-area-cell');
        const dateCell = row.querySelector('.birthday-date-cell');
        const avatar = row.querySelector('.birthday-avatar');
        const countdownCell = row.querySelector('.birthday-countdown-cell');
        const date = parseDate(row.dataset.date);

        if (name && avatar) avatar.textContent = initials(name.textContent);
        if (dateCell && date) dateCell.textContent = dateFormatter.format(date);
        row.dataset.search = [
            name ? name.textContent : '',
            area ? area.textContent : '',
            dateCell ? dateCell.textContent : ''
        ].join(' ').toLocaleLowerCase('es');
        row.dataset.month = date ? String(date.getMonth() + 1) : '';

        if (!countdownCell) return;
        countdownCell.textContent = '';
        const remainingDays = daysUntil(date);
        if (remainingDays === null) {
            countdownCell.textContent = '—';
            return;
        }

        const badge = document.createElement('span');
        badge.className = 'birthday-countdown' + (remainingDays === 0 ? ' is-today' : '');
        if (remainingDays === 0) {
            badge.innerHTML = '<i class="bi bi-balloon-heart-fill" aria-hidden="true"></i> ¡Hoy!';
        } else if (remainingDays === 1) {
            badge.innerHTML = '<i class="bi bi-gift" aria-hidden="true"></i> Mañana';
        } else {
            badge.innerHTML = '<i class="bi bi-clock" aria-hidden="true"></i> ' + remainingDays + ' días';
        }
        countdownCell.appendChild(badge);
        row.dataset.nextDate = nextBirthday(date).getTime();
    }

    function rows() {
        return Array.from(tbody.querySelectorAll('.birthday-row'));
    }

    function updateSummary() {
        const allRows = rows();
        const monthCount = allRows.filter(function (row) {
            const date = parseDate(row.dataset.date);
            return date && date.getMonth() === today.getMonth();
        }).length;
        const soonCount = allRows.filter(function (row) {
            const date = parseDate(row.dataset.date);
            const days = daysUntil(date);
            return days !== null && days <= 30;
        }).length;

        document.getElementById('birthday-total').textContent = allRows.length;
        document.getElementById('birthday-month-total').textContent = monthCount;
        document.getElementById('birthday-soon-total').textContent = soonCount;
        document.getElementById('birthday-count-pill').textContent =
            allRows.length + (allRows.length === 1 ? ' persona' : ' personas');
    }

    function applyFilters() {
        const query = searchInput.value.trim().toLocaleLowerCase('es');
        const selectedMonth = monthSelect.value;
        const allRows = rows();
        let visibleCount = 0;

        allRows.forEach(function (row) {
            const matchesQuery = !query || row.dataset.search.includes(query);
            const matchesMonth = !selectedMonth || row.dataset.month === selectedMonth;
            const visible = matchesQuery && matchesMonth;
            row.hidden = !visible;
            if (visible) visibleCount += 1;
        });

        const hasRecords = allRows.length > 0;
        emptyState.hidden = hasRecords;
        noResults.hidden = !hasRecords || visibleCount > 0;
        if (tableWrap) tableWrap.classList.toggle('is-empty', !hasRecords);
        if (hasRecords && visibleCount === 0) {
            emptyTitle.textContent = 'No encontramos resultados';
            emptyCopy.textContent = 'Prueba con otro nombre, área o mes.';
        } else {
            emptyTitle.textContent = 'Aún no hay cumpleaños en la lista';
            emptyCopy.textContent = 'Agrega el primero con el formulario y aquí aparecerán las fechas para celebrar.';
        }

        document.getElementById('birthday-results-count').textContent =
            'Mostrando ' + visibleCount + (visibleCount === 1 ? ' persona' : ' personas');
        clearSearchButton.hidden = !query;
        updateSummary();
    }

    function sortRows() {
        rows()
            .sort(function (first, second) {
                return Number(first.dataset.nextDate || Infinity) -
                    Number(second.dataset.nextDate || Infinity);
            })
            .forEach(function (row) { tbody.appendChild(row); });
    }

    function showToast(message) {
        toast.textContent = message;
        toast.hidden = false;
        window.clearTimeout(toastTimer);
        toastTimer = window.setTimeout(function () { toast.hidden = true; }, 4200);
    }

    function makeRow(name, area, dateValue) {
        const row = document.createElement('tr');
        row.className = 'birthday-row';
        row.dataset.date = dateValue;

        const personCell = document.createElement('td');
        personCell.className = 'birthday-person-cell';
        const avatar = document.createElement('span');
        avatar.className = 'birthday-avatar';
        avatar.setAttribute('aria-hidden', 'true');
        const personName = document.createElement('span');
        personName.className = 'birthday-person-name';
        personName.textContent = name;
        personCell.append(avatar, personName);

        const areaCell = document.createElement('td');
        areaCell.className = 'birthday-area-cell';
        areaCell.textContent = area || 'Sin área';

        const dateCell = document.createElement('td');
        dateCell.className = 'birthday-date-cell';
        const countdownCell = document.createElement('td');
        countdownCell.className = 'birthday-countdown-cell';

        row.append(personCell, areaCell, dateCell, countdownCell);
        updateRow(row);
        return row;
    }

    rows().forEach(updateRow);
    sortRows();
    applyFilters();

    dateInput.addEventListener('input', function () {
        const date = parseDate(dateInput.value);
        const previewText = date
            ? 'Se mostrará como ' + dateFormatter.format(date) + '.'
            : 'Elige una fecha para ver cómo se mostrará.';
        datePreview.querySelector('span').textContent = previewText;
    });

    searchInput.addEventListener('input', applyFilters);
    monthSelect.addEventListener('change', applyFilters);
    clearSearchButton.addEventListener('click', function () {
        searchInput.value = '';
        searchInput.focus();
        applyFilters();
    });

    form.addEventListener('submit', function (event) {
        event.preventDefault();
        if (!form.reportValidity()) return;

        const name = nameInput.value.trim();
        const area = areaInput.value.trim();
        const dateValue = dateInput.value;
        const selectedDate = parseDate(dateValue);
        if (!name || !selectedDate || dateValue > todayIso) {
            showToast('Revisa el nombre y la fecha de nacimiento antes de agregar.');
            return;
        }

        const duplicate = rows().some(function (row) {
            return row.querySelector('.birthday-person-name').textContent.trim().toLocaleLowerCase('es') ===
                    name.toLocaleLowerCase('es') &&
                row.dataset.date === dateValue;
        });
        if (duplicate) {
            showToast('Ese cumpleaños ya aparece en la lista.');
            return;
        }

        saveButton.disabled = true;
        saveButton.innerHTML = '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Guardando...';
        fetch(form.dataset.saveUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                nombre: name,
                area: area,
                fecha_nacimiento: dateValue
            })
        })
            .then(async function (response) {
                const result = await response.json();
                if (!response.ok || !result.ok) {
                    throw new Error(result.error || 'No se pudo guardar el cumpleaños.');
                }
                return result.colaborador;
            })
            .then(function (colaborador) {
                tbody.appendChild(makeRow(
                    colaborador.nombre,
                    colaborador.area,
                    colaborador.fecha_nacimiento
                ));
                sortRows();
                form.reset();
                datePreview.querySelector('span').textContent = 'Elige una fecha para ver cómo se mostrará.';
                searchInput.value = '';
                monthSelect.value = '';
                applyFilters();
                showToast('Cumpleaños guardado. El equipo verá el aviso el día correspondiente.');
                nameInput.focus();
            })
            .catch(function (error) {
                showToast(error.message || 'No se pudo guardar el cumpleaños. Inténtalo nuevamente.');
            })
            .finally(function () {
                saveButton.disabled = false;
                saveButton.innerHTML = '<i class="bi bi-plus-lg" aria-hidden="true"></i> Guardar cumpleaños';
            });
    });
});
