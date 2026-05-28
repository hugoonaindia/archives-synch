"""
Tests básicos para la aplicación Flask de equilibria.
"""

import pytest
import sys
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from app import app

@pytest.fixture
def client():
    """Fixture para crear un cliente de test"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_route(client):
    """Test de la ruta principal"""
    response = client.get('/')
    assert response.status_code == 200

def test_dashboard_route(client):
    """Test de la ruta del dashboard"""
    response = client.get('/dashboard')
    assert response.status_code == 200

def test_pacientes_route(client):
    """Test de la ruta de pacientes"""
    response = client.get('/pacientes')
    assert response.status_code == 200

def test_tareas_route(client):
    """Test de la ruta de tareas"""
    response = client.get('/tareas')
    assert response.status_code == 200

def test_api_exportar_json(client):
    """Test de la API de exportación en formato JSON"""
    response = client.get('/api/exportar?formato=json')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/json'

if __name__ == '__main__':
    pytest.main([__file__])