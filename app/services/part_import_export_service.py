# app/services/part_import_export_service.py

import io
import pandas as pd
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

# --- ИЗМЕНЕНИЕ: Исправляем пути импорта ---
from app import db
from app.models import Part, RouteTemplate, Stage, RouteStage, AssemblyComponent


def _get_or_create_route_from_operations(operations_str: str) -> RouteTemplate:
    """
    Находит существующий маршрут по набору операций или создает новый.
    :param operations_str: Строка с операциями, разделенными ';' или ','.
    :return: Экземпляр RouteTemplate или None.
    """
    operations = [op.strip() for op in operations_str.replace(',', ';').split(';') if op.strip()]
    if not operations:
        return None

    # Ищем существующий маршрут с таким же именем
    route_name = " -> ".join(operations)
    route = RouteTemplate.query.filter_by(name=route_name).first()

    if route:
        return route

    # Если не нашли, создаем новый
    new_route = RouteTemplate(name=route_name, is_default=False)
    db.session.add(new_route)
    db.session.flush() # Получаем ID для new_route

    # Находим или создаем этапы и привязываем их к маршруту
    for i, op_name in enumerate(operations):
        # Ищем этап без учета регистра
        stage = Stage.query.filter(func.lower(Stage.name) == func.lower(op_name)).first()
        if not stage:
            stage = Stage(name=op_name)
            db.session.add(stage)
            db.session.flush() # Получаем ID для stage
        
        route_stage = RouteStage(template_id=new_route.id, stage_id=stage.id, order=i)
        db.session.add(route_stage)

    return new_route


