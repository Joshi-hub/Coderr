# Third-party
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class RegistrationTests(APITestCase):
    """Tests for POST /api/registration/"""

    url = '/api/registration/'

    def test_successful_registration_returns_201(self):
        """Valid data creates a user and returns token + user info."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'securepass123',
            'repeated_password': 'securepass123',
            'type': 'customer',
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['username'], 'newuser')
        self.assertEqual(response.data['email'], 'newuser@example.com')
        self.assertIn('user_id', response.data)

    def test_mismatched_passwords_returns_400(self):
        """Passwords that don't match are rejected."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'securepass123',
            'repeated_password': 'wrongpass',
            'type': 'customer',
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_email_returns_400(self):
        """An already-registered email is rejected."""
        User.objects.create_user(username='existing', email='taken@example.com', password='pass')
        data = {
            'username': 'newuser',
            'email': 'taken@example.com',
            'password': 'securepass123',
            'repeated_password': 'securepass123',
            'type': 'customer',
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_fields_returns_400(self):
        """Incomplete data is rejected."""
        response = self.client.post(self.url, {'username': 'x'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTests(APITestCase):
    """Tests for POST /api/login/"""

    url = '/api/login/'

    def setUp(self):
        self.user = User.objects.create_user(
            username='loginuser', email='login@example.com', password='securepass123'
        )

    def test_successful_login_returns_200(self):
        """Valid credentials return token + user info."""
        response = self.client.post(
            self.url, {'username': 'loginuser', 'password': 'securepass123'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['username'], 'loginuser')
        self.assertEqual(response.data['email'], 'login@example.com')
        self.assertIn('user_id', response.data)

    def test_wrong_password_returns_400(self):
        """Wrong password is rejected with 400."""
        response = self.client.post(
            self.url, {'username': 'loginuser', 'password': 'wrongpass'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_user_returns_400(self):
        """Unknown username is rejected with 400."""
        response = self.client.post(
            self.url, {'username': 'nobody', 'password': 'pass'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_fields_returns_400(self):
        """Missing password field is rejected."""
        response = self.client.post(self.url, {'username': 'loginuser'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
