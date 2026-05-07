from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from offers_app.models import Offer, OfferDetail
from profiles_app.models import UserProfile


def make_user(username, email, profile_type):
    user = User.objects.create_user(username=username, email=email, password='pass123!')
    UserProfile.objects.create(user=user, type=profile_type)
    token, _ = Token.objects.get_or_create(user=user)
    return user, token


DETAIL_PAYLOAD = [
    {'title': 'Basic', 'revisions': 2, 'delivery_time_in_days': 5,
     'price': '100.00', 'features': ['Logo'], 'offer_type': 'basic'},
    {'title': 'Standard', 'revisions': 5, 'delivery_time_in_days': 7,
     'price': '200.00', 'features': ['Logo', 'Cards'], 'offer_type': 'standard'},
    {'title': 'Premium', 'revisions': 10, 'delivery_time_in_days': 10,
     'price': '500.00', 'features': ['Logo', 'Cards', 'Flyer'], 'offer_type': 'premium'},
]


def make_offer(user):
    offer = Offer.objects.create(user=user, title='Test Offer', description='Desc')
    for d in DETAIL_PAYLOAD:
        OfferDetail.objects.create(offer=offer, **{**d, 'price': d['price']})
    return offer


class OfferListTests(APITestCase):
    """GET /api/offers/ — public, paginated, filterable."""

    def setUp(self):
        self.biz, self.biz_token = make_user('biz', 'biz@x.com', 'business')
        self.offer = make_offer(self.biz)

    def test_unauthenticated_returns_200(self):
        r = self.client.get('/api/offers/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_response_is_paginated(self):
        r = self.client.get('/api/offers/')
        self.assertIn('count', r.data)
        self.assertIn('results', r.data)

    def test_result_contains_expected_fields(self):
        r = self.client.get('/api/offers/')
        offer = r.data['results'][0]
        for field in ('id', 'user', 'title', 'description', 'details', 'min_price', 'min_delivery_time', 'user_details'):
            self.assertIn(field, offer)

    def test_details_are_url_based(self):
        r = self.client.get('/api/offers/')
        detail = r.data['results'][0]['details'][0]
        self.assertIn('id', detail)
        self.assertIn('url', detail)
        self.assertNotIn('price', detail)

    def test_min_price_is_minimum_of_details(self):
        r = self.client.get('/api/offers/')
        self.assertEqual(str(r.data['results'][0]['min_price']), '100.00')

    def test_min_delivery_time_is_minimum_of_details(self):
        r = self.client.get('/api/offers/')
        self.assertEqual(r.data['results'][0]['min_delivery_time'], 5)

    def test_filter_by_creator_id(self):
        other, _ = make_user('other', 'other@x.com', 'business')
        r = self.client.get(f'/api/offers/?creator_id={self.biz.id}')
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['results'][0]['user'], self.biz.id)

    def test_filter_by_min_price(self):
        r = self.client.get('/api/offers/?min_price=200')
        self.assertEqual(r.data['count'], 0)

    def test_filter_by_max_delivery_time(self):
        r = self.client.get('/api/offers/?max_delivery_time=4')
        self.assertEqual(r.data['count'], 0)
        r2 = self.client.get('/api/offers/?max_delivery_time=5')
        self.assertEqual(r2.data['count'], 1)

    def test_search_by_title(self):
        r = self.client.get('/api/offers/?search=Test')
        self.assertEqual(r.data['count'], 1)
        r2 = self.client.get('/api/offers/?search=nonexistent')
        self.assertEqual(r2.data['count'], 0)

    def test_custom_page_size(self):
        for i in range(3):
            make_offer(self.biz)
        r = self.client.get('/api/offers/?page_size=2')
        self.assertEqual(len(r.data['results']), 2)


class OfferCreateTests(APITestCase):
    """POST /api/offers/ — business users only."""

    def setUp(self):
        self.biz, self.biz_token = make_user('biz', 'biz@x.com', 'business')
        self.cust, self.cust_token = make_user('cust', 'cust@x.com', 'customer')

    def _post(self, token=None, payload=None):
        if token:
            self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        else:
            self.client.credentials()
        body = payload or {'title': 'Offer', 'description': 'Desc', 'details': DETAIL_PAYLOAD}
        return self.client.post('/api/offers/', body, format='json')

    def test_business_user_can_create(self):
        r = self._post(self.biz_token)
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', r.data)

    def test_response_contains_full_details(self):
        r = self._post(self.biz_token)
        detail = r.data['details'][0]
        for field in ('id', 'title', 'revisions', 'delivery_time_in_days', 'price', 'features', 'offer_type'):
            self.assertIn(field, detail)

    def test_unauthenticated_returns_401(self):
        r = self._post()
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_returns_403(self):
        r = self._post(self.cust_token)
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_less_than_3_details_returns_400(self):
        r = self._post(self.biz_token, {'title': 'X', 'description': 'Y', 'details': [DETAIL_PAYLOAD[0]]})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_offer_type_returns_400(self):
        bad = [DETAIL_PAYLOAD[0], DETAIL_PAYLOAD[0], DETAIL_PAYLOAD[1]]
        r = self._post(self.biz_token, {'title': 'X', 'description': 'Y', 'details': bad})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_offer_is_owned_by_creating_user(self):
        r = self._post(self.biz_token)
        self.assertEqual(r.data.get('user', self.biz.id), self.biz.id)


