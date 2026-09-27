"""
Regras de negócio do sistema de turismo.

Cada função handle_* recebe o payload (dicionário vindo do RabbitMQ) e a
conexão com o banco, valida os dados e chama as funções de db_methods.
Em caso de dado inválido, lança ValueError com uma mensagem clara; o
callback do RabbitMQ devolve essa mensagem ao cliente como erro.
"""

import db_methods


# ---------------------------------------------------------------------------
# Funções auxiliares de validação
# ---------------------------------------------------------------------------

def _require_text(payload, field, max_len):
    """Garante que o campo é um texto não vazio com até max_len caracteres."""
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"O campo '{field}' é obrigatório.")
    value = value.strip()
    if len(value) > max_len:
        raise ValueError(f"O campo '{field}' deve ter no máximo {max_len} caracteres.")
    return value


def _require_int(payload, field):
    """Garante que o campo é um número inteiro positivo (um ID)."""
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"O campo '{field}' deve ser um ID válido.")
    return value


def _require_coordinate(payload, field, limit):
    """Garante que o campo é um número entre -limit e +limit."""
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"O campo '{field}' deve ser um número.")
    if not -limit <= value <= limit:
        raise ValueError(f"O campo '{field}' deve estar entre -{limit} e {limit}.")
    return float(value)


# ---------------------------------------------------------------------------
# História 1: cadastrar ponto de interesse
# ---------------------------------------------------------------------------

def handle_add_point(payload, connection_sql):
    data = {
        'name': _require_text(payload, 'name', 150),
        'description': (payload.get('description') or '').strip(),
        'latitude': _require_coordinate(payload, 'latitude', 90),
        'longitude': _require_coordinate(payload, 'longitude', 180),
    }
    point_id = db_methods.add_point(data, connection_sql)
    return {'status': 'success', 'id': point_id}


# ---------------------------------------------------------------------------
# História 2: criar tour a partir de uma lista de PDIs
# ---------------------------------------------------------------------------

def handle_add_tour(payload, connection_sql):
    name = _require_text(payload, 'name', 150)
    point_ids = payload.get('pontos_ids')
    if not isinstance(point_ids, list) or not point_ids:
        raise ValueError("O tour deve ter pelo menos um PDI em 'pontos_ids'.")
    if any(isinstance(p, bool) or not isinstance(p, int) for p in point_ids):
        raise ValueError("'pontos_ids' deve conter apenas IDs numéricos.")
    if len(set(point_ids)) != len(point_ids):
        raise ValueError("'pontos_ids' contém PDIs repetidos.")

    missing = set(point_ids) - db_methods.get_existing_point_ids(point_ids, connection_sql)
    if missing:
        raise ValueError(f"PDIs inexistentes: {sorted(missing)}")

    data = {
        'name': name,
        'description': (payload.get('description') or '').strip(),
        'pontos_ids': point_ids,
    }
    tour_id = db_methods.add_tour(data, connection_sql)
    return {'status': 'success', 'id': tour_id}


def handle_add_point_to_tour(payload, connection_sql):
    tour_id = _require_int(payload, 'tour_id')
    point_id = _require_int(payload, 'point_id')
    if not db_methods.tour_exists(tour_id, connection_sql):
        raise ValueError(f"Tour {tour_id} não existe.")
    if not db_methods.get_existing_point_ids([point_id], connection_sql):
        raise ValueError(f"PDI {point_id} não existe.")
    if db_methods.is_point_in_tour(tour_id, point_id, connection_sql):
        raise ValueError(f"PDI {point_id} já faz parte do tour {tour_id}.")
    db_methods.add_point_to_tour({'tour_id': tour_id, 'point_id': point_id}, connection_sql)
    return {'status': 'success'}


# ---------------------------------------------------------------------------
# Tabela de despacho: tipo de mensagem -> função que trata
# (usada pelo callback em rabbitmq_methods.py)
# ---------------------------------------------------------------------------

HANDLERS = {
    'add_point': handle_add_point,
    'add_tour': handle_add_tour,
    'add_point_to_tour': handle_add_point_to_tour,
}
