"""
WSGI entrypoint para Vercel
Exporta a aplicação FastAPI como WSGI para que Vercel possa servir
"""

from api import app

# Fazer app FastAPI compatível com WSGI
wsgi_app = app
