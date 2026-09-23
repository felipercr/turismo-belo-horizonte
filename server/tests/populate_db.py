
import os
import json
import time
import pika

def send_message(channel, queue_name, payload):
    """Converte o payload em JSON e envia para a fila do RabbitMQ."""
    message = json.dumps(payload)
    channel.basic_publish(
        exchange='',
        routing_key=queue_name,
        body=message,
        properties=pika.BasicProperties(
            delivery_mode=2  # Torna a mensagem persistente
        )
    )
    print(f" [>] Enviado ({payload.get('type')}): {payload.get('name') or payload}")


def main():
    RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
    QUEUE_NAME = 'my_queue'

    # Conexão com o RabbitMQ
    credentials = pika.PlainCredentials('guest', 'guest')
    parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
    
    try:
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME)
        print(f"Conectado ao RabbitMQ em '{RABBITMQ_HOST}'. Enviando mensagens...\n")
    except Exception as e:
        print(f"Erro ao conectar ao RabbitMQ: {e}")
        return

    # 1. Enviar Pontos de Interesse (Gerarão IDs 1, 2, 3, 4 no Postgres)
    points = [
        {
            'type': 'add_point',
            'name': 'Cristo Redentor',
            'description': 'Estátua do Cristo no topo do Corcovado.',
            'latitude': -22.951916,
            'longitude': -43.210487
        },
        {
            'type': 'add_point',
            'name': 'Pão de Açúcar',
            'description': 'Teleférico com vista panorâmica.',
            'latitude': -22.949221,
            'longitude': -43.154516
        },
        {
            'type': 'add_point',
            'name': 'Jardim Botânico',
            'description': 'Parque com flora tropical.',
            'latitude': -22.966888,
            'longitude': -43.226722
        },
        {
            'type': 'add_point',
            'name': 'Maracanã',
            'description': 'Estádio de futebol.',
            'latitude': -22.912167,
            'longitude': -43.230164
        }
    ]

    for point in points:
        send_message(channel, QUEUE_NAME, point)
        time.sleep(0.1)  # Pequeno delay para garantir ordem de processamento

    print("\n--- Enviando Tours ---")

    # 2. Enviar Tours (Assumindo que os pontos 1 e 2 já foram criados)
    tours = [
        {
            'type': 'add_tour',
            'name': 'Tour Cartões Postais',
            'description': 'Pontos mais famosos do Rio.',
            'pontos_ids': [1, 2]  # Vincula Cristo (ID 1) e Pão de Açúcar (ID 2)
        },
        {
            'type': 'add_tour',
            'name': 'Tour Verde & Esporte',
            'description': 'Natureza e futebol.',
            'pontos_ids': []  # Inicia sem pontos
        }
    ]

    for tour in tours:
        send_message(channel, QUEUE_NAME, tour)
        time.sleep(0.1)

    print("\n--- Associando Pontos Existentes a Tours ---")

    # 3. Vincular pontos individuais a tours existentes (Tour ID 2 e Tour ID 1)
    links = [
        {'type': 'add_point_to_tour', 'tour_id': 2, 'point_id': 3},  # Jardim Botânico no Tour 2
        {'type': 'add_point_to_tour', 'tour_id': 2, 'point_id': 4},  # Maracanã no Tour 2
        {'type': 'add_point_to_tour', 'tour_id': 1, 'point_id': 3}   # Jardim Botânico no Tour 1
    ]

    for link in links:
        send_message(channel, QUEUE_NAME, link)
        time.sleep(0.1)

    connection.close()
    print("\n [✓] Todas as mensagens foram enviadas para o RabbitMQ com sucesso!")

if __name__ == '__main__':
    main()