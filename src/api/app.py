"""FastAPI 应用入口。"""

from src.api.registrar import register_app

app = register_app()
