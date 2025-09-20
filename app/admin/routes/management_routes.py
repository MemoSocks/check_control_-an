# app/admin/routes/management_routes.py

from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user

# --- ИЗМЕНЕНИЕ: Исправляем пути импорта ---
from app import db
from app.models import Part, AuditLog, RouteTemplate, RouteStage, Stage, Permission, StatusHistory
from app.admin.management_forms import StageDictionaryForm, RouteTemplateForm
from app.admin.utils import permission_required

management_bp = Blueprint('management', __name__)


@management_bp.route('/')
@login_required
def admin_page():
    # Проверяем, есть ли у пользователя хотя бы одно из прав для доступа к админке
    if not any([current_user.can(p) for p in [
        Permission.ADMIN, Permission.VIEW_AUDIT_LOG, Permission.ADD_PARTS,
        Permission.MANAGE_STAGES, Permission.MANAGE_ROUTES, Permission.VIEW_REPORTS
    ]]):
        flash('У вас нет прав для доступа к этому разделу.', 'error')
        return redirect(url_for('main.dashboard'))
    
    return render_template('admin.html')


@management_bp.route('/stages')
@permission_required(Permission.MANAGE_STAGES)
def list_stages():
    """Отображает страницу управления справочником этапов."""
    stages = Stage.query.order_by(Stage.name).all()
    form = StageDictionaryForm()
    # Заполняем форму данными по умолчанию для новых чекбоксов
    form.can_scrap.data = True
    form.can_rework.data = True
    return render_template('list_stages.html', stages=stages, form=form)


@management_bp.route('/stages/add', methods=['POST'])
@permission_required(Permission.MANAGE_STAGES)
def add_stage():
    """Обрабатывает создание нового этапа."""
    form = StageDictionaryForm()
    if form.validate_on_submit():
        stage_name = form.name.data.strip()
        if Stage.query.filter(Stage.name.ilike(stage_name)).first():
            flash('Этап с таким названием уже существует.', 'error')
        else:
            new_stage = Stage(
                name=stage_name,
                can_scrap=form.can_scrap.data,
                can_rework=form.can_rework.data
            )
            db.session.add(new_stage)
            db.session.commit()
            flash(f'Этап "{stage_name}" успешно добавлен в справочник.', 'success')
    return redirect(url_for('admin.management.list_stages'))


@management_bp.route('/stages/edit/<int:stage_id>', methods=['POST'])
@permission_required(Permission.MANAGE_STAGES)
def edit_stage(stage_id):
    """Обрабатывает редактирование существующего этапа."""
    stage = db.get_or_404(Stage, stage_id)
    form = StageDictionaryForm(obj=stage)
    if form.validate_on_submit():
        stage.name = form.name.data.strip()
        stage.can_scrap = form.can_scrap.data
        stage.can_rework = form.can_rework.data
        db.session.commit()
        flash(f'Этап "{stage.name}" успешно обновлен.', 'success')
    else:
        flash('Произошла ошибка при обновлении этапа.', 'error')
    return redirect(url_for('admin.management.list_stages'))


@management_bp.route('/stages/delete/<int:stage_id>', methods=['POST'])
@permission_required(Permission.MANAGE_STAGES)
def delete_stage(stage_id):
    """Обрабатывает удаление этапа."""
    stage = db.get_or_404(Stage, stage_id)
    # Проверяем, не используется ли этап в каком-либо маршруте
    if RouteStage.query.filter_by(stage_id=stage_id).first():
        flash('Нельзя удалить этап, так как он используется в одном или нескольких маршрутах.', 'error')
    else:
        stage_name = stage.name
        db.session.delete(stage)
        db.session.commit()
        flash(f'Этап "{stage_name}" удален из справочника.', 'success')
    return redirect(url_for('admin.management.list_stages'))


@management_bp.route('/routes')
@permission_required(Permission.MANAGE_ROUTES)
def list_routes():
    """Отображает страницу управления технологическими маршрутами."""
    routes = RouteTemplate.query.order_by(RouteTemplate.name).all()
    return render_template('list_routes.html', routes=routes)


