from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from apps.users.models import User


class RegistrationTests(APITestCase):
    def test_register_creates_user(self):
        data = {
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'strongpass123',
        }
        response = self.client.post('/api/users/register/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_register_duplicate_email_fails(self):
        User.objects.create_user(username='existing', email='dup@test.com', password='pass')
        data = {'username': 'other', 'email': 'dup@test.com', 'password': 'pass'}
        response = self.client.post('/api/users/register/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='loginuser', email='login@test.com', password='testpass'
        )

    def test_login_success(self):
        response = self.client.post('/api/users/login/', {
            'email': 'login@test.com', 'password': 'testpass',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_login_wrong_password(self):
        response = self.client.post('/api/users/login/', {
            'email': 'login@test.com', 'password': 'wrong',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProfileTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='profileuser', email='profile@test.com', password='testpass'
        )
        self.client.force_authenticate(user=self.user)

    def test_get_profile(self):
        response = self.client.get('/api/users/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'profileuser')

    def test_update_profile(self):
        response = self.client.patch('/api/users/me/', {
            'first_name': 'Test', 'last_name': 'User',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Test')

    def test_profile_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/users/me/')
        self.assertIn(response.status_code, [401, 403])
