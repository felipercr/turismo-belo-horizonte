# Mensagens da API (fila `my_queue` no RabbitMQ)

Toda requisição é um JSON com o campo `type`. A resposta volta na fila
indicada em `reply_to` (padrão RPC; ver `server/tests/read_db.py`).
Em caso de erro, a resposta é `{"status": "error", "message": "..."}`.

## Administrador

| `type` | Campos | Resposta |
|---|---|---|
| `add_point` | `name`, `description`?, `latitude`, `longitude` | `{"status": "success", "id": 1}` |
| `add_tour` | `name`, `description`?, `pontos_ids` (lista, mín. 1) | `{"status": "success", "id": 1}` |
| `add_point_to_tour` | `tour_id`, `point_id` | `{"status": "success"}` |
| `delete_point` | `point_id` | `{"status": "success"}` |
| `delete_tour` | `tour_id` | `{"status": "success"}` |

## Login

| `type` | Campos | Resposta |
|---|---|---|
| `register` | `username`, `password`, `role` (`user` ou `admin`) | `{"status": "success", "id": 1, "role": "user"}` |
| `login` | `username`, `password` | `{"status": "success", "id": 1, "role": "admin"}` |

## Consultas

| `type` | Campos | Resposta |
|---|---|---|
| `get_points` | — | lista de PDIs `{id, name, description, latitude, longitude}` |
| `get_tours` | — | lista de tours `{id, name, description, points: [...]}` |

## Turista

| `type` | Campos | Resposta |
|---|---|---|
| `register_tourist` | `name` | `{"status": "success", "id": 1}` |
| `choose_tour` | `tourist_id`, `tour_id` | `{"status": "success"}` |
| `mark_visited` | `tourist_id`, `point_id` | `{"status": "success"}` |
| `get_tourist_progress` | `tourist_id` | turista + `tour` com cada PDI marcado `visited: true/false` |

## Grupo

| `type` | Campos | Resposta |
|---|---|---|
| `create_group` | `tourist_id` | `{"status": "success", "code": "83STUA"}` |
| `join_group` | `tourist_id`, `code` | `{"status": "success", "tour_id": 1}` |
| `get_group_progress` | `code` | `{code, tour, members: [{id, name, visited_points, visited_count, total_points}]}` |

## Regras principais

- Turista precisa escolher um tour antes de marcar visitas ou criar grupo.
- Só é possível marcar como visitado um PDI do tour escolhido, e uma única vez.
- Quem entra em um grupo passa a fazer o tour do grupo (visitas anteriores são zeradas).
- Turista em grupo não pode trocar de tour nem entrar em outro grupo.
- Códigos de grupo têm 6 caracteres, sem letras/números ambíguos (0, O, 1, I, L).

## Frontend

O navegador não fala AMQP, então o frontend conversa com o **API gateway**
(`server/api-gateway`, Node.js), que expõe rotas REST (`/api/points`,
`/api/tours`, `/api/login`...) e repassa cada pedido para a fila `my_queue`.
O código da interface fica em `frontend/index.html`; o gateway o entrega ao
navegador. Com o `docker compose` rodando, a interface fica em
**http://localhost:3000**.

