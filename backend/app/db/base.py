# Importa la Base y todos los modelos para que Alembic los inspeccione
from app.core.database import Base
from app.models.user import User
from app.models.project import Project, ProjectCollaborator
from app.models.canvas import CanvasSnapshot