class OfferRetrieveTests(APITestCase):
    """GET /api/offers/{id}/ — requires auth."""

    def setUp(self):
        self.biz, self.biz_token = make_user('biz', 'biz@x.com', 'business')
        self.offer = make_offer(self.biz)

    def test_authenticated_returns_200(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.biz_token.key}')
        r = self.client.get(f'/api/offers/{self.offer.id}/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_unauthenticated_returns_401(self):
        r = self.client.get(f'/api/offers/{self.offer.id}/')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.biz_token.key}')
        r = self.client.get('/api/offers/99999/')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_details_are_url_based(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.biz_token.key}')
        r = self.client.get(f'/api/offers/{self.offer.id}/')
        self.assertIn('url', r.data['details'][0])


class OfferPatchTests(APITestCase):
    """PATCH /api/offers/{id}/ — owner only."""

    def setUp(self):
        self.biz, self.biz_token = make_user('biz', 'biz@x.com', 'business')
        self.other, self.other_token = make_user('other', 'other@x.com', 'business')
        self.offer = make_offer(self.biz)

    def _patch(self, token, payload):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        return self.client.patch(f'/api/offers/{self.offer.id}/', payload, format='json')

    def test_owner_can_patch_title(self):
        r = self._patch(self.biz_token, {'title': 'New Title'})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['title'], 'New Title')

    def test_owner_can_patch_single_detail_by_offer_type(self):
        update = {'details': [
            {'title': 'Basic New', 'revisions': 3, 'delivery_time_in_days': 4,
             'price': '120.00', 'features': ['Logo'], 'offer_type': 'basic'}
        ]}
        r = self._patch(self.biz_token, update)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        basic = next(d for d in r.data['details'] if d['offer_type'] == 'basic')
        self.assertEqual(basic['title'], 'Basic New')

    def test_patch_returns_all_details(self):
        r = self._patch(self.biz_token, {'title': 'X'})
        self.assertEqual(len(r.data['details']), 3)

    def test_non_owner_returns_403(self):
        r = self._patch(self.other_token, {'title': 'Hacked'})
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_returns_401(self):
        self.client.credentials()
        r = self.client.patch(f'/api/offers/{self.offer.id}/', {'title': 'X'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


class OfferDeleteTests(APITestCase):
    """DELETE /api/offers/{id}/ — owner only, returns 204."""

    def setUp(self):
        self.biz, self.biz_token = make_user('biz', 'biz@x.com', 'business')
        self.other, self.other_token = make_user('other', 'other@x.com', 'business')
        self.offer = make_offer(self.biz)

    def test_owner_can_delete(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.biz_token.key}')
        r = self.client.delete(f'/api/offers/{self.offer.id}/')
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Offer.objects.filter(pk=self.offer.id).exists())

    def test_non_owner_returns_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.other_token.key}')
        r = self.client.delete(f'/api/offers/{self.offer.id}/')
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_returns_401(self):
        r = self.client.delete(f'/api/offers/{self.offer.id}/')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


class OfferDetailRetrieveTests(APITestCase):
    """GET /api/offerdetails/{id}/ — requires auth."""

    def setUp(self):
        self.biz, self.biz_token = make_user('biz', 'biz@x.com', 'business')
        self.offer = make_offer(self.biz)
        self.detail = self.offer.details.filter(offer_type='basic').first()

    def test_authenticated_returns_full_detail(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.biz_token.key}')
        r = self.client.get(f'/api/offerdetails/{self.detail.id}/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        for field in ('id', 'title', 'revisions', 'delivery_time_in_days', 'price', 'features', 'offer_type'):
            self.assertIn(field, r.data)

    def test_unauthenticated_returns_401(self):
        r = self.client.get(f'/api/offerdetails/{self.detail.id}/')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.biz_token.key}')
        r = self.client.get('/api/offerdetails/99999/')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)
