"""
Regras de negócio do sistema de turismo.

Cada função handle_* recebe o payload (dicionário vindo do RabbitMQ) e a
conexão com o banco, valida os dados e chama as funções de db_methods.
Em caso de dado inválido, lança ValueError com uma mensagem clara; o
callback do RabbitMQ devolve essa mensagem ao cliente como erro.
"""

import secrets

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
# História 3: turista se cadastra, vê os tours e escolhe um
# ---------------------------------------------------------------------------

def _get_tourist_or_fail(payload, connection_sql):
    tourist_id = _require_int(payload, 'tourist_id')
    tourist = db_methods.get_tourist(tourist_id, connection_sql)
    if tourist is None:
        raise ValueError(f"Turista {tourist_id} não existe.")
    return tourist


def handle_register_tourist(payload, connection_sql):
    name = _require_text(payload, 'name', 100)
    tourist_id = db_methods.add_tourist(name, connection_sql)
    return {'status': 'success', 'id': tourist_id}


def handle_choose_tour(payload, connection_sql):
    tourist = _get_tourist_or_fail(payload, connection_sql)
    tour_id = _require_int(payload, 'tour_id')
    if not db_methods.tour_exists(tour_id, connection_sql):
        raise ValueError(f"Tour {tour_id} não existe.")
    if tourist['group_id'] is not None:
        raise ValueError("Turista está em um grupo e não pode trocar de tour.")
    db_methods.set_tourist_tour(tourist['id'], tour_id, connection_sql)
    return {'status': 'success'}


# ---------------------------------------------------------------------------
# Histórias 4 e 5: ver PDIs do tour (com progresso) e marcar como visitado
# ---------------------------------------------------------------------------

def handle_mark_visited(payload, connection_sql):
    tourist = _get_tourist_or_fail(payload, connection_sql)
    point_id = _require_int(payload, 'point_id')
    if tourist['tour_id'] is None:
        raise ValueError("Turista ainda não escolheu um tour.")
    if not db_methods.is_point_in_tour(tourist['tour_id'], point_id, connection_sql):
        raise ValueError(f"PDI {point_id} não faz parte do tour escolhido.")
    if point_id in db_methods.get_visited_point_ids(tourist['id'], connection_sql):
        raise ValueError(f"PDI {point_id} já foi marcado como visitado.")
    db_methods.add_visit(tourist['id'], point_id, connection_sql)
    return {'status': 'success'}


def handle_get_tourist_progress(payload, connection_sql):
    """Retorna o tour do turista com cada PDI marcado como visitado ou não."""
    tourist = _get_tourist_or_fail(payload, connection_sql)
    if tourist['tour_id'] is None:
        return {**tourist, 'tour': None}
    tour = next(t for t in db_methods.get_tours(connection_sql)
                if t['id'] == tourist['tour_id'])
    visited = set(db_methods.get_visited_point_ids(tourist['id'], connection_sql))
    for point in tour['points']:
        point['visited'] = point['id'] in visited
    return {**tourist, 'tour': tour}


# ---------------------------------------------------------------------------
# Histórias 6 e 7: criar grupo com código único e entrar em grupo
# ---------------------------------------------------------------------------

# Sem 0/O e 1/I/L para o código não ser confundido ao ser digitado
CODE_ALPHABET = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
CODE_LENGTH = 6


def _generate_unique_code(connection_sql):
    while True:
        code = ''.join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        if not db_methods.group_code_exists(code, connection_sql):
            return code


def handle_create_group(payload, connection_sql):
    tourist = _get_tourist_or_fail(payload, connection_sql)
    if tourist['tour_id'] is None:
        raise ValueError("Escolha um tour antes de criar um grupo.")
    if tourist['group_id'] is not None:
        raise ValueError("Turista já está em um grupo.")
    code = _generate_unique_code(connection_sql)
    db_methods.create_group(code, tourist['tour_id'], tourist['id'], connection_sql)
    return {'status': 'success', 'code': code}


def handle_join_group(payload, connection_sql):
    tourist = _get_tourist_or_fail(payload, connection_sql)
    code = _require_text(payload, 'code', CODE_LENGTH).upper()
    group = db_methods.get_group_by_code(code, connection_sql)
    if group is None:
        raise ValueError(f"Nenhum grupo encontrado com o código '{code}'.")
    if tourist['group_id'] is not None:
        raise ValueError("Turista já está em um grupo.")
    db_methods.join_group(tourist['id'], group['id'], group['tour_id'], connection_sql)
    return {'status': 'success', 'tour_id': group['tour_id']}


# ---------------------------------------------------------------------------
# Tabela de despacho: tipo de mensagem -> função que trata
# (usada pelo callback em rabbitmq_methods.py)
# ---------------------------------------------------------------------------

HANDLERS = {
    'add_point': handle_add_point,
    'add_tour': handle_add_tour,
    'add_point_to_tour': handle_add_point_to_tour,
    'register_tourist': handle_register_tourist,
    'choose_tour': handle_choose_tour,
    'mark_visited': handle_mark_visited,
    'get_tourist_progress': handle_get_tourist_progress,
    'create_group': handle_create_group,
    'join_group': handle_join_group,
}
