// app/static/js/dashboard-websocket.js

/**
 * Глобальная функция-обработчик для всех входящих WebSocket-событий на дашборде.
 * @param {object} data - Данные, полученные от сервера.
 */
function dashboardSocketHandler(data) {
    console.log('WebSocket event received:', data.event, data);
    const mainTable = document.getElementById('main-dashboard-table');
    if (!mainTable) return;

    switch (data.event) {
        case 'part_created':
            addPartRow(data.safe_key, data.html);
            updateProductCounters(data.product_designation, 1);
            break;
        case 'part_deleted':
            removePartRow(data.part_id);
            updateProductCounters(data.product_designation, -1);
            break;
        case 'part_updated':
        case 'stage_completed':
            // Предполагаем, что функция updatePartRow существует в другом файле
            if (typeof updatePartRow === 'function') {
                updatePartRow(data);
            }
            break;
        case 'bulk_delete':
            if (data.deleted_parts) {
                data.deleted_parts.forEach(part => {
                    removePartRow(part.part_id);
                    updateProductCounters(part.product_designation, -1);
                });
            }
            break;
    }
}

/**
 * Добавляет новую строку детали в раскрытый список изделия.
 * @param {string} safeKey - Безопасный ключ для ID родительской строки.
 * @param {string} html - HTML-код новой строки.
 */
function addPartRow(safeKey, html) {
    const detailsRow = document.getElementById(`details-for-${safeKey}`);
    if (!detailsRow || detailsRow.classList.contains('hidden')) {
        invalidateCacheForProduct(safeKey);
        return;
    }
    const contentCell = detailsRow.querySelector('.details-placeholder');
    let tableBody = contentCell.querySelector('tbody');

    if (!tableBody) {
        const productRow = document.querySelector(`.product-row[data-safe-key="${safeKey}"]`);
        if (productRow && typeof loadDetailsForProduct === 'function') {
            invalidateCacheForProduct(safeKey);
            loadDetailsForProduct(productRow, productRow.dataset.productDesignation, safeKey);
        }
        return;
    }

    const tempContainer = document.createElement('tbody');
    tempContainer.innerHTML = html;
    const newRow = tempContainer.firstChild;
    if (newRow) {
        tableBody.prepend(newRow);
    }
}

/**
 * Удаляет строку детали из таблицы.
 * @param {string} partId - ID удаляемой детали.
 */
function removePartRow(partId) {
    const encodedPartId = encodeURIComponent(partId).replace(/[.'()]/g, c => '%' + c.charCodeAt(0).toString(16));
    const row = document.getElementById(`part-row-${encodedPartId}`);
    if (row) {
        row.style.backgroundColor = '#fee2e2';
        row.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        row.style.opacity = '0';
        row.style.transform = 'translateX(-20px)';
        setTimeout(() => row.remove(), 500);
    }
}

/**
 * Обновляет счетчик деталей для конкретного изделия.
 * @param {string} productDesignation - Наименование изделия.
 * @param {number} delta - Изменение счетчика (+1 или -1).
 */
function updateProductCounters(productDesignation, delta) {
    const productRow = document.querySelector(`[data-product-designation="${productDesignation}"]`);
    if (productRow) {
        const countCell = productRow.children[1];
        const currentCount = parseInt(countCell.textContent, 10);
        if (!isNaN(currentCount)) {
            const newCount = currentCount + delta;
            countCell.textContent = newCount;
            if (newCount === 0) {
                productRow.style.opacity = '0.5';
            } else {
                productRow.style.opacity = '1';
            }
        }
    }
}

/**
 * Сбрасывает кэш для конкретного изделия, чтобы при следующем открытии данные загрузились заново.
 * @param {string} safeKey - Безопасный ключ изделия.
 */
function invalidateCacheForProduct(safeKey) {
    const productRow = document.querySelector(`.product-row[data-safe-key="${safeKey}"]`);
    if (productRow) {
        const productDesignation = productRow.dataset.productDesignation;
        if (window.dashboardDetailsCache) {
            Object.keys(window.dashboardDetailsCache)
                .filter(key => key.startsWith(productDesignation))
                .forEach(key => delete window.dashboardDetailsCache[key]);
        }
    }
}