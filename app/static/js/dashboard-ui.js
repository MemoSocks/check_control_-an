// app/static/js/dashboard-ui.js

document.addEventListener('DOMContentLoaded', function() {
    
    window.dashboardDetailsCache = {};

    const mainTable = document.getElementById('main-dashboard-table');
    const bulkActionsBar = document.getElementById('bulk-actions-bar');
    const bulkActionsCounter = document.getElementById('bulk-actions-counter');
    const bulkClearButton = document.getElementById('bulk-clear-selection');
    const bulkDeleteForm = document.getElementById('bulk-delete-form');
    const bulkPrintForm = document.getElementById('bulk-print-form');
    
    // --- НАЧАЛО ИЗМЕНЕНИЯ: Получаем шаблон контекстного меню ---
    const contextMenu = document.getElementById('context-menu');
    // --- КОНЕЦ ИЗМЕНЕНИЯ ---

    const searchInput = document.getElementById('searchInput');
    const responsibleFilter = document.getElementById('responsibleFilter');
    let searchTimeout;

    function updateBulkActionsPanel() {
        if (!mainTable || !bulkActionsBar || !bulkActionsCounter) return;
        const selectedCheckboxes = mainTable.querySelectorAll('.part-checkbox:checked');
        const count = selectedCheckboxes.length;
        bulkActionsCounter.textContent = `Выбрано: ${count}`;
        bulkActionsBar.classList.toggle('translate-y-full', count === 0);
    }

    function prepareFormForSubmit(form) {
        form.querySelectorAll('input[name="part_ids"]').forEach(input => input.remove());
        const selectedCheckboxes = mainTable.querySelectorAll('.part-checkbox:checked');
        selectedCheckboxes.forEach(cb => {
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = 'part_ids';
            hiddenInput.value = cb.value;
            form.appendChild(hiddenInput);
        });
        return selectedCheckboxes.length;
    }

    function handleFilterChange() {
        Object.keys(window.dashboardDetailsCache).forEach(key => delete window.dashboardDetailsCache[key]);
        document.querySelectorAll('.product-row').forEach(productRow => {
            const detailsRow = document.getElementById(`details-for-${productRow.dataset.safeKey}`);
            if (detailsRow && !detailsRow.classList.contains('hidden')) {
                if (typeof loadDetailsForProduct === 'function') {
                    loadDetailsForProduct(
                        productRow,
                        productRow.dataset.productDesignation,
                        productRow.dataset.safeKey
                    );
                }
            }
        });
    }
    
    // --- НАЧАЛО ИЗМЕНЕНИЯ: Логика для контекстного меню ---
    function showContextMenu(event, targetRow) {
        event.preventDefault();
        
        // Очищаем предыдущее меню и получаем CSRF-токен
        contextMenu.innerHTML = '';
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

        // Создаем пункты меню на основе data-атрибутов
        const menuItems = [
            { text: 'История', url: targetRow.dataset.historyUrl },
            { text: 'Редактировать', url: targetRow.dataset.editUrl },
            { text: 'Скачать QR', url: targetRow.dataset.qrUrl, isForm: true },
            { text: 'Удалить', url: targetRow.dataset.deleteUrl, isForm: true, isDestructive: true }
        ];

        menuItems.forEach(item => {
            if (item.url) {
                let menuItem;
                if (item.isForm) {
                    // Создаем форму для действий, требующих POST
                    menuItem = document.createElement('form');
                    menuItem.action = item.url;
                    menuItem.method = 'post';
                    menuItem.className = 'block';
                    if (item.isDestructive) {
                        menuItem.classList.add('form-confirm');
                        menuItem.dataset.text = `Удалить деталь ${targetRow.dataset.partId}?`;
                    }
                    
                    const csrfInput = document.createElement('input');
                    csrfInput.type = 'hidden';
                    csrfInput.name = 'csrf_token';
                    csrfInput.value = csrfToken;

                    const button = document.createElement('button');
                    button.type = 'submit';
                    button.textContent = item.text;
                    button.className = 'block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100';
                    if (item.isDestructive) button.classList.add('hover:text-red-700');
                    
                    menuItem.appendChild(csrfInput);
                    menuItem.appendChild(button);
                } else {
                    // Создаем обычную ссылку
                    menuItem = document.createElement('a');
                    menuItem.href = item.url;
                    menuItem.textContent = item.text;
                    menuItem.className = 'block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100';
                }
                contextMenu.appendChild(menuItem);
            }
        });

        // Позиционируем и показываем меню
        contextMenu.style.left = `${event.pageX}px`;
        contextMenu.style.top = `${event.pageY}px`;
        contextMenu.classList.remove('hidden');

        // Закрываем меню по клику в любом другом месте
        document.addEventListener('click', () => contextMenu.classList.add('hidden'), { once: true });
    }
    // --- КОНЕЦ ИЗМЕНЕНИЯ ---

    // === РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ СОБЫТИЙ ===

    if (bulkDeleteForm) {
        bulkDeleteForm.addEventListener('submit', function(event) {
            event.preventDefault();
            const selectedCount = prepareFormForSubmit(bulkDeleteForm);
            if (selectedCount === 0) {
                if (window.Swal) Swal.fire('Нет выбранных элементов', 'Пожалуйста, выберите хотя бы одну деталь.', 'info');
                return;
            }
            if (window.Swal) {
                Swal.fire({
                    title: 'Вы уверены?', text: `Вы собираетесь удалить ${selectedCount} деталей. Это действие необратимо!`,
                    icon: 'warning', showCancelButton: true, confirmButtonColor: '#d33',
                    cancelButtonColor: '#3085d6', confirmButtonText: 'Да, удалить!', cancelButtonText: 'Отмена'
                }).then((result) => { if (result.isConfirmed) { bulkDeleteForm.submit(); } });
            } else {
                bulkDeleteForm.submit();
            }
        });
    }

    if (bulkPrintForm) {
        bulkPrintForm.addEventListener('submit', function(event) {
            if (prepareFormForSubmit(bulkPrintForm) === 0) {
                event.preventDefault();
                if (window.Swal) Swal.fire('Нет выбранных элементов', 'Пожалуйста, выберите хотя бы одну деталь для печати.', 'info');
            }
        });
    }

    if (bulkClearButton) {
        bulkClearButton.addEventListener('click', () => {
            mainTable.querySelectorAll('.part-checkbox:checked, .select-all-parts:checked').forEach(cb => cb.checked = false);
            updateBulkActionsPanel();
        });
    }

    if (mainTable) {
        mainTable.addEventListener('click', function(event) {
            const productRow = event.target.closest('.product-row');
            if (productRow) {
                const productToggle = productRow.querySelector('.product-toggle');
                const productDesignation = productRow.dataset.productDesignation;
                const safeKey = productRow.dataset.safeKey;
                const detailsRow = document.getElementById(`details-for-${safeKey}`);
                
                if (!detailsRow || !productToggle) return;

                detailsRow.classList.toggle('hidden');
                const isHidden = detailsRow.classList.contains('hidden');
                productToggle.innerHTML = isHidden ? `${productDesignation} ▾` : `${productDesignation} ▴`;

                if (!isHidden) {
                    if (typeof loadDetailsForProduct === 'function') {
                        loadDetailsForProduct(productRow, productDesignation, safeKey);
                    }
                }
            }
        });

        mainTable.addEventListener('change', function(event) {
            if (event.target.matches('.part-checkbox, .select-all-parts')) {
                if (event.target.matches('.select-all-parts')) {
                    event.target.closest('.details-table')?.querySelectorAll('.part-checkbox').forEach(cb => cb.checked = event.target.checked);
                }
                updateBulkActionsPanel();
            }
        });

        // --- НАЧАЛО ИЗМЕНЕНИЯ: Добавляем обработчик правого клика ---
        mainTable.addEventListener('contextmenu', function(event) {
            const targetRow = event.target.closest('.context-menu-target');
            if (targetRow) {
                showContextMenu(event, targetRow);
            }
        });
        // --- КОНЕЦ ИЗМЕНЕНИЯ ---
    }
    
    if (searchInput) {
        searchInput.addEventListener('keyup', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(handleFilterChange, 500);
        });
    }

    if (responsibleFilter) {
        responsibleFilter.addEventListener('change', handleFilterChange);
    }
    
    const style = document.createElement('style');
    style.innerHTML = `
        @keyframes highlight-fade-in {
            from { background-color: #d1fae5; opacity: 0; }
            50% { background-color: #d1fae5; opacity: 1; }
            to { background-color: transparent; opacity: 1; }
        }
        .highlight-new {
            animation: highlight-fade-in 3s ease-out;
        }
        @keyframes highlight-fade-update {
            from { background-color: #e0e7ff; }
            to { background-color: transparent; }
        }
        .highlight-update {
            animation: highlight-fade-update 3s ease-out;
        }
    `;
    document.head.appendChild(style);
});