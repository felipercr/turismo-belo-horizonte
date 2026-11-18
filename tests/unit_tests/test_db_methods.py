import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../server"))
)
import db_methods


class TestDatabaseMethods(unittest.TestCase):

    def setUp(self):
        """Configuração inicial comum para os testes."""
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value.__enter__.return_value = (
            self.mock_cursor
        )

    # ---------------------------------------------------------------------------
    # Testes de Conexão e Tabelas
    # ---------------------------------------------------------------------------

    @patch("psycopg2.connect")
    def test_connect_to_db_success(self, mock_psycopg2_connect):
        mock_conn_instance = MagicMock()
        mock_psycopg2_connect.return_value = mock_conn_instance

        # Chamada da função
        conn = db_methods.connect_to_db("localhost", "user", "pass", "mydb")

        # Verificações
        mock_psycopg2_connect.assert_called_once_with(
            host="localhost", user="user", password="pass", dbname="mydb"
        )
        self.assertEqual(conn, mock_conn_instance)

    @patch("psycopg2.connect")
    def test_connect_to_db_failure(self, mock_psycopg2_connect):
        mock_psycopg2_connect.side_effect = Exception("Connection refused")

        with self.assertRaises(RuntimeError) as context:
            db_methods.connect_to_db("localhost", "user", "pass", "mydb")

        self.assertIn("Database connection failed", str(context.exception))

    def test_create_db_tables(self):
        db_methods.create_db_tables(self.mock_conn)

        self.mock_cursor.execute.assert_called_once()
        self.mock_conn.commit.assert_called_once()

    # ---------------------------------------------------------------------------
    # Testes de Inserção e Gestão de Pontos/Tours
    # ---------------------------------------------------------------------------

    def test_add_point(self):
        self.mock_cursor.fetchone.return_value = [10]  # ID retornado
        data = {
            "name": "Praça da Liberdade",
            "description": "Praça famosa",
            "latitude": -19.932,
            "longitude": -43.938,
        }

        point_id = db_methods.add_point(data, self.mock_conn)

        self.assertEqual(point_id, 10)
        self.mock_cursor.execute.assert_called_once()
        self.mock_conn.commit.assert_called_once()

    def test_add_tour(self):
        self.mock_cursor.fetchone.return_value = [5]  # Tour ID retornado
        data = {
            "name": "Tour Histórico",
            "description": "Passeio pelo centro",
            "pontos_ids": [1, 2, 3],
        }

        tour_id = db_methods.add_tour(data, self.mock_conn)

        self.assertEqual(tour_id, 5)
        # 1 insert do tour + 3 inserts de pontos vinculados = 4 execuções
        self.assertEqual(self.mock_cursor.execute.call_count, 4)
        self.mock_conn.commit.assert_called_once()

    def test_add_point_to_tour(self):
        data = {"tour_id": 2, "point_id": 4}

        db_methods.add_point_to_tour(data, self.mock_conn)

        self.mock_cursor.execute.assert_called_once()
        self.mock_conn.commit.assert_called_once()

    # ---------------------------------------------------------------------------
    # Testes de Consultas (GET)
    # ---------------------------------------------------------------------------

    def test_get_points(self):
        self.mock_cursor.fetchall.return_value = [
            (
                1,
                "Museu",
                "Arte e história",
                -19.9281,
                -43.9401,
            )
        ]

        points = db_methods.get_points(self.mock_conn)

        expected = [
            {
                "id": 1,
                "name": "Museu",
                "description": "Arte e história",
                "latitude": -19.9281,
                "longitude": -43.9401,
            }
        ]
        self.assertEqual(points, expected)
        self.mock_cursor.execute.assert_called_once()

    def test_get_tours(self):
        # Simula linhas vindas do JOIN (tour com 1 PDI e um tour sem PDI)
        self.mock_cursor.fetchall.return_value = [
            (1, "Tour A", "Desc A", 101, "Ponto X", "Desc X", -19.9, -43.9),
            (2, "Tour B", "Desc B", None, None, None, None, None),
        ]

        tours = db_methods.get_tours(self.mock_conn)

        self.assertEqual(len(tours), 2)
        self.assertEqual(tours[0]["id"], 1)
        self.assertEqual(len(tours[0]["points"]), 1)
        self.assertEqual(tours[1]["id"], 2)
        self.assertEqual(tours[1]["points"], [])

    # ---------------------------------------------------------------------------
    # Testes de Auxiliares de Negócio
    # ---------------------------------------------------------------------------

    def test_get_existing_point_ids(self):
        self.mock_cursor.fetchall.return_value = [(1,), (3,)]

        result = db_methods.get_existing_point_ids([1, 2, 3], self.mock_conn)

        self.assertEqual(result, {1, 3})

    def test_get_existing_point_ids_empty(self):
        result = db_methods.get_existing_point_ids([], self.mock_conn)
        self.assertEqual(result, set())
        self.mock_cursor.execute.assert_not_called()

    def test_tour_exists_true(self):
        self.mock_cursor.fetchone.return_value = [1]
        self.assertTrue(db_methods.tour_exists(1, self.mock_conn))

    def test_tour_exists_false(self):
        self.mock_cursor.fetchone.return_value = None
        self.assertFalse(db_methods.tour_exists(99, self.mock_conn))

    def test_is_point_in_tour(self):
        self.mock_cursor.fetchone.return_value = [1]
        self.assertTrue(db_methods.is_point_in_tour(1, 10, self.mock_conn))

    def test_get_tour_point_ids(self):
        self.mock_cursor.fetchall.return_value = [(10,), (15,)]
        self.assertEqual(db_methods.get_tour_point_ids(1, self.mock_conn), [10, 15])

    # ---------------------------------------------------------------------------
    # Testes de Turistas e Visitas
    # ---------------------------------------------------------------------------

    def test_add_tourist(self):
        self.mock_cursor.fetchone.return_value = [42]
        tourist_id = db_methods.add_tourist("João", self.mock_conn)
        self.assertEqual(tourist_id, 42)
        self.mock_conn.commit.assert_called_once()

    def test_get_tourist_found(self):
        self.mock_cursor.fetchone.return_value = (1, "Maria", 2, 3)
        tourist = db_methods.get_tourist(1, self.mock_conn)
        self.assertEqual(
            tourist, {"id": 1, "name": "Maria", "tour_id": 2, "group_id": 3}
        )

    def test_get_tourist_not_found(self):
        self.mock_cursor.fetchone.return_value = None
        self.assertIsNone(db_methods.get_tourist(99, self.mock_conn))

    def test_set_tourist_tour(self):
        db_methods.set_tourist_tour(1, 5, self.mock_conn)
        # Deve ter executado DELETE e UPDATE
        self.assertEqual(self.mock_cursor.execute.call_count, 2)
        self.mock_conn.commit.assert_called_once()

    def test_add_visit(self):
        db_methods.add_visit(1, 10, self.mock_conn)
        self.mock_cursor.execute.assert_called_once()
        self.mock_conn.commit.assert_called_once()

    def test_get_visited_point_ids(self):
        self.mock_cursor.fetchall.return_value = [(10,), (20,)]
        self.assertEqual(db_methods.get_visited_point_ids(1, self.mock_conn), [10, 20])

    # ---------------------------------------------------------------------------
    # Testes de Grupos
    # ---------------------------------------------------------------------------

    def test_group_code_exists(self):
        self.mock_cursor.fetchone.return_value = [1]
        self.assertTrue(db_methods.group_code_exists("ABC12345", self.mock_conn))

    def test_create_group(self):
        self.mock_cursor.fetchone.return_value = [7]  # group_id
        group_id = db_methods.create_group("ABC12345", 1, 10, self.mock_conn)
        self.assertEqual(group_id, 7)
        self.assertEqual(self.mock_cursor.execute.call_count, 2)
        self.mock_conn.commit.assert_called_once()

    def test_get_group_by_code(self):
        self.mock_cursor.fetchone.return_value = (7, "ABC12345", 1)
        group = db_methods.get_group_by_code("ABC12345", self.mock_conn)
        self.assertEqual(group, {"id": 7, "code": "ABC12345", "tour_id": 1})

    def test_join_group(self):
        db_methods.join_group(tourist_id=2, group_id=7, tour_id=1, connection_sql=self.mock_conn)
        self.assertEqual(self.mock_cursor.execute.call_count, 2)
        self.mock_conn.commit.assert_called_once()

    def test_get_group_members(self):
        self.mock_cursor.fetchall.return_value = [
            (1, "Alice", 10),
            (1, "Alice", 20),
            (2, "Bob", None),
        ]
        members = db_methods.get_group_members(1, self.mock_conn)
        expected = [
            {"id": 1, "name": "Alice", "visited": [10, 20]},
            {"id": 2, "name": "Bob", "visited": []},
        ]
        self.assertEqual(members, expected)

    # ---------------------------------------------------------------------------
    # Testes de Usuários e Exclusões (Admin)
    # ---------------------------------------------------------------------------

    def test_username_exists(self):
        self.mock_cursor.fetchone.return_value = [1]
        self.assertTrue(db_methods.username_exists("admin", self.mock_conn))

    def test_register_user(self):
        self.mock_cursor.fetchone.return_value = [3]
        data = {"username": "user1", "password": "123", "role": "tourist"}
        user_id = db_methods.register_user(data, self.mock_conn)
        self.assertEqual(user_id, 3)
        self.mock_conn.commit.assert_called_once()

    def test_login_user(self):
        self.mock_cursor.fetchone.return_value = (3, "tourist")
        result = db_methods.login_user(
            {"username": "user1", "password": "123"}, self.mock_conn
        )
        self.assertEqual(result, (3, "tourist"))

    def test_point_exists(self):
        self.mock_cursor.fetchone.return_value = [1]
        self.assertTrue(db_methods.point_exists(1, self.mock_conn))

    def test_delete_point(self):
        db_methods.delete_point(1, self.mock_conn)
        self.mock_cursor.execute.assert_called_once()
        self.mock_conn.commit.assert_called_once()

    def test_delete_tour(self):
        db_methods.delete_tour(1, self.mock_conn)
        self.mock_cursor.execute.assert_called_once()
        self.mock_conn.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()