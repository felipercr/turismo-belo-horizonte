import psycopg2

def connect_to_db(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME):
    try:
        connection_sql = psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, dbname=DB_NAME)
        print(" Connected successfully to PostgreSQL!")
        return connection_sql
    except Exception as e:
        raise RuntimeError(f" Database connection failed: {e}")


def create_db_tables(connection_sql):
    with connection_sql.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS points_of_interest (
                id SERIAL PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                description TEXT,
                latitude DECIMAL(9, 6) NOT NULL,
                longitude DECIMAL(9, 6) NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tours (
                id SERIAL PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                description TEXT
            );

            CREATE TABLE IF NOT EXISTS tour_points (
                tour_id INT NOT NULL REFERENCES tours(id) ON DELETE CASCADE,
                point_of_interest_id INT NOT NULL REFERENCES points_of_interest(id) ON DELETE CASCADE,
                PRIMARY KEY (tour_id, point_of_interest_id)
            );
        """)
        connection_sql.commit()


def add_point(data, connection_sql):
    """Insere um novo ponto de interesse recebido do RabbitMQ."""
    query = """
        INSERT INTO points_of_interest (name, description, latitude, longitude)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
    """
    with connection_sql.cursor() as cur:
        cur.execute(query, (
            data['name'],
            data.get('description', ''),
            data['latitude'],
            data['longitude']
        ))
        point_id = cur.fetchone()[0]
        connection_sql.commit()
        print(f" [✓] Ponto '{data['name']}' inserido com ID {point_id}")
        return point_id


def add_tour(data, connection_sql):
    """Insere um tour e vincula a lista de IDs de pontos existente."""
    query_tour = "INSERT INTO tours (name, description) VALUES (%s, %s) RETURNING id;"
    query_vinculo = "INSERT INTO tour_points (tour_id, point_of_interest_id) VALUES (%s, %s);"

    with connection_sql.cursor() as cur:
        cur.execute(query_tour, (data['name'], data.get('description', '')))
        tour_id = cur.fetchone()[0]

        for point_id in data.get('pontos_ids', []):
            cur.execute(query_vinculo, (tour_id, point_id))

        connection_sql.commit()
        print(f" [✓] Tour '{data['name']}' inserido com ID {tour_id}")
        return tour_id


def add_point_to_tour(data, connection_sql):
    """Associa um ponto de interesse existente a um tour existente."""
    query = """
        INSERT INTO tour_points (tour_id, point_of_interest_id)
        VALUES (%s, %s);
    """
    with connection_sql.cursor() as cur:
        cur.execute(query, (data['tour_id'], data['point_id']))
        connection_sql.commit()
        print(f" [✓] Ponto {data['point_id']} associado ao Tour {data['tour_id']}")


def get_points(connection_sql):
    """Retorna todos os pontos de interesse do banco de dados."""
    query = """
        SELECT id, name, description, latitude, longitude
        FROM points_of_interest
        ORDER BY id;
    """
    with connection_sql.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

        points = []
        for row in rows:
            points.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'latitude': float(row[3]),
                'longitude': float(row[4])
            })
        return points


def get_tours(connection_sql):
    """Retorna todos os tours cadastrados e a lista de seus respectivos pontos."""
    query = """
        SELECT 
            t.id AS tour_id,
            t.name AS tour_name,
            t.description AS tour_description,
            p.id AS point_id,
            p.name AS point_name,
            p.description AS point_description,
            p.latitude,
            p.longitude
        FROM tours t
        LEFT JOIN tour_points tp ON t.id = tp.tour_id
        LEFT JOIN points_of_interest p ON tp.point_of_interest_id = p.id
        ORDER BY t.id, p.id;
    """
    with connection_sql.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

        tours_map = {}
        for row in rows:
            tour_id = row[0]
            
            # Inicializa a estrutura do tour se ainda não existir
            if tour_id not in tours_map:
                tours_map[tour_id] = {
                    'id': tour_id,
                    'name': row[1],
                    'description': row[2],
                    'points': []
                }
            
            # Adiciona o ponto apenas se houver vinculo (evita None em tours sem pontos)
            if row[3] is not None:
                tours_map[tour_id]['points'].append({
                    'id': row[3],
                    'name': row[4],
                    'description': row[5],
                    'latitude': float(row[6]),
                    'longitude': float(row[7])
                })

        return list(tours_map.values())