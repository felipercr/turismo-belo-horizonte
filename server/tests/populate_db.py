
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

    # 1. Enviar Pontos de Interesse de BH (coordenadas aproximadas)
    # Gerarão IDs 1 a 8 no Postgres, na ordem abaixo
    def pdi(name, description, lat, lon):
        return {'type': 'add_point', 'name': name, 'description': description,
                'latitude': lat, 'longitude': lon}

    points = [
        pdi('Praça da Liberdade', 'Praça com palácios e museus do Circuito Cultural.', -19.932000, -43.938000),
        pdi('Mercado Central', 'Mercado tradicional com comidas e produtos mineiros.', -19.922500, -43.943200),
        pdi('Praça Sete', 'Marco zero do centro de BH, com o Pirulito.', -19.919100, -43.938600),
        pdi('Parque Municipal', 'Parque Américo Renné Giannetti, no centro.', -19.924500, -43.933600),
        pdi('Igreja São Francisco de Assis', 'Igrejinha da Pampulha, obra de Niemeyer.', -19.858000, -43.978400),
        pdi('Mineirão', 'Estádio Governador Magalhães Pinto.', -19.865900, -43.971100),
        pdi('Museu de Arte da Pampulha', 'Antigo cassino projetado por Niemeyer.', -19.851100, -43.975800),
        pdi('Mirante do Mangabeiras', 'Vista panorâmica da cidade.', -19.953000, -43.918000),
    ]

    for point in points:
        send_message(channel, QUEUE_NAME, point)
        time.sleep(0.1)  # Pequeno delay para garantir ordem de processamento

    print("\n--- Enviando Tours ---")

    # 2. Enviar Tours (IDs 1 e 2)
    tours = [
        {
            'type': 'add_tour',
            'name': 'Centro Histórico',
            'description': 'Os pontos mais tradicionais do centro de BH.',
            'pontos_ids': [1, 2, 3, 4]
        },
        {
            'type': 'add_tour',
            'name': 'Pampulha Modernista',
            'description': 'Conjunto moderno da Pampulha, Patrimônio da Humanidade.',
            'pontos_ids': [5, 6, 7]
        }
    ]

    for tour in tours:
        send_message(channel, QUEUE_NAME, tour)
        time.sleep(0.1)

    print("\n--- Associando Pontos Existentes a Tours ---")

    # 3. Vincular um ponto individual a um tour existente
    links = [
        {'type': 'add_point_to_tour', 'tour_id': 1, 'point_id': 8},  # Mirante no Centro Histórico
    ]

    for link in links:
        send_message(channel, QUEUE_NAME, link)
        time.sleep(0.1)

    connection.close()
    print("\n [✓] Todas as mensagens foram enviadas para o RabbitMQ com sucesso!")

if __name__ == '__main__':
    main()