import time
import pika
import json
from functools import partial

import db_methods

def connect_to_rabbitmq(host, max_retries=5, delay=10):
    credentials = pika.PlainCredentials('guest', 'guest')
    parameters = pika.ConnectionParameters(host=host, credentials=credentials)

    for attempt in range(max_retries):
        try:
            print(f"Tentando conectar ao RabbitMQ em {host} (Tentativa {attempt+1}/{max_retries})...")
            connection = pika.BlockingConnection(parameters)
            print("Conectado com sucesso ao RabbitMQ!")
            return connection
        except pika.exceptions.AMQPConnectionError:
            print(f"Falha ao conectar no RabbitMQ. Tentando novamente em {delay} segundos...")
            time.sleep(delay)

    raise RuntimeError("Falha de conexão com o RabbitMQ após limite de tentativas.")


def callback(ch, method, properties, body, connection_sql):
    """Executado quando uma mensagem chega na fila."""
    try:
        payload = json.loads(body.decode('utf-8'))
        msg_type = payload.get('type')
        response_data = None

        # --- Ações de Escrita (retornam confirmação/ID para o cliente) ---
        if msg_type == 'add_point':
            point_id = db_methods.add_point(payload, connection_sql)
            response_data = {'status': 'success', 'id': point_id}

        elif msg_type == 'add_tour':
            tour_id = db_methods.add_tour(payload, connection_sql)
            response_data = {'status': 'success', 'id': tour_id}

        elif msg_type == 'add_point_to_tour':
            db_methods.add_point_to_tour(payload, connection_sql)
            response_data = {'status': 'success'}

        # --- Ações de Leitura ---
        elif msg_type == 'get_points':
            response_data = db_methods.get_points(connection_sql)

        elif msg_type == 'get_tours':
            response_data = db_methods.get_tours(connection_sql)

        else:
            response_data = {'error': f"Tipo de mensagem desconhecido: '{msg_type}'"}

        # Se o cliente solicitou resposta (RPC), envia o resultado de volta
        if properties.reply_to:
            ch.basic_publish(
                exchange='',
                routing_key=properties.reply_to,
                properties=pika.BasicProperties(
                    correlation_id=properties.correlation_id
                ),
                body=json.dumps(response_data, ensure_ascii=False)
            )
            print(f" [->] Resposta enviada para '{properties.reply_to}' (ID: {properties.correlation_id})")

        # Confirma o recebimento da mensagem original
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f" [!] Erro no callback: {e}")
        connection_sql.rollback()

        # Se ocorreu erro mas o cliente estava esperando resposta via RPC, notifica o cliente
        if properties.reply_to:
            ch.basic_publish(
                exchange='',
                routing_key=properties.reply_to,
                properties=pika.BasicProperties(
                    correlation_id=properties.correlation_id
                ),
                body=json.dumps({'status': 'error', 'message': str(e)}, ensure_ascii=False)
            )
            # Confirma a mensagem para removê-la da fila, pois o erro já foi notificado
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            # Se não era RPC, rejeita a mensagem sem colocar de volta na fila (evita loop infinito)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def start_consuming(connection_rabbitmq, connection_sql):
    channel = connection_rabbitmq.channel()
    channel.queue_declare(queue='my_queue')

    # Encapsula o callback repassando connection_sql
    on_message_callback = partial(callback, connection_sql=connection_sql)

    channel.basic_consume(
        queue='my_queue',
        on_message_callback=on_message_callback,
        auto_ack=False
    )
    print(' [*] Aguardando mensagens da fila "my_queue". Pressione CTRL+C para sair.')
    channel.start_consuming()