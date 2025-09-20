// app/static/js/main.js

/**
 * Обрабатывает клик по кнопке "изменить" ответственного.
 * Загружает форму в модальное окно, отправляет данные и обновляет страницу.
 * @param {Event} event - Событие клика.
 */
async function handleChangeResponsible(event) {
    const button = event.target;
    const formUrl = button.dataset.formUrl;
    const actionUrl = button.dataset.actionUrl;

    if (!formUrl || !actionUrl) {
        console.error('Не найдены URL для формы или действия в data-атрибутах кнопки.');
        return;
    }

    try {
        const response = await fetch(formUrl);
        if (!response.ok) throw new Error('Не удалось загрузить форму.');
        const formHtml = await response.text();

        Swal.fire({
            title: 'Смена ответственного',
            html: formHtml,
            // --- НАЧАЛО ИСПРАВЛЕНИЯ: Убираем стандартные кнопки Swal ---
            showConfirmButton: false, // Скрываем стандартную кнопку "OK"
            showCancelButton: false,  // Скрываем стандартную кнопку "Cancel"
            // --- КОНЕЦ ИСПРАВЛЕНИЯ ---
            customClass: {
                // Добавляем кастомный класс, чтобы можно было стилизовать кнопки из HTML
                popup: 'responsible-swal'
            }
        });
    } catch (error) {
        Swal.fire('Ошибка', `Не удалось загрузить форму: ${error.message}`, 'error');
    }
}

/**
 * Обрабатывает клик по кнопке "Редактировать" примечание.
 * Открывает модальное окно с полем для редактирования текста.
 * @param {Event} event - Событие клика.
 */
async function handleEditNote(event) {
    const button = event.target;
    const noteId = button.dataset.noteId;
    const actionUrl = button.dataset.actionUrl;
    const noteTextElement = document.getElementById(`note-text-${noteId}`);

    if (!noteId || !actionUrl || !noteTextElement) {
        console.error('Не найдены необходимые data-атрибуты или элемент текста для примечания.');
        return;
    }

    const currentText = noteTextElement.textContent.trim();

    const { value: newText } = await Swal.fire({
        title: 'Редактировать примечание',
        input: 'textarea',
        inputValue: currentText,
        showCancelButton: true,
        confirmButtonText: 'Сохранить',
        cancelButtonText: 'Отмена',
        inputValidator: (value) => {
            if (!value) {
                return 'Текст примечания не может быть пустым!'
            }
        }
    });

    if (newText && newText.trim() !== currentText) {
        const formData = new FormData();
        formData.append('text', newText);
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        formData.append('csrf_token', csrfToken);
        
        try {
            const response = await fetch(actionUrl, {
                method: 'POST',
                body: formData,
            });
            const result = await response.json();
            if (response.ok && result.status === 'success') {
                noteTextElement.innerHTML = result.new_text.replace(/\n/g, '<br>');
                Swal.fire('Сохранено!', 'Примечание успешно обновлено.', 'success');
            } else {
                throw new Error(result.message || 'Неизвестная ошибка');
            }
        } catch (error) {
            Swal.fire('Ошибка', `Не удалось сохранить примечание: ${error.message}`, 'error');
        }
    }
}

/**
 * Отслеживает изменения в форме и активирует/деактивирует кнопку отправки.
 */
function handleFormChange() {
    const forms = document.querySelectorAll('.disable-on-no-change');
    forms.forEach(form => {
        const submitButton = form.querySelector('input[type="submit"], button[type="submit"]');
        if (!submitButton) return;

        submitButton.disabled = true;
        submitButton.classList.add('opacity-50', 'cursor-not-allowed');

        form.addEventListener('input', () => {
            submitButton.disabled = false;
            submitButton.classList.remove('opacity-50', 'cursor-not-allowed');
        });
    });
}

document.addEventListener('DOMContentLoaded', () => {
    // WebSocket
    const socket = io();
    socket.on('connect', () => {
        console.log('WebSocket connected!');
    });
    socket.on('notification', (data) => {
        if (typeof dashboardSocketHandler === 'function') {
            dashboardSocketHandler(data);
        }
        Swal.fire({
            toast: true,
            position: 'top-end',
            icon: 'info',
            title: data.message,
            showConfirmButton: false,
            timer: 4000,
            timerProgressBar: true,
        });
    });

    // Обработчик для кнопок подтверждения с data-атрибутом
    document.body.addEventListener('submit', function(event) {
        const form = event.target;
        if (form.matches('.form-confirm')) {
            event.preventDefault();
            const text = form.dataset.text || 'Вы уверены, что хотите выполнить это действие?';
            Swal.fire({
                title: 'Подтвердите действие',
                text: text,
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#d33',
                cancelButtonColor: '#3085d6',
                confirmButtonText: 'Да, выполнить!',
                cancelButtonText: 'Отмена',
            }).then((result) => {
                if (result.isConfirmed) {
                    form.submit();
                }
            });
        }
    });
    
    // Делегирование событий для динамически добавляемых элементов
    document.body.addEventListener('click', function(event) {
        if (event.target && event.target.id === 'change-responsible-btn') {
            handleChangeResponsible(event);
        }
        if (event.target && event.target.classList.contains('edit-note-btn')) {
            handleEditNote(event);
        }
        // --- НАЧАЛО ИСПРАВЛЕНИЯ: Обработчик для кнопок в модальном окне ---
        if (event.target && event.target.matches('.swal2-confirm')) {
            // Имитируем клик по скрытой кнопке submit внутри модального окна
            const form = document.getElementById('change-responsible-form-modal');
            if (form) {
                const hiddenSubmit = form.querySelector('input[type="submit"]');
                if (hiddenSubmit) {
                    hiddenSubmit.click();
                }
            }
        }
        // --- КОНЕЦ ИСПРАВЛЕНИЯ ---
    });

    handleFormChange();
});