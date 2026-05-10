from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from offers_app.models import Offer, OfferDetail
from orders_app.models import Order
from profiles_app.models import UserProfile


def make_user(username, email, profile_type, is_staff=False):
    user = User.objects.create_user(username=username, email=email, password='pass123!', is_staff=is_staff)
    UserProfile.objects.create(user=user, type=profile_type)
    token, _ = Token.objects.get_or_create(user=user)
    return user, token


def make_offer_with_details(business_user):
    offer = Offer.objects.create(user=business_user, title='Test Offer', description='Desc')
    details = []
    for ot, price, days in [('basic', 100, 5), ('standard', 200, 7), ('premium', 500, 10)]:
        details.append(OfferDetail.objects.create(
            offer=offer, title=f'{ot.title()} Plan', revisions=2,
            delivery_time_in_days=days, price=str(price),
            features=['Feature A'], offer_type=ot,
        ))
    return offer, details


def make_order(customer, business):
    _, details = make_offer_with_details(business)
    return Order.objects.create(
        customer_user=customer,
        business_user=business,
        title=details[0].title,
        revisions=details[0].revisions,
        delivery_time_in_days=details[0].delivery_time_in_days,
        price=details[0].price,
        features=details[0].features,
        offer_type=details[0].offer_type,
    )


