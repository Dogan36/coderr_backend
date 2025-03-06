from django.contrib.auth.models import User
from coderr_app.models import Offers, OfferDetails, Profil
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token

class TestOffersAPI(APITestCase):
    """
    Tests für die Angebote API.
    """

    def setUp(self):
        """
        Setzt Testdaten auf.
        """
        # Erstelle Benutzer
        self.business_user = User.objects.create_user(username="business_user", password="test123")
        self.customer_user = User.objects.create_user(username="customer_user", password="test123")

        # Erstelle Token für beide Benutzer
        self.business_token = Token.objects.create(user=self.business_user)
        self.customer_token = Token.objects.create(user=self.customer_user)

        # Erstelle Profile
        self.business_profile = Profil.objects.create(user=self.business_user, profile_type="business")

        # Erstelle ein Angebot und Angebotsdetails
        self.offer = Offers.objects.create(
            user=self.business_user, title="Test Offer", description="Test Description", min_price=50, min_delivery_time=3
        )

        self.offer_detail = OfferDetails.objects.create(
            offer=self.offer, title="Basic", price=50, revisions=1, delivery_time_in_days=3, features=["Feature 1"], offer_type="basic"
        )

        self.offers_url = "/api/offers/"

    def authenticate_as(self, user):
        """Setzt das Auth-Token im Header, um API-Requests als `user` zu machen."""
        if user == self.business_user:
            self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.business_token.key}')
        elif user == self.customer_user:
            self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.customer_token.key}')

    def test_get_offers(self):
        """ Testet, ob alle Angebote abrufbar sind. """
        response = self.client.get(self.offers_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_offer_as_business(self):
        """ Testet, ob ein Geschäftsnutzer ein Angebot erstellen kann. """
        self.authenticate_as(self.business_user)
        response = self.client.post(self.offers_url, {
            "title": "New Offer",
            "description": "New offer description",
           "details": [
                {
                    "title": "Basic",
                    "price": 50,
                    "revisions": 1,
                    "delivery_time_in_days": 3,
                    "features": ["Feature 1"],
                    "offer_type": "basic"
                },
                {
                    "title": "Basic",
                    "price": 50,
                    "revisions": 1,
                    "delivery_time_in_days": 3,
                    "features": ["Feature 1"],
                    "offer_type": "standard"
                },
                {
                    "title": "Basic",
                    "price": 50,
                    "revisions": 1,
                    "delivery_time_in_days": 3,
                    "features": ["Feature 1"],
                    "offer_type": "premium"
                }
            ]
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_offer_as_customer_fails(self):
        """ Testet, ob ein Kunde KEIN Angebot erstellen kann. """
        self.authenticate_as(self.customer_user)
        response = self.client.post(self.offers_url, {
            "title": "New Offer",
            "description": "New offer description",
            "min_price": 100,
            "min_delivery_time": 5,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)