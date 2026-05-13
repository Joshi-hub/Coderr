from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from profiles_app.models import UserProfile
from reviews_app.models import Review


def make_user(username, email, profile_type):
    user = User.objects.create_user(username=username, email=email, password='pass123!')
    UserProfile.objects.create(user=user, type=profile_type)
    token, _ = Token.objects.get_or_create(user=user)
    return user, token


def make_review(reviewer, business_user, rating=4, description='Good service.'):
    return Review.objects.create(
        reviewer=reviewer,
        business_user=business_user,
        rating=rating,
        description=description,
    )


class ReviewListTests(APITestCase):
    """GET /api/reviews/ — authenticated, filterable, orderable."""

    def setUp(self):
        self.biz1, self.biz1_token = make_user('biz1', 'biz1@x.com', 'business')
        self.biz2, _ = make_user('biz2', 'biz2@x.com', 'business')
        self.cust1, self.cust1_token = make_user('cust1', 'cust1@x.com', 'customer')
        self.cust2, _ = make_user('cust2', 'cust2@x.com', 'customer')
        make_review(self.cust1, self.biz1, rating=3)
        make_review(self.cust1, self.biz2, rating=5)
        make_review(self.cust2, self.biz1, rating=4)

    def test_authenticated_returns_all_reviews(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.cust1_token.key}')
        r = self.client.get('/api/reviews/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 3)

    def test_response_is_plain_list(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.cust1_token.key}')
        r = self.client.get('/api/reviews/')
        self.assertIsInstance(r.data, list)
        self.assertNotIn('results', r.data)

    def test_response_contains_expected_fields(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.cust1_token.key}')
        r = self.client.get('/api/reviews/')
        for field in ('id', 'business_user', 'reviewer', 'rating', 'description', 'created_at', 'updated_at'):
            self.assertIn(field, r.data[0])

    def test_filter_by_business_user_id(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.cust1_token.key}')
        r = self.client.get(f'/api/reviews/?business_user_id={self.biz1.id}')
        self.assertEqual(len(r.data), 2)
        self.assertTrue(all(rv['business_user'] == self.biz1.id for rv in r.data))

    def test_filter_by_reviewer_id(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.cust1_token.key}')
        r = self.client.get(f'/api/reviews/?reviewer_id={self.cust1.id}')
        self.assertEqual(len(r.data), 2)

    def test_ordering_by_rating(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.cust1_token.key}')
        r = self.client.get('/api/reviews/?ordering=rating')
        ratings = [rv['rating'] for rv in r.data]
        self.assertEqual(ratings, sorted(ratings))

    def test_ordering_by_rating_descending(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.cust1_token.key}')
        r = self.client.get('/api/reviews/?ordering=-rating')
        ratings = [rv['rating'] for rv in r.data]
        self.assertEqual(ratings, sorted(ratings, reverse=True))

    def test_unauthenticated_returns_401(self):
        r = self.client.get('/api/reviews/')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


class ReviewCreateTests(APITestCase):
    """POST /api/reviews/ — customer only, one per business user."""

    def setUp(self):
        self.biz, self.biz_token = make_user('biz', 'biz@x.com', 'business')
        self.cust, self.cust_token = make_user('cust', 'cust@x.com', 'customer')

    def _post(self, token=None, payload=None):
        if token:
            self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        else:
            self.client.credentials()
        body = payload if payload is not None else {
            'business_user': self.biz.id,
            'rating': 4,
            'description': 'Great service!',
        }
        return self.client.post('/api/reviews/', body, format='json')

    def test_customer_can_create_review(self):
        r = self._post(self.cust_token)
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_response_contains_all_fields(self):
        r = self._post(self.cust_token)
        for field in ('id', 'business_user', 'reviewer', 'rating', 'description', 'created_at', 'updated_at'):
            self.assertIn(field, r.data)

    def test_reviewer_is_set_to_request_user(self):
        r = self._post(self.cust_token)
        self.assertEqual(r.data['reviewer'], self.cust.id)

    def test_business_user_returns_403(self):
        r = self._post(self.biz_token)
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_returns_401(self):
        r = self._post()
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_duplicate_review_returns_400(self):
        self._post(self.cust_token)
        r = self._post(self.cust_token)
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rating_below_1_returns_400(self):
        r = self._post(self.cust_token, {'business_user': self.biz.id, 'rating': 0, 'description': 'X'})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rating_above_5_returns_400(self):
        r = self._post(self.cust_token, {'business_user': self.biz.id, 'rating': 6, 'description': 'X'})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reviewing_non_business_user_returns_400(self):
        r = self._post(self.cust_token, {'business_user': self.cust.id, 'rating': 4, 'description': 'X'})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


class ReviewPatchTests(APITestCase):
    """PATCH /api/reviews/{id}/ — reviewer only, rating and description only."""

    def setUp(self):
        self.biz, _ = make_user('biz', 'biz@x.com', 'business')
        self.cust, self.cust_token = make_user('cust', 'cust@x.com', 'customer')
        self.other_cust, self.other_cust_token = make_user('other', 'other@x.com', 'customer')
        self.review = make_review(self.cust, self.biz)

    def _patch(self, token, payload):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        return self.client.patch(f'/api/reviews/{self.review.id}/', payload, format='json')

    def test_reviewer_can_update_rating(self):
        r = self._patch(self.cust_token, {'rating': 5})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['rating'], 5)

    def test_reviewer_can_update_description(self):
        r = self._patch(self.cust_token, {'description': 'Updated!'})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['description'], 'Updated!')

    def test_patch_returns_all_fields(self):
        r = self._patch(self.cust_token, {'rating': 5})
        for field in ('id', 'business_user', 'reviewer', 'rating', 'description', 'created_at', 'updated_at'):
            self.assertIn(field, r.data)

    def test_invalid_rating_returns_400(self):
        r = self._patch(self.cust_token, {'rating': 10})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_user_cannot_patch(self):
        r = self._patch(self.other_cust_token, {'rating': 1})
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_returns_401(self):
        self.client.credentials()
        r = self.client.patch(f'/api/reviews/{self.review.id}/', {'rating': 5}, format='json')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_review_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.cust_token.key}')
        r = self.client.patch('/api/reviews/99999/', {'rating': 5}, format='json')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)


class ReviewDeleteTests(APITestCase):
    """DELETE /api/reviews/{id}/ — reviewer only, returns 204."""

    def setUp(self):
        self.biz, _ = make_user('biz', 'biz@x.com', 'business')
        self.cust, self.cust_token = make_user('cust', 'cust@x.com', 'customer')
        self.other_cust, self.other_cust_token = make_user('other', 'other@x.com', 'customer')
        self.review = make_review(self.cust, self.biz)

    def test_reviewer_can_delete(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.cust_token.key}')
        r = self.client.delete(f'/api/reviews/{self.review.id}/')
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Review.objects.filter(pk=self.review.id).exists())

    def test_other_user_cannot_delete(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.other_cust_token.key}')
        r = self.client.delete(f'/api/reviews/{self.review.id}/')
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_returns_401(self):
        r = self.client.delete(f'/api/reviews/{self.review.id}/')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_review_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.cust_token.key}')
        r = self.client.delete('/api/reviews/99999/')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)
