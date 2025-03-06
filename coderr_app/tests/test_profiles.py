from django.contrib.auth.models import User
from coderr_app.models import Profil
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token  # Import für Token
class TestProfilesAPI(APITestCase):
    """
    Tests für die Profile API.
    """

    def setUp(self):
        """
        Setzt Testdaten auf.
        """
        # Erstelle zwei Benutzer (ein Business, ein Customer)
        self.business_user = User.objects.create_user(username="business_user", password="test123")
        self.customer_user = User.objects.create_user(username="customer_user", password="test123")

        # Erstelle Profile für beide Benutzer
        self.business_profile = Profil.objects.create(user=self.business_user, profile_type="business", location="Berlin", tel="123456", description="Business Profile", working_hours="9-17")
        self.customer_profile = Profil.objects.create(user=self.customer_user, profile_type="customer", location="Hamburg", tel="654321", description="Customer Profile", working_hours="10-18")
        
        # 🔑 Token für Authentifizierung erstellen
        self.business_token = Token.objects.create(user=self.business_user)
        self.customer_token = Token.objects.create(user=self.customer_user)
        # URLs
        self.profile_url = f"/api/profile/{self.business_user.id}/"
       
        self.business_profiles_url = "/api/profiles/business/"
        self.customer_profiles_url = "/api/profiles/customer/"

    def test_get_profile_authenticated(self):
        """
        Testet, ob ein authentifizierter Benutzer sein eigenes Profil abrufen kann.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.business_token.key}')  # Token senden
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"], self.business_user.id)
        self.assertEqual(response.data["type"], "business")

    def test_get_profile_unauthenticated(self):
        """
        Testet, ob ein nicht-authentifizierter Benutzer ein Profil abrufen kann (sollte nicht erlaubt sein).
        """
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_profile_as_owner(self):
        """
        Testet, ob ein Benutzer sein eigenes Profil aktualisieren kann.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.business_token.key}')
        response = self.client.patch(self.profile_url, {"location": "München"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.business_profile.refresh_from_db()
        self.assertEqual(self.business_profile.location, "München")

    def test_patch_profile_as_other_user(self):
        """
        Testet, ob ein Benutzer ein fremdes Profil bearbeiten kann (sollte nicht erlaubt sein).
        """
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.customer_token.key}')
        response = self.client.patch(self.profile_url, {"location": "Frankfurt"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    
    def test_get_business_profiles(self):
        """
        Testet, ob eine Liste aller Business-Profile abgerufen werden kann.
        """
        response = self.client.get(self.business_profiles_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["type"], "business")

    def test_get_customer_profiles(self):
        """
        Testet, ob eine Liste aller Kundenprofile abgerufen werden kann.
        """
        response = self.client.get(self.customer_profiles_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["type"], "customer")