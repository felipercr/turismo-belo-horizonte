import os
import time

import db_methods
import rabbitmq_methods

def main():

    DB_HOST       = os.getenv('DB_HOST', 'postgres')
    DB_USER       = os.getenv('DB_USER', 'admin')
    DB_PASSWORD   = os.getenv('DB_PASSWORD', 'admin')
    DB_NAME       = os.getenv('DB_NAME', 'mydb')
    RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq_server')
    time.sleep(10)

    # Conexão com o BD SQL
    connection_sql = db_methods.connect_to_db(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)
    db_methods.create_db_tables(connection_sql)

    # Conexão com o RabbitMQ
    connection_rabbitmq = rabbitmq_methods.connect_to_rabbitmq(RABBITMQ_HOST)
    rabbitmq_methods.start_consuming(connection_rabbitmq, connection_sql)
    

if __name__ == '__main__':
    main()