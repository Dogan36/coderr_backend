from django.contrib.auth.models import User
from coderr_app.models import Offers, Profil
from rest_framework.test import APITestCase
from rest_framework import status

class TestStatisticsAPI(APITestCase):
    """
    Tests für die Statistik API.
    """

    def setUp(self):
        """
        Setzt Testdaten auf.
        """
        self.business_user = User.objects.create_user(username="business_user", password="test123")
        self.business_profile = Profil.objects.create(user=self.business_user, profile_type="business")

        self.offer = Offers.objects.create(user=self.business_user, title="Test Offer", description="Test", min_price=10, min_delivery_time=3)

        self.statistics_url = "/api/base-info/"

    def test_get_statistics(self):
        """ Testet, ob Basisstatistiken abrufbar sind. """
        response = self.client.get(self.statistics_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)