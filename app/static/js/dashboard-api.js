// app/static/js/dashboard-api.js

/**
 * Асинхронно загружает с сервера и отображает список деталей для конкретного изделия.
 * @param {HTMLElement} productRow - HTML-элемент строки изделия (<tr>), по которой кликнули.
 * @param {string} productDesignation - Наименование изделия.
 * @param {string} safeKey - Безопасный ключ для ID строки с деталями.
 */
async function loadDetailsForProduct(productRow, productDesignation, safeKey) {
    const detailsRow = document.getElementById(`details-for-${safeKey}`);
    const contentCell = detailsRow.querySelector('.details-placeholder');
    
    const cacheKey = `${productDesignation}_${document.getElementById('searchInput').value}_${document.getElementById('responsibleFilter').value}`;
    
    if (window.dashboardDetailsCache && window.dashboardDetailsCache[cacheKey]) {
        contentCell.innerHTML = window.dashboardDetailsCache[cacheKey];
        return;
    }

    contentCell.innerHTML = `<div class="p-8 text-center text-gray-500">Загрузка...</div>`;
    
    try {
        const params = new URLSearchParams();
        const searchTerm = document.getElementById('searchInput').value;
        const responsibleId = document.getElementById('responsibleFilter').value;

        if (searchTerm) params.append('search', searchTerm);
        if (responsibleId) params.append('responsible_id', responsibleId);

        const response = await fetch(`/api/parts/${encodeURIComponent(productDesignation)}?${params.toString()}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const data = await response.json();
        const { parts, permissions } = data;
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

        if (parts.length === 0) {
            contentCell.innerHTML = '<div class="p-8 text-center text-gray-500">Детали, соответствующие фильтру, не найдены.</div>';
        } else {
            const rowsHtml = parts.map(part => {
                const progress = part.quantity_total > 0 ? (part.quantity_completed / part.quantity_total) * 100 : 0;
                const progressText = `${part.quantity_completed} из ${part.quantity_total}`;
                
                const routeHtml = part.route_stages.length > 0 ? `
                    <div class="route-timeline flex items-center space-x-1">
                        ${part.route_stages.map((stage, index) => {
                            let stageClass = 'bg-gray-300'; // pending
                            let title = `Ожидание: ${stage.name} (${stage.qty_done}/${part.quantity_total})`;
                            if (stage.status === 'completed') {
                                stageClass = 'bg-green-500';
                                title = `Выполнено: ${stage.name} (${stage.qty_done}/${part.quantity_total})`;
                            } else if (stage.status === 'in_progress') {
                                stageClass = 'bg-blue-500 animate-pulse';
                                title = `В процессе: ${stage.name} (${stage.qty_done}/${part.quantity_total})`;
                            }
                            const barHtml = `<div class="w-full h-1.5 ${stageClass} rounded-full" title="${title}"></div>`;
                            const separatorHtml = index < part.route_stages.length - 1 ? '<div class="w-2 h-px bg-gray-300"></div>' : '';
                            return `<div class="flex-1 flex items-center">${barHtml}${separatorHtml}</div>`;
                        }).join('')}
                    </div>
                ` : '<span class="text-gray-400 italic">Маршрут не назначен</span>';

                const progressBarHtml = `<div class="w-full bg-gray-200 rounded-full h-2.5"><div class="bg-blue-600 h-2.5 rounded-full" style="width: ${progress}%"></div></div><small>${progressText}</small>`;
                const encodedPartId = encodeURIComponent(part.part_id).replace(/[.'()]/g, c => '%' + c.charCodeAt(0).toString(16));

                // --- НАЧАЛО ИСПРАВЛЕНИЯ: Генерируем data-атрибуты корректно ---
                const dataAttrs = `
                    data-history-url="${part.history_url}"
                    data-edit-url="${permissions?.can_edit ? part.edit_url : ''}"
                    data-qr-url="${permissions?.can_generate_qr ? part.qr_url : ''}"
                    data-delete-url="${permissions?.can_delete ? part.delete_url : ''}"
                    data-part-id="${part.part_id}"
                `;
                // --- КОНЕЦ ИСПРАВЛЕНИЯ ---

                return `<tr class="hover:bg-gray-100 context-menu-target" id="part-row-${encodedPartId}" ${dataAttrs}>
                            <td class="px-6 py-4"><input type="checkbox" value="${part.part_id}" class="part-checkbox rounded border-gray-300"></td>
                            <td class="px-6 py-4"><a href="${part.history_url}" class="text-blue-600 hover:underline font-medium">${part.part_id}</a></td>
                            <td class="px-6 py-4 text-sm text-gray-900 name-cell">${part.name}</td>
                            <td class="px-6 py-4 text-sm text-gray-500 material-cell">${part.material}</td>
                            <td class="px-6 py-4 text-sm route-cell">${routeHtml}</td>
                            <td class="px-6 py-4 progress-cell">${progressBarHtml}</td>
                            <td class="px-6 py-4 text-sm text-gray-500 responsible-cell">${part.responsible_user}</td>
                        </tr>`;
            }).join('');
            
            contentCell.innerHTML = `<table class="min-w-full details-table">
                                        <thead class="bg-gray-100">
                                            <tr>
                                                <th class="px-6 py-3 w-12"><input type="checkbox" class="select-all-parts rounded border-gray-300" title="Выбрать все"></th>
                                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Обозначение</th>
                                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Наименование</th>
                                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Материал</th>
                                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase w-1/5">Маршрут</th>
                                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Прогресс (шт.)</th>
                                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ответственный</th>
                                            </tr>
                                        </thead>
                                        <tbody class="bg-white divide-y divide-gray-200">${rowsHtml}</tbody>
                                    </table>`;
        }
        
        if (window.dashboardDetailsCache) {
            window.dashboardDetailsCache[cacheKey] = contentCell.innerHTML;
        }
    } catch (error) {
        console.error('Ошибка загрузки деталей:', error);
        contentCell.innerHTML = '<div class="p-8 text-center text-red-500">Ошибка загрузки. Попробуйте обновить страницу.</div>';
    }
}

/**
 * Обновляет одну строку детали, если она видна на экране.
 * @param {object} data - Данные для обновления.
 */
function updatePartRow(data) {
    const encodedPartId = encodeURIComponent(data.part_id).replace(/[.'()]/g, c => '%' + c.charCodeAt(0).toString(16));
    const row = document.getElementById(`part-row-${encodedPartId}`);
    if (!row) return;

    if (data.progress_html) row.querySelector('.progress-cell')?.innerHTML = data.progress_html;
    if (data.responsible_user) row.querySelector('.responsible-cell')?.textContent = data.responsible_user;
    if (data.name) row.querySelector('.name-cell').textContent = data.name;
    if (data.material) row.querySelector('.material-cell').textContent = data.material;
    if (data.size) row.querySelector('.size-cell').textContent = data.size;

    row.classList.add('highlight-update');
    setTimeout(() => row.classList.remove('highlight-update'), 3000);
}