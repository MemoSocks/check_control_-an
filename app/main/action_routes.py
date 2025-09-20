# app/main/action_routes.py

from flask import Blueprint, request, redirect, url_for, flash, render_template, jsonify
from sqlalchemy import func

from app import db
from flask_login import current_user, login_required
from app.models import (Part, Stage, PartNote, Permission, StatusHistory,
                        StatusType, RouteStage, AuditLog)
from app.admin.action_forms import ConfirmStageQuantityForm, AddNoteForm, ReworkScrapForm
from app.services import part_status_service as pss
from app.services.part_utils_service import _send_websocket_notification

# Создаем новый блюпринт специально для действий
action_bp = Blueprint('actions', __name__)


@action_bp.route('/confirm_stage/<path:part_id>/<int:stage_id>', methods=['POST'])
def confirm_stage(part_id, stage_id):
    """Обрабатывает POST-запрос на подтверждение (выполнение) этапа."""
    part = db.get_or_404(Part, part_id)
    stage = db.get_or_404(Stage, stage_id)
    form = ConfirmStageQuantityForm()

    if form.validate_on_submit():
        quantity_done = form.quantity.data
        
        operator_name = ""
        if current_user.is_authenticated:
            operator_name = current_user.full_name or current_user.username
        else:
            if not form.operator_name.data or len(form.operator_name.data) < 3:
                flash("Поле 'Ваше ФИО' обязательно для выполнения этапа.", "error")
                return render_template('select_stage.html', part=part, next_stage=stage, form=form, rework_scrap_form=ReworkScrapForm())
            operator_name = form.operator_name.data
        
        completed_on_this_stage = db.session.query(func.sum(StatusHistory.quantity)).filter_by(
            part_id=part.part_id, status=stage.name, status_type=StatusType.COMPLETED
        ).scalar() or 0
        remaining_on_stage = part.quantity_total - completed_on_this_stage
        
        if quantity_done > remaining_on_stage:
            flash(f'Ошибка: Нельзя выполнить {quantity_done} шт. На этом этапе осталось {remaining_on_stage} шт.', 'error')
            # --- ИЗМЕНЕНИЕ: Обновляем url_for ---
            return redirect(url_for('main.main_pages.select_stage', part_id=part.part_id))

        pss.complete_stage(part, stage, quantity_done, operator_name)
        
        notification_message = f"Деталь {part_id} перешла на этап '{stage.name}'. Готово: {quantity_done} шт."
        flash(notification_message, "success")
        _send_websocket_notification('stage_completed', notification_message, {'part_id': part.part_id})
        
        # --- ИЗМЕНЕНИЕ: Обновляем url_for ---
        return redirect(url_for('main.main_pages.dashboard'))

    # --- ИЗМЕНЕНИЕ: Обновляем url_for ---
    return render_template('select_stage.html', part=part, next_stage=stage, form=form, rework_scrap_form=ReworkScrapForm())


@action_bp.route('/handle_action/<path:part_id>/<int:stage_id>', methods=['POST'])
@login_required
def handle_action(part_id, stage_id):
    """Обрабатывает отправку в брак или на доработку."""
    part = db.get_or_404(Part, part_id)
    stage = db.get_or_404(Stage, stage_id)
    form = ReworkScrapForm()

    if form.validate_on_submit():
        action = form.action.data
        quantity = form.quantity.data
        comment = form.comment.data

        if action == 'scrap' and current_user.can(Permission.SEND_TO_SCRAP):
            pss.scrap_part(part, stage, quantity, current_user, comment)
            flash(f'{quantity} шт. детали {part_id} отправлено в брак.', 'error')
        elif action == 'rework' and current_user.can(Permission.SEND_TO_REWORK):
            try:
                pss.rework_part(part, stage, quantity, current_user, comment)
                flash(f'{quantity} шт. детали {part_id} отправлено на доработку.', 'warning')
            except ValueError as e:
                flash(str(e), 'error')
        else:
            flash('Недостаточно прав для выполнения этого действия.', 'error')
    else:
        flash('Произошла ошибка валидации. Убедитесь, что причина указана (минимум 5 символов).', 'error')
        
    # --- ИЗМЕНЕНИЕ: Обновляем url_for ---
    return redirect(url_for('main.main_pages.select_stage', part_id=part_id))


@action_bp.route('/add_note/<path:part_id>', methods=['POST'])
@login_required
def add_note(part_id):
    """Обрабатывает добавление примечания к детали."""
    part = db.get_or_404(Part, part_id)
    form = AddNoteForm()
    
    if part.route_template:
        form.stage.query = db.session.query(Stage).join(RouteStage).filter(
            RouteStage.template_id == part.route_template_id
        ).order_by(Stage.name)
    else:
        form.stage.query = db.session.query(Stage).filter_by(id=-1)

    if form.validate_on_submit():
        stage_obj = form.stage.data
        new_note = PartNote(
            part_id=part.part_id,
            user_id=current_user.id,
            text=form.text.data,
            stage_id=stage_obj.id if stage_obj else None
        )
        db.session.add(new_note)

        log_details = f"К детали '{part.part_id}' добавлено примечание."
        db.session.add(AuditLog(user_id=current_user.id, action="Добавлено примечание",
                                details=log_details, category='part', part_id=part.part_id))
        db.session.commit()
        flash('Примечание успешно добавлено.', 'success')
    else:
        error_messages = [e for field, errors in form.errors.items() for e in errors]
        flash('Ошибка: ' + ' '.join(error_messages), 'error')
        
    # --- ИЗМЕНЕНИЕ: Обновляем url_for ---
    return redirect(url_for('main.main_pages.history', part_id=part.part_id))


@action_bp.route('/edit_note/<int:note_id>', methods=['POST'])
@login_required
def edit_note(note_id):
    """Обрабатывает AJAX-запрос на редактирование примечания."""
    note = db.get_or_404(PartNote, note_id)
    if note.user_id != current_user.id and not current_user.is_admin():
        return jsonify({'status': 'error', 'message': 'Нет прав'}), 403

    new_text = request.form.get('text')
    if new_text and new_text.strip():
        note.text = new_text
        log_details = f"В детали '{note.part_id}' изменено примечание (ID: {note.id})."
        db.session.add(AuditLog(user_id=current_user.id, action="Изменено примечание",
                                details=log_details, category='management', part_id=note.part_id))
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Примечание обновлено.', 'new_text': new_text})
    else:
        return jsonify({'status': 'error', 'message': 'Текст не может быть пустым.'}), 400


@action_bp.route('/delete_note/<int:note_id>', methods=['POST'])
@login_required
def delete_note(note_id):
    """Обрабатывает POST-запрос на удаление примечания."""
    note = db.get_or_404(PartNote, note_id)
    if note.user_id != current_user.id and not current_user.is_admin():
        flash('У вас нет прав для удаления этого примечания.', 'error')
        # --- ИЗМЕНЕНИЕ: Обновляем url_for ---
        return redirect(url_for('main.main_pages.history', part_id=note.part_id))

    part_id = note.part_id
    log_details = f"В детали '{part_id}' удалено примечание (ID: {note.id})."
    db.session.add(AuditLog(user_id=current_user.id, action="Удалено примечание",
                            details=log_details, category='management', part_id=part_id))

    db.session.delete(note)
    db.session.commit()
    flash('Примечание удалено.', 'success')
    # --- ИЗМЕНЕНИЕ: Обновляем url_for ---
    return redirect(url_for('main.main_pages.history', part_id=part_id))