class OrderListTests(APITestCase):
    """GET /api/orders/ — authenticated, user sees only their own orders."""

    def setUp(self):
        self.biz, self.biz_token = make_user('biz', 'biz@x.com', 'business')
        self.cust, self.cust_token = make_user('cust', 'cust@x.com', 'customer')
        self.other_cust, _ = make_user('other', 'other@x.com', 'customer')
        self.order = make_order(self.cust, self.biz)

    def test_customer_sees_own_orders(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.cust_token.key}')
        r = self.client.get('/api/orders/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 1)

    def test_business_sees_own_orders(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.biz_token.key}')
        r = self.client.get('/api/orders/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 1)

    def test_unrelated_user_sees_no_orders(self):
        other_biz, other_tok = make_user('other_biz', 'ob@x.com', 'business')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {other_tok.key}')
        r = self.client.get('/api/orders/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 0)

    def test_response_is_plain_list_not_paginated(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.cust_token.key}')
        r = self.client.get('/api/orders/')
        self.assertIsInstance(r.data, list)
        self.assertNotIn('results', r.data)

    def test_order_contains_expected_fields(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.cust_token.key}')
        r = self.client.get('/api/orders/')
        order = r.data[0]
        for field in ('id', 'customer_user', 'business_user', 'title', 'revisions',
                      'delivery_time_in_days', 'price', 'features', 'offer_type',
                      'status', 'created_at', 'updated_at'):
            self.assertIn(field, order)

    def test_unauthenticated_returns_401(self):
        r = self.client.get('/api/orders/')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


class OrderCreateTests(APITestCase):
    """POST /api/orders/ — customer only, from offer_detail_id."""

    def setUp(self):
        self.biz, self.biz_token = make_user('biz', 'biz@x.com', 'business')
        self.cust, self.cust_token = make_user('cust', 'cust@x.com', 'customer')
        _, self.details = make_offer_with_details(self.biz)
        self.basic_detail = self.details[0]

    def _post(self, token=None, payload=None):
        if token:
            self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        else:
            self.client.credentials()
        body = payload if payload is not None else {'offer_detail_id': self.basic_detail.id}
        return self.client.post('/api/orders/', body, format='json')

    def test_customer_can_create_order(self):
        r = self._post(self.cust_token)
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_order_fields_are_copied_from_detail(self):
        r = self._post(self.cust_token)
        self.assertEqual(r.data['title'], self.basic_detail.title)
        self.assertEqual(r.data['offer_type'], 'basic')
        self.assertEqual(r.data['customer_user'], self.cust.id)
        self.assertEqual(r.data['business_user'], self.biz.id)

    def test_initial_status_is_in_progress(self):
        r = self._post(self.cust_token)
        self.assertEqual(r.data['status'], 'in_progress')

    def test_business_user_returns_403(self):
        r = self._post(self.biz_token)
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_returns_401(self):
        r = self._post()
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_offer_detail_id_returns_400(self):
        r = self._post(self.cust_token, {})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_offer_detail_id_returns_400(self):
        r = self._post(self.cust_token, {'offer_detail_id': 'abc'})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_offer_detail_id_returns_404(self):
        r = self._post(self.cust_token, {'offer_detail_id': 99999})
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)


class OrderPatchTests(APITestCase):
    """PATCH /api/orders/{id}/ — business_user of the order only, status field only."""

    def setUp(self):
        self.biz, self.biz_token = make_user('biz', 'biz@x.com', 'business')
        self.cust, self.cust_token = make_user('cust', 'cust@x.com', 'customer')
        self.other_biz, self.other_biz_token = make_user('other_biz', 'ob@x.com', 'business')
        self.order = make_order(self.cust, self.biz)

    def _patch(self, token, payload):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        return self.client.patch(f'/api/orders/{self.order.id}/', payload, format='json')

    def test_business_user_can_update_status_to_completed(self):
        r = self._patch(self.biz_token, {'status': 'completed'})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['status'], 'completed')

    def test_business_user_can_update_status_to_cancelled(self):
        r = self._patch(self.biz_token, {'status': 'cancelled'})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['status'], 'cancelled')

    def test_invalid_status_returns_400(self):
        r = self._patch(self.biz_token, {'status': 'invalid_status'})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_response_contains_all_fields(self):
        r = self._patch(self.biz_token, {'status': 'completed'})
        for field in ('id', 'customer_user', 'business_user', 'title', 'status'):
            self.assertIn(field, r.data)

    def test_customer_cannot_patch(self):
        r = self._patch(self.cust_token, {'status': 'completed'})
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_business_user_cannot_patch(self):
        r = self._patch(self.other_biz_token, {'status': 'completed'})
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_returns_401(self):
        self.client.credentials()
        r = self.client.patch(f'/api/orders/{self.order.id}/', {'status': 'completed'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_order_returns_404(self):
        r = self._patch(self.biz_token, {'status': 'completed'})
        r2 = self.client.patch('/api/orders/99999/', {'status': 'completed'}, format='json')
        self.assertEqual(r2.status_code, status.HTTP_404_NOT_FOUND)


class OrderDeleteTests(APITestCase):
    """DELETE /api/orders/{id}/ — staff only, returns 204."""

    def setUp(self):
        self.biz, self.biz_token = make_user('biz', 'biz@x.com', 'business')
        self.cust, self.cust_token = make_user('cust', 'cust@x.com', 'customer')
        self.staff, self.staff_token = make_user('staff', 'staff@x.com', 'business', is_staff=True)
        self.order = make_order(self.cust, self.biz)

    def test_staff_can_delete(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.staff_token.key}')
        r = self.client.delete(f'/api/orders/{self.order.id}/')
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Order.objects.filter(pk=self.order.id).exists())

    def test_non_staff_business_user_cannot_delete(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.biz_token.key}')
        r = self.client.delete(f'/api/orders/{self.order.id}/')
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_cannot_delete(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.cust_token.key}')
        r = self.client.delete(f'/api/orders/{self.order.id}/')
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_returns_401(self):
        r = self.client.delete(f'/api/orders/{self.order.id}/')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


class OrderCountTests(APITestCase):
    """GET /api/order-count/{business_user_id}/ — in_progress count."""

    def setUp(self):
        self.biz, self.biz_token = make_user('biz', 'biz@x.com', 'business')
        self.cust, self.cust_token = make_user('cust', 'cust@x.com', 'customer')
        make_order(self.cust, self.biz)
        order2 = make_order(self.cust, self.biz)
        order2.status = 'completed'
        order2.save()

    def test_returns_in_progress_count(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.cust_token.key}')
        r = self.client.get(f'/api/order-count/{self.biz.id}/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['order_count'], 1)

    def test_nonexistent_business_user_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.cust_token.key}')
        r = self.client.get('/api/order-count/99999/')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_customer_id_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.cust_token.key}')
        r = self.client.get(f'/api/order-count/{self.cust.id}/')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_returns_401(self):
        r = self.client.get(f'/api/order-count/{self.biz.id}/')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


class CompletedOrderCountTests(APITestCase):
    """GET /api/completed-order-count/{business_user_id}/ — completed count."""

    def setUp(self):
        self.biz, self.biz_token = make_user('biz', 'biz@x.com', 'business')
        self.cust, self.cust_token = make_user('cust', 'cust@x.com', 'customer')
        order1 = make_order(self.cust, self.biz)
        order1.status = 'completed'
        order1.save()
        order2 = make_order(self.cust, self.biz)
        order2.status = 'completed'
        order2.save()
        make_order(self.cust, self.biz)  # still in_progress

    def test_returns_completed_count(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.cust_token.key}')
        r = self.client.get(f'/api/completed-order-count/{self.biz.id}/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['completed_order_count'], 2)

    def test_nonexistent_business_user_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.cust_token.key}')
        r = self.client.get('/api/completed-order-count/99999/')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_customer_id_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.cust_token.key}')
        r = self.client.get(f'/api/completed-order-count/{self.cust.id}/')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_returns_401(self):
        r = self.client.get(f'/api/completed-order-count/{self.biz.id}/')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)
