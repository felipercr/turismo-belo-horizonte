import os
import json
import uuid
import time
import pika

class RabbitMQClientRPC:
    def __init__(self, host):
        credentials = pika.PlainCredentials('guest', 'guest')
        parameters = pika.ConnectionParameters(host=host, credentials=credentials)
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

        # Fila temporária exclusiva de resposta
        result = self.channel.queue_declare(queue='', exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self._on_response,
            auto_ack=True
        )

        self.response = None
        self.corr_id = None
        self.received = False

    def _on_response(self, ch, method, props, body):
        """Executado quando a resposta chega na fila de callback."""
        raw_body = body.decode('utf-8')
        print(f" [<-] Resposta recebida! Conteúdo: {raw_body}", flush=True)

        if self.corr_id == props.correlation_id:
            try:
                self.response = json.loads(raw_body)
            except Exception as e:
                self.response = {'error': f"JSON inválido: {e}"}
            # Marca como recebido para interromper o loop de espera
            self.received = True
        else:
            print(f" [!] ID divergente. Esperado: {self.corr_id}, Recebido: {props.correlation_id}", flush=True)

    def send_request(self, queue_name, payload, timeout=5):
        """Envia requisição e aguarda utilizando a flag self.received."""
        self.response = None
        self.received = False
        self.corr_id = str(uuid.uuid4())

        self.channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id
            ),
            body=json.dumps(payload)
        )

        start_time = time.time()

        # Aguarda a flag de recebimento ficar True
        while not self.received:
            self.connection.process_data_events(time_limit=1)

            if time.time() - start_time > timeout:
                raise TimeoutError(f"Tempo limite ({timeout}s) excedido para '{payload.get('type')}'")

        return self.response

    def close(self):
        self.connection.close()


def main():
    RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
    QUEUE_NAME = 'my_queue'

    print(f"Conectando ao RabbitMQ em '{RABBITMQ_HOST}'...")
    client = RabbitMQClientRPC(host=RABBITMQ_HOST)

    try:
        # 1. Solicitar pontos
        print("\n[<] Solicitando pontos de interesse via RabbitMQ...")
        points = client.send_request(QUEUE_NAME, {'type': 'get_points'}, timeout=5)
        print("\n=================== PONTOS RECEBIDOS ===================")
        print(json.dumps(points, indent=2, ensure_ascii=False))

        # 2. Solicitar tours
        print("\n[<] Solicitando tours via RabbitMQ...")
        tours = client.send_request(QUEUE_NAME, {'type': 'get_tours'}, timeout=5)
        print("\n==================== TOURS RECEBIDOS ====================")
        print(json.dumps(tours, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"\n [!] Falha na requisição: {e}")
    finally:
        client.close()
        print("\n[✓] Execução finalizada!")


if __name__ == '__main__':
    main()