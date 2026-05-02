# Third-party
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

# Local
from profiles_app.models import UserProfile


def create_user(username, email, user_type):
    """Helper: create a user with a profile and return (user, token)."""
    user = User.objects.create_user(username=username, email=email, password='pass123!')
    UserProfile.objects.create(user=user, type=user_type)
    token, _ = Token.objects.get_or_create(user=user)
    return user, token


class ProfileRetrieveTests(APITestCase):
    """Tests for GET /api/profile/{pk}/"""

    def setUp(self):
        self.user, self.token = create_user('alice', 'alice@example.com', 'customer')
        self.url = f'/api/profile/{self.user.id}/'

    def test_authenticated_user_can_retrieve_profile(self):
        """Any authenticated user can view a profile."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'alice')
        self.assertEqual(response.data['type'], 'customer')
        self.assertIn('email', response.data)
        self.assertIn('created_at', response.data)

    def test_string_fields_are_never_null(self):
        """first_name, last_name, location, tel, description, working_hours return '' not null."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        response = self.client.get(self.url)
        for field in ['first_name', 'last_name', 'location', 'tel', 'description', 'working_hours']:
            self.assertIsNotNone(response.data[field], msg=f'{field} must not be null')

    def test_unauthenticated_request_returns_401(self):
        """Unauthenticated requests are rejected."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unknown_profile_returns_404(self):
        """Non-existent user id returns 404."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        response = self.client.get('/api/profile/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ProfileUpdateTests(APITestCase):
    """Tests for PATCH /api/profile/{pk}/"""

    def setUp(self):
        self.user, self.token = create_user('bob', 'bob@example.com', 'business')
        self.other_user, self.other_token = create_user('eve', 'eve@example.com', 'customer')
        self.url = f'/api/profile/{self.user.id}/'

    def test_owner_can_patch_own_profile(self):
        """Profile owner can update their own profile fields."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        response = self.client.patch(self.url, {'location': 'Berlin'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['location'], 'Berlin')

    def test_owner_can_update_email(self):
        """Profile owner can change their email address."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        response = self.client.patch(self.url, {'email': 'new@example.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'new@example.com')

    def test_duplicate_email_returns_400(self):
        """Cannot change email to one already in use by another user."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        response = self.client.patch(self.url, {'email': 'eve@example.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_owner_cannot_patch_profile(self):
        """A different authenticated user cannot update someone else's profile."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.other_token.key}')
        response = self.client.patch(self.url, {'location': 'Hacked'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_type_field_is_read_only(self):
        """The type field cannot be changed via PATCH."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        self.client.patch(self.url, {'type': 'customer'}, format='json')
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.type, 'business')

    def test_unauthenticated_patch_returns_401(self):
        """Unauthenticated PATCH is rejected."""
        response = self.client.patch(self.url, {'location': 'Berlin'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class BusinessProfileListTests(APITestCase):
    """Tests for GET /api/profiles/business/"""

    def setUp(self):
        self.user, self.token = create_user('biz1', 'biz1@example.com', 'business')
        create_user('cust1', 'cust1@example.com', 'customer')

    def test_returns_only_business_profiles(self):
        """Only business profiles are returned."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        response = self.client.get('/api/profiles/business/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertTrue(all(p['type'] == 'business' for p in response.data))

    def test_response_is_not_paginated(self):
        """Response is a plain list, not a paginated object."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        response = self.client.get('/api/profiles/business/')
        self.assertIsInstance(response.data, list)
        self.assertNotIn('results', response.data)

    def test_email_not_in_list_response(self):
        """Email is not exposed in the list endpoint."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        response = self.client.get('/api/profiles/business/')
        for profile in response.data:
            self.assertNotIn('email', profile)

    def test_unauthenticated_request_returns_401(self):
        response = self.client.get('/api/profiles/business/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CustomerProfileListTests(APITestCase):
    """Tests for GET /api/profiles/customer/"""

    def setUp(self):
        self.user, self.token = create_user('cust2', 'cust2@example.com', 'customer')
        create_user('biz2', 'biz2@example.com', 'business')

    def test_returns_only_customer_profiles(self):
        """Only customer profiles are returned."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        response = self.client.get('/api/profiles/customer/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertTrue(all(p['type'] == 'customer' for p in response.data))

    def test_response_is_not_paginated(self):
        """Response is a plain list, not a paginated object."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        response = self.client.get('/api/profiles/customer/')
        self.assertIsInstance(response.data, list)

    def test_unauthenticated_request_returns_401(self):
        response = self.client.get('/api/profiles/customer/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RegistrationCreatesProfileTests(APITestCase):
    """Ensures that registration automatically creates a UserProfile."""

    def test_registration_creates_profile_with_correct_type(self):
        """A UserProfile with the correct type is created after registration."""
        data = {
            'username': 'newbiz',
            'email': 'newbiz@example.com',
            'password': 'securepass123',
            'repeated_password': 'securepass123',
            'type': 'business',
        }
        response = self.client.post('/api/registration/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='newbiz')
        self.assertTrue(hasattr(user, 'profile'))
        self.assertEqual(user.profile.type, 'business')
