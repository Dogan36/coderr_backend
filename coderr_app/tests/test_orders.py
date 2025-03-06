from django.contrib.auth.models import User
from coderr_app.models import Orders, OfferDetails, Offers, Profil
from rest_framework.test import APITestCase
from rest_framework import status

class TestOrdersAPI(APITestCase):
    """
    Tests für die Bestellungen API.
    """

    def setUp(self):
        """
        Setzt Testdaten auf.
        """
        self.customer_user = User.objects.create_user(username="customer_user", password="test123")
        self.business_user = User.objects.create_user(username="business_user", password="test123")
        self.admin_user = User.objects.create_superuser(username="admin", password="admin123")

        self.customer_profile = Profil.objects.create(user=self.customer_user, profile_type="customer")
        self.business_profile = Profil.objects.create(user=self.business_user, profile_type="business")

        self.offer = Offers.objects.create(user=self.business_user, title="Test Offer", description="Test", min_price=10, min_delivery_time=3)
        self.offer_detail = OfferDetails.objects.create(
            offer=self.offer, title="Basic", price=10, revisions=1, delivery_time_in_days=3, features=["Test"], offer_type="basic"
        )

        self.order = Orders.objects.create(
            customer_user=self.customer_profile, business_user=self.business_user,
            title="Order Test", revisions=1, delivery_time_in_days=3, price=10,
            features=["Test"], offer_type="basic", status="in_progress"
        )

        self.orders_url = "/api/orders/"

    def test_get_orders(self):
        """ Testet, ob ein eingeloggter Benutzer seine Bestellungen sehen kann. """
        self.client.login(username="customer_user", password="test123")
        response = self.client.get(self.orders_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_order_as_customer(self):
        """ Testet, ob ein Kunde eine Bestellung erstellen kann. """
        self.client.login(username="customer_user", password="test123")
        response = self.client.post(self.orders_url, {"offer_detail_id": self.offer_detail.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_order_as_business_user_fails(self):
        """ Testet, ob ein Anbieter KEINE Bestellung erstellen kann. """
        self.client.login(username="business_user", password="test123")
        response = self.client.post(self.orders_url, {"offer_detail_id": self.offer_detail.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)