@management_bp.route('/routes/add', methods=['GET', 'POST'])
@permission_required(Permission.MANAGE_ROUTES)
def add_route():
    """Обрабатывает создание нового маршрута."""
    form = RouteTemplateForm()
    if form.validate_on_submit():
        try:
            # Если новый маршрут отмечен как "по умолчанию", снимаем этот флаг со старого
            if form.is_default.data:
                current_default = RouteTemplate.query.filter_by(is_default=True).first()
                if current_default:
                    current_default.is_default = False
            
            new_template = RouteTemplate(name=form.name.data, is_default=form.is_default.data)
            db.session.add(new_template)
            # Создаем связи между маршрутом и этапами с сохранением порядка
            for i, stage_id in enumerate(form.stages.data):
                route_stage = RouteStage(template=new_template, stage_id=stage_id, order=i)
                db.session.add(route_stage)

            log_entry = AuditLog(user_id=current_user.id, action="Управление маршрутами", details=f"Создан новый маршрут '{new_template.name}'.", category='management')
            db.session.add(log_entry)
            
            db.session.commit()
            
            flash('Новый технологический маршрут успешно создан.', 'success')
            return redirect(url_for('admin.management.list_routes'))
        except Exception as e:
            db.session.rollback()
            flash(f'Произошла ошибка при создании маршрута: {e}', 'error')
    return render_template('route_form.html', form=form, title='Создать новый маршрут')


@management_bp.route('/routes/edit/<int:route_id>', methods=['GET', 'POST'])
@permission_required(Permission.MANAGE_ROUTES)
def edit_route(route_id):
    """Обрабатывает редактирование существующего маршрута."""
    template = db.get_or_404(RouteTemplate, route_id)
    form = RouteTemplateForm(obj=template)

    if form.validate_on_submit():
        try:
            # Проверяем, не пытаются ли удалить этап, который уже используется в производстве
            original_stage_ids = {rs.stage_id for rs in template.stages}
            new_stage_ids = set(form.stages.data)
            stages_to_remove_ids = original_stage_ids - new_stage_ids

            if stages_to_remove_ids:
                # Ищем детали, которые используют этот маршрут и уже прошли удаляемые этапы
                conflicting_stages_query = db.session.query(Stage.name).join(RouteStage).join(RouteTemplate).join(Part).join(StatusHistory, StatusHistory.part_id == Part.part_id)\
                    .filter(RouteTemplate.id == template.id)\
                    .filter(RouteStage.stage_id.in_(stages_to_remove_ids))\
                    .filter(StatusHistory.status == Stage.name)\
                    .distinct()
                
                conflicting_stages = conflicting_stages_query.all()

                if conflicting_stages:
                    stage_names = ", ".join([f"'{s[0]}'" for s in conflicting_stages])
                    flash(f'Нельзя удалить этап(ы) {stage_names}, так как он(и) уже используется(-ются) в производстве. Сначала измените маршрут у соответствующих деталей.', 'error')
                    return render_template('route_form.html', form=form, title=f'Редактировать: {template.name}')

            # Обновляем флаг "по умолчанию"
            if form.is_default.data:
                current_default = RouteTemplate.query.filter(RouteTemplate.is_default==True, RouteTemplate.id != template.id).first()
                if current_default:
                    current_default.is_default = False

            template.name = form.name.data
            template.is_default = form.is_default.data
            
            # Полностью пересоздаем связи с этапами
            RouteStage.query.filter_by(template_id=template.id).delete()
            for i, stage_id in enumerate(form.stages.data):
                route_stage = RouteStage(template=template, stage_id=stage_id, order=i)
                db.session.add(route_stage)

            log_entry = AuditLog(user_id=current_user.id, action="Управление маршрутами", details=f"Изменен маршрут '{template.name}'.", category='management')
            db.session.add(log_entry)
            
            db.session.commit()
            
            flash('Маршрут успешно обновлен.', 'success')
            return redirect(url_for('admin.management.list_routes'))
        except Exception as e:
            db.session.rollback()
            flash(f'Произошла ошибка при обновлении маршрута: {e}', 'error')
    
    # Заполняем поле с этапами текущими данными для отображения в форме
    form.stages.data = [stage.stage_id for stage in sorted(template.stages, key=lambda s: s.order)]
    return render_template('route_form.html', form=form, title=f'Редактировать: {template.name}')


@management_bp.route('/routes/delete/<int:route_id>', methods=['POST'])
@permission_required(Permission.MANAGE_ROUTES)
def delete_route(route_id):
    """Обрабатывает удаление маршрута."""
    template = db.get_or_404(RouteTemplate, route_id)
    # Проверяем, не назначен ли маршрут каким-либо деталям
    if Part.query.filter_by(route_template_id=route_id).first():
        flash('Нельзя удалить маршрут, так как он присвоен одной или нескольким деталям.', 'error')
    else:
        template_name = template.name
        db.session.delete(template)
        log_entry = AuditLog(user_id=current_user.id, action="Управление маршрутами", details=f"Удален маршрут '{template_name}'.", category='management')
        db.session.add(log_entry)
        db.session.commit()
        flash(f'Маршрут "{template_name}" успешно удален.', 'success')
    return redirect(url_for('admin.management.list_routes'))