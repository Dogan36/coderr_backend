from django.contrib.auth.models import User
from coderr_app.models import Profil
from rest_framework.test import APITestCase
from rest_framework import status

class TestReviewsAPI(APITestCase):
    """
    Tests für die Bewertungen API.
    """

    def setUp(self):
        """
        Setzt Testdaten auf.
        """
        self.business_user = User.objects.create_user(username="business_user", password="test123")
        self.customer_user = User.objects.create_user(username="customer_user", password="test123")

        self.business_profile = Profil.objects.create(user=self.business_user, profile_type="business")
        self.customer_profile = Profil.objects.create(user=self.customer_user, profile_type="customer")

        self.reviews_url = "/api/reviews/"

    def test_get_reviews(self):
        """ Testet, ob Bewertungen abrufbar sind. """
        response = self.client.get(self.reviews_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_review_as_customer(self):
        """ Testet, ob ein Kunde eine Bewertung abgeben kann. """
        self.client.login(username="customer_user", password="test123")
        response = self.client.post(self.reviews_url, {
            "business_user": self.business_user.id,
            "rating": 5,
            "description": "Great service!"
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_review_as_business_fails(self):
        """ Testet, ob ein Anbieter KEINE Bewertung abgeben kann. """
        self.client.login(username="business_user", password="test123")
        response = self.client.post(self.reviews_url, {
            "business_user": self.business_user.id,
            "rating": 5,
            "description": "Great service!"
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)