def import_parts_from_excel(file_storage, user):
    """
    Обрабатывает Excel/CSV файл для массового импорта деталей и их иерархии.
    :param file_storage: Объект FileStorage из Flask.
    :param user: Текущий пользователь.
    :return: Кортеж (количество добавленных, количество пропущенных).
    """
    try:
        # Пытаемся прочитать файл, определяя формат по расширению
        if file_storage.filename.endswith('.csv'):
            df = pd.read_csv(file_storage, sep=None, engine='python', header=None, dtype=str)
        else:
            df = pd.read_excel(file_storage, header=None, dtype=str)
    except Exception as e:
        raise ValueError(f"Не удалось прочитать файл. Убедитесь, что он не поврежден. Ошибка: {e}")

    if df.empty:
        return 0, 0

    # Карта возможных названий колонок
    header_map = {
        'Обозначение': ['Обозначение', 'Артикул', 'part_id'],
        'Наименование': ['Наименование', 'name'],
        'Кол-во': ['Кол-во', 'Количество', 'quantity'],
        'Размер': ['Размер', 'size'],
        'Операции': ['Операции', 'Маршрут', 'route'],
        'Прим.': ['Прим.', 'Примечание', 'Материал', 'material']
    }

    # Поиск строки с заголовками
    header_row_index = -1
    for i, row in df.iterrows():
        # Преобразуем всю строку в одну строку в нижнем регистре для поиска
        row_str = ' '.join(str(s).lower() for s in row.values)
        if 'обозначение' in row_str and 'наименование' in row_str:
            header_row_index = i
            break
    
    if header_row_index == -1:
        raise ValueError("В файле не найдена строка с заголовками (должна содержать 'Обозначение' и 'Наименование').")

    headers = [str(h).strip() for h in df.iloc[header_row_index]]
    df = df.iloc[header_row_index + 1:]
    df.columns = headers
    df = df.fillna('') # Заменяем NaN на пустые строки для удобства

    # Определение имен колонок по синонимам
    def find_col(name):
        for alias in header_map[name]:
            if alias in df.columns:
                return alias
        return None

    col_id = find_col('Обозначение')
    col_name = find_col('Наименование')
    col_qty = find_col('Кол-во')
    col_material = find_col('Прим.')
    col_size = find_col('Размер')
    col_ops = find_col('Операции')
    
    if not all([col_id, col_name, col_qty, col_material]):
        raise ValueError("Не найдены обязательные колонки: 'Обозначение', 'Наименование', 'Кол-во', 'Прим.'")

    added_count = 0
    skipped_count = 0
    current_product_id = None
    current_product_designation = "Не определено"

    default_route = RouteTemplate.query.filter_by(is_default=True).first()
    if not default_route and col_ops is None:
        raise ValueError("В файле не указаны операции и не найден маршрут по умолчанию в системе. Импорт невозможен.")

    existing_parts_ids = {p.part_id for p in Part.query.with_entities(Part.part_id).all()}

    for _, row in df.iterrows():
        part_id = str(row.get(col_id, '')).strip()
        name = str(row.get(col_name, '')).strip()
        
        # Ищем строку, которая определяет название всего изделия
        if not part_id and len(row.iloc) > 1 and str(row.iloc[1]).strip():
             current_product_designation = str(row.iloc[1]).strip()
             current_product_id = None # Сбрасываем родителя при смене изделия
             continue

        if not part_id or not name:
            continue
        
        # Определяем, является ли строка родительской (сборкой)
        is_parent = 'СБ' in part_id.upper() or not str(row.get(col_qty, '')).strip()
        
        if is_parent:
            current_product_id = part_id
        
        if part_id in existing_parts_ids:
            skipped_count += 1
            continue
        
        # Обработка количества
        try:
            quantity = int(float(str(row.get(col_qty, '1')).replace(',', '.')))
        except (ValueError, TypeError):
            quantity = 1

        # Определение маршрута
        route = None
        if col_ops and str(row.get(col_ops, '')).strip():
            route = _get_or_create_route_from_operations(str(row[col_ops]))
        else:
            route = default_route

        new_part = Part(
            part_id=part_id,
            product_designation=current_product_designation,
            name=name,
            quantity_total=quantity if is_parent else 1,
            material=str(row.get(col_material, '')),
            size=str(row.get(col_size, '')) if col_size else '',
            route_template_id=route.id if route else None
        )
        db.session.add(new_part)
        
        if not is_parent and current_product_id:
            link = AssemblyComponent(parent_id=current_product_id, child_id=part_id, quantity=quantity)
            db.session.add(link)

        existing_parts_ids.add(part_id)
        added_count += 1
        
    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        raise ValueError(f"Ошибка целостности данных при импорте. Возможно, дубликат ID. Ошибка: {e}")
    
    return added_count, skipped_count


def export_all_parts_to_csv():
    """
    Выгружает все детали из базы данных в CSV-файл.
    :return: Потоковый объект io.StringIO с данными CSV.
    """
    parts = Part.query.options(
        joinedload(Part.route_template).subqueryload(RouteTemplate.stages).joinedload(RouteStage.stage),
        joinedload(Part.responsible)
    ).order_by(Part.product_designation, Part.part_id).all()

    if not parts:
        return None

    data_for_export = []
    for part in parts:
        route_str = ""
        if part.route_template and part.route_template.stages:
            sorted_stages = sorted(part.route_template.stages, key=lambda s: s.order)
            route_str = " -> ".join([rs.stage.name for rs in sorted_stages])
        
        data_for_export.append({
            'Изделие': part.product_designation,
            'Обозначение': part.part_id,
            'Наименование': part.name,
            'Материал': part.material,
            'Размер': part.size,
            'Кол-во в партии': part.quantity_total,
            'Кол-во выполнено': part.quantity_completed,
            'Кол-во в браке': part.quantity_scrapped,
            'Текущий этап': part.current_status,
            'Ответственный': part.responsible.username if part.responsible else '',
            'Маршрут': route_str,
            'Дата создания': part.date_added.strftime('%Y-%m-%d %H:%M:%S'),
        })

    df = pd.DataFrame(data_for_export)
    
    output = io.StringIO()
    # Используем точку с запятой как разделитель для лучшей совместимости с Excel
    df.to_csv(output, index=False, sep=';', encoding='utf-8-sig')
    
    return output