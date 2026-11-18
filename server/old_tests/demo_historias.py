"""
Demonstra as histórias de usuário 3 a 8 enviando mensagens pelo RabbitMQ.
Pré-requisito: servidor rodando e banco populado com populate_db.py.
Uso: python server/tests/demo_historias.py
"""

import os
import json

from read_db import RabbitMQClientRPC

QUEUE_NAME = 'my_queue'


def main():
    client = RabbitMQClientRPC(host=os.getenv('RABBITMQ_HOST', 'localhost'))

    def send(title, payload):
        response = client.send_request(QUEUE_NAME, payload)
        print(f"\n=== {title}\n{json.dumps(response, indent=2, ensure_ascii=False)}")
        return response

    try:
        # História 3: turistas se cadastram, veem os tours e escolhem um
        ana = send("Cadastrar turista Ana", {'type': 'register_tourist', 'name': 'Ana'})['id']
        bruno = send("Cadastrar turista Bruno", {'type': 'register_tourist', 'name': 'Bruno'})['id']
        tours = client.send_request(QUEUE_NAME, {'type': 'get_tours'})
        print("\n=== Tours disponíveis:", [t['name'] for t in tours])
        send("Ana escolhe o tour 1", {'type': 'choose_tour', 'tourist_id': ana, 'tour_id': 1})

        # História 5: marcar PDIs como visitados
        send("Ana visita o PDI 1", {'type': 'mark_visited', 'tourist_id': ana, 'point_id': 1})
        send("Ana visita o PDI 2", {'type': 'mark_visited', 'tourist_id': ana, 'point_id': 2})
        send("ERRO esperado: PDI fora do tour", {'type': 'mark_visited', 'tourist_id': ana, 'point_id': 5})
        send("ERRO esperado: visita repetida", {'type': 'mark_visited', 'tourist_id': ana, 'point_id': 1})

        # História 4: PDIs do tour com o progresso (para o mapa)
        send("Progresso da Ana", {'type': 'get_tourist_progress', 'tourist_id': ana})

        # Histórias 6 e 7: criar grupo e entrar com o código
        code = send("Ana cria um grupo", {'type': 'create_group', 'tourist_id': ana})['code']
        send("ERRO esperado: código inválido", {'type': 'join_group', 'tourist_id': bruno, 'code': 'XXXXXX'})
        send("Bruno entra no grupo", {'type': 'join_group', 'tourist_id': bruno, 'code': code})
        send("Bruno visita o PDI 3", {'type': 'mark_visited', 'tourist_id': bruno, 'point_id': 3})

        # História 8: progresso do grupo
        send("Progresso do grupo", {'type': 'get_group_progress', 'code': code})
    finally:
        client.close()


if __name__ == '__main__':
    main()
