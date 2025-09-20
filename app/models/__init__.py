# app/models/__init__.py

# Этот файл собирает все модели из отдельных файлов в одно пространство имен,
# чтобы их можно было удобно импортировать в других частях приложения.
# Например: from app.models import User, Part

from .user_models import User, Role, Permission, AnonymousUser
from .route_models import Stage, RouteTemplate, RouteStage
from .part_models import Part, AssemblyComponent
from .history_models import StatusHistory, AuditLog, PartNote, ResponsibleHistory, StatusType