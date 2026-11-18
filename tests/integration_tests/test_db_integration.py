import sys
import os
import unittest
import psycopg2

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../server"))
)
import db_methods

class TestDatabaseIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Conecta ao banco real do PostgreSQL definido no docker-compose."""
        cls.db_host = os.getenv("DB_HOST", "localhost")
        cls.db_user = os.getenv("DB_USER", "admin")
        cls.db_password = os.getenv("DB_PASSWORD", "admin")
        cls.db_name = os.getenv("DB_NAME", "mydb")
        cls.db_port = os.getenv("DB_PORT", "5432")

        try:
            cls.connection = psycopg2.connect(
                host=cls.db_host,
                user=cls.db_user,
                password=cls.db_password,
                dbname=cls.db_name,
                port=cls.db_port,
            )
            # Cria/Garante as tabelas no banco de dados real
            db_methods.create_db_tables(cls.connection)
        except Exception as e:
            raise RuntimeError(
                f"Não foi possível conectar ao banco de dados: {e}. "
                "Certifique-se de que o docker-compose está rodando (docker compose -f server/docker-compose.yml up -d)."
            )

    @classmethod
    def tearDownClass(cls):
        """Fecha a conexão com o banco após todos os testes."""
        if hasattr(cls, "connection") and cls.connection:
            cls.connection.close()

    def test_01_points_lifecycle(self):
        """ Testa: add_point, get_points, point_exists, get_existing_point_ids """
        point_data = {
            "name": "Praça da Liberdade",
            "description": "Cartão postal",
            "latitude": -19.932000,
            "longitude": -43.938000,
        }
        point_id = db_methods.add_point(point_data, self.connection)
        self.assertIsNotNone(point_id)

        # Testa point_exists
        self.assertTrue(db_methods.point_exists(point_id, self.connection))

        # Testa get_existing_point_ids
        existing = db_methods.get_existing_point_ids([point_id, 99999], self.connection)
        self.assertIn(point_id, existing)
        self.assertNotIn(99999, existing)

        # Testa get_points
        points = db_methods.get_points(self.connection)
        self.assertTrue(any(p["id"] == point_id for p in points))
        
        # Guarda para uso nos próximos testes
        self.__class__.sample_point_id = point_id

    def test_02_tours_lifecycle(self):
        """ Testa: add_tour, tour_exists, get_tour_point_ids, is_point_in_tour, add_point_to_tour, get_tours """
        point_id = self.__class__.sample_point_id

        tour_data = {
            "name": "Tour Cultural BH",
            "description": "Passeio pelos museus e praças",
            "pontos_ids": [point_id]
        }
        tour_id = db_methods.add_tour(tour_data, self.connection)
        self.assertIsNotNone(tour_id)

        # Testa tour_exists
        self.assertTrue(db_methods.tour_exists(tour_id, self.connection))

        # Testa get_tour_point_ids e is_point_in_tour
        point_ids = db_methods.get_tour_point_ids(tour_id, self.connection)
        self.assertIn(point_id, point_ids)
        self.assertTrue(db_methods.is_point_in_tour(tour_id, point_id, self.connection))

        # Testa add_point_to_tour (adicionando um segundo ponto avulso)
        point_data_2 = {
            "name": "Mercado Central",
            "description": "Comércio tradicional",
            "latitude": -19.922000,
            "longitude": -43.945000,
        }
        point_id_2 = db_methods.add_point(point_data_2, self.connection)
        db_methods.add_point_to_tour({"tour_id": tour_id, "point_id": point_id_2}, self.connection)
        
        self.assertTrue(db_methods.is_point_in_tour(tour_id, point_id_2, self.connection))

        # Testa get_tours
        tours = db_methods.get_tours(self.connection)
        inserted_tour = next((t for t in tours if t["id"] == tour_id), None)
        self.assertIsNotNone(inserted_tour)
        self.assertEqual(len(inserted_tour["points"]), 2)

        self.__class__.sample_tour_id = tour_id
        self.__class__.sample_point_id_2 = point_id_2

    def test_03_tourists_and_visits(self):
        """ Testa: add_tourist, get_tourist, set_tourist_tour, add_visit, get_visited_point_ids """
        tourist_id = db_methods.add_tourist("Felipe Turista", self.connection)
        self.assertIsNotNone(tourist_id)

        tourist = db_methods.get_tourist(tourist_id, self.connection)
        self.assertEqual(tourist["name"], "Felipe Turista")

        tour_id = self.__class__.sample_tour_id
        point_id = self.__class__.sample_point_id

        # Define o tour para o turista
        db_methods.set_tourist_tour(tourist_id, tour_id, self.connection)
        tourist_updated = db_methods.get_tourist(tourist_id, self.connection)
        self.assertEqual(tourist_updated["tour_id"], tour_id)

        # Registra visitas
        db_methods.add_visit(tourist_id, point_id, self.connection)
        visited = db_methods.get_visited_point_ids(tourist_id, self.connection)
        self.assertEqual(visited, [point_id])

        self.__class__.sample_tourist_id = tourist_id

    def test_04_groups(self):
        """ Testa: group_code_exists, create_group, get_group_by_code, join_group, get_group_members """
        code = "BH2026"
        tour_id = self.__class__.sample_tour_id
        tourist_id = self.__class__.sample_tourist_id

        self.assertFalse(db_methods.group_code_exists(code, self.connection))

        # Cria grupo com o turista criador
        group_id = db_methods.create_group(code, tour_id, tourist_id, self.connection)
        self.assertIsNotNone(group_id)
        self.assertTrue(db_methods.group_code_exists(code, self.connection))

        # Busca grupo por código
        group = db_methods.get_group_by_code(code, self.connection)
        self.assertEqual(group["id"], group_id)
        self.assertEqual(group["code"], code)

        # Adiciona outro turista e coloca no grupo
        tourist_id_2 = db_methods.add_tourist("Maria Turista", self.connection)
        db_methods.join_group(tourist_id_2, group_id, tour_id, self.connection)

        # Verifica membros do grupo
        members = db_methods.get_group_members(group_id, self.connection)
        self.assertEqual(len(members), 2)

    def test_05_users_authentication(self):
        """ Testa: username_exists, register_user, login_user """
        username = "admin_test"
        self.assertFalse(db_methods.username_exists(username, self.connection))

        user_data = {
            "username": username,
            "password": "securepassword123",
            "role": "admin"
        }
        user_id = db_methods.register_user(user_data, self.connection)
        self.assertIsNotNone(user_id)
        self.assertTrue(db_methods.username_exists(username, self.connection))

        # Testa Login correto
        login_result = db_methods.login_user({"username": username, "password": "securepassword123"}, self.connection)
        self.assertIsNotNone(login_result)
        self.assertEqual(login_result[1], "admin")

        # Testa Login incorreto
        wrong_login = db_methods.login_user({"username": username, "password": "wrongpassword"}, self.connection)
        self.assertIsNone(wrong_login)

    def test_06_deletions(self):
        """ Testa: delete_point e delete_tour (com cascade) """
        tour_id = self.__class__.sample_tour_id
        point_id_2 = self.__class__.sample_point_id_2

        # Deleta um ponto avulso
        db_methods.delete_point(point_id_2, self.connection)
        self.assertFalse(db_methods.point_exists(point_id_2, self.connection))

        # Deleta o tour
        db_methods.delete_tour(tour_id, self.connection)
        self.assertFalse(db_methods.tour_exists(tour_id, self.connection))


if __name__ == "__main__":
    unittest.main()