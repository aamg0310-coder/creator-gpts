from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()

class HealthCheckTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_health_check(self):
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'healthy')


class StatsTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_stats_returns_numbers(self):
        response = self.client.get('/api/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_users', response.data)
        self.assertIn('total_chatbots', response.data)


class PageViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_home_loads(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_search_loads(self):
        response = self.client.get('/buscar/')
        self.assertEqual(response.status_code, 200)

    def test_chatbot_list_loads(self):
        response = self.client.get('/lista-chatbots/')
        self.assertEqual(response.status_code, 200)

    def test_create_requires_login(self):
        response = self.client.get('/crear-chatbot/')
        self.assertEqual(response.status_code, 302)

    def test_login_page_loads(self):
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)

    def test_register_page_loads(self):
        response = self.client.get('/register/')
        self.assertEqual(response.status_code, 200)
