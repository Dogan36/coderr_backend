

from django.db.models import Min, Max, DecimalField, IntegerField
from django.db.models.functions import Coalesce
from rest_framework import viewsets, generics, status, filters, mixins
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from ..models import Offers, OfferDetails, Orders, Profil, Reviews
from .serializers import OffersSerializer, OfferDetailsSerializer, OrdersSerializer, ProfilSerializer, ReviewsSerializer, UserSerializer, ProfilTypeSerializer, OrderCreateSerializer
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from django.db.models import Avg
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from coderr_app.api.permissions import IsBusinessForCreateOnly, IsBusinessForPatchOnly, IsCustomerForCreateOnly, IsOwnerForPatchOnly, IsAdminOrCustomPermission, IsOwnerOfProfile, IsUniqueReviewer, IsOwnerCustomerOrAdmin
from rest_framework.generics import RetrieveUpdateAPIView
from .pagination import LargeResultsSetPagination

class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users.

    - Provides CRUD operations for user accounts.
    - Uses `UserSerializer` for serialization.
    - Ensures that the authenticated user is assigned automatically on creation.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)




class OffersViewSet(viewsets.ModelViewSet):
    """
    ViewSet für Angebote.

    - Authentifizierung erforderlich.
    - `POST`: Nur Business-User dürfen erstellen.
    - `PATCH/DELETE`: Nur Business-User dürfen ihre eigenen Angebote ändern.
    - `GET`: Alle authentifizierten Benutzer dürfen Angebote sehen.
    """
    queryset = Offers.objects.all()
    serializer_class = OffersSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['title', 'description']
    filterset_fields = ['user']
    pagination_class = LargeResultsSetPagination
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    def get_object(self):
        """
        Holt das `Offer`-Objekt. Falls es nicht existiert, gibt es `404 Not Found` zurück.
        Danach werden die Objekt-Permissions geprüft.
        """
        obj = get_object_or_404(Offers, pk=self.kwargs.get("pk"))  # Zuerst prüfen, ob das Objekt existiert
        print(f"🔍 get_object() liefert: {obj}")  
        
        self.check_object_permissions(self.request, obj)  # Erst jetzt die Berechtigungen prüfen
        return obj
    def get_permissions(self):
        """
        Setzt verschiedene Berechtigungen je nach HTTP-Methode.
        """
        print(f"🔑 Request Methode: {self.request.method}")  

        if self.action == "retrieve":  # Einzelnes Angebot abrufen
            return [IsAuthenticated()]

        if self.action == "create":  # `POST`
            return [IsAuthenticated(), IsBusinessForCreateOnly()]
        
        if self.action in ["update", "partial_update", "destroy"]:  # `PATCH` und `DELETE`
            return [IsAuthenticated()]  # Hier nur Authentifizierung prüfen, nicht Ownership!

        return []  # `list` bleibt öffentlich
    
    

    def perform_create(self, serializer):
        """
        Erstellt ein neues Angebot und speichert das Bild.
        """
        instance = serializer.save(user=self.request.user)  
        image = self.request.FILES.get('image', None)
        if image:
            instance = serializer.instance
            instance.image = image
            instance.save()
        

    def update(self, request, *args, **kwargs):
        """
        Überschreibt `update()`, um `PATCH` zu unterstützen.
        """
        print("🔄 update() in View wird aufgerufen!")  
        kwargs['partial'] = True  # `PATCH` erlaubt partielle Updates
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        """
        Behandelt das eigentliche Update des Angebots:
        - Normale Felder werden aktualisiert.
        - Falls `offer_details` vorhanden sind, werden sie neu erstellt.
        - `min_price` & `min_delivery_time` werden aktualisiert.
        """
        print("🔄 perform_update() wird aufgerufen!")  

        instance = serializer.instance
        validated_data = serializer.validated_data

        # 🔹 Datei-Upload (`image`) separat behandeln
        image = self.request.FILES.get('image', None)
        if image:
            instance.image = image

        # 🔹 Standard-Felder aktualisieren (außer `offer_details`)
        for attr, value in validated_data.items():
            if attr != "offer_details":  # `offer_details` separat behandeln
                setattr(instance, attr, value)
        print(self.request.data)
        # 🔹 Falls `offer_details` mitgeschickt wurden, alte löschen & neu erstellen
        details_data = self.request.data.get("details", None)
        print(f"🔍 Neue offer_details: {details_data}")
        if details_data is not None:
            print("🛠 Aktualisiere offer_details...")
            instance.offer_details.all().delete()
            new_details = [OfferDetails(offer=instance, **detail_data) for detail_data in details_data]
            OfferDetails.objects.bulk_create(new_details)

        # 🔹 `min_price` & `min_delivery_time` neu berechnen
        aggregated = OfferDetails.objects.filter(offer=instance).aggregate(
            min_price=Min("price"),
            min_delivery_time=Min("delivery_time_in_days")
        )
        instance.min_price = aggregated.get('min_price') or 0
        instance.min_delivery_time = aggregated.get('min_delivery_time') or 0

        instance.save()  # 🔥 Alle Änderungen speichern!
        print("✅ Update erfolgreich gespeichert.")

    def get_queryset(self):
        """
        Gibt gefilterte Angebote basierend auf Query-Parametern zurück.
        """
        queryset = Offers.objects.all()
        params = self.request.query_params

        creator_id = params.get("creator_id")
        min_price = params.get("min_price")
        max_delivery_time = params.get("max_delivery_time")
        ordering = params.get("ordering", "created_at")

        # Sortierung anwenden
        if ordering in ["created_at", "-created_at", "updated_at", "-updated_at"]:
            queryset = queryset.order_by(ordering)

        # Filter anwenden
        if creator_id:
            queryset = queryset.filter(user_id=creator_id)
        if min_price:
            try:
                queryset = queryset.filter(min_price__gte=float(min_price))
            except ValueError:
                pass
        if max_delivery_time:
            if not max_delivery_time.isdigit():
                raise ValueError("Max delivery time must be a number.")
            queryset = queryset.filter(min_delivery_time__lte=int(max_delivery_time))

        return queryset

    def list(self, request, *args, **kwargs):
        """
        Gibt eine paginierte Liste der Angebote zurück.
        """
        try:
            queryset = self.filter_queryset(self.get_queryset())
        except ValueError as e:
            return Response({"error": str(e)}, status=400)  # Direkt zurückgeben!

        # Paginierung anwenden
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Löscht ein Angebot und gibt `{}` als Response zurück.
        """
        instance = self.get_object()  # Das Objekt abrufen
        self.perform_destroy(instance)  # Standard-Löschlogik von DRF aufrufen
        return Response({}, status=status.HTTP_204_NO_CONTENT)  # ✅ `{}` zurückgeben
    
class OfferDetailsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing offer details.

    - Provides CRUD operations for `OfferDetails`.
    - Each `OfferDetails` entry is linked to an `Offer`.
    - Allows retrieving, creating, updating, and deleting offer details.
    """
    queryset = OfferDetails.objects.all()
    serializer_class = OfferDetailsSerializer


class OrdersViewSet(viewsets.ModelViewSet):
    """
    ViewSet für Bestellungen (Orders).
    
    - `GET /orders/` → Liste der eigenen Bestellungen (als Kunde oder Anbieter).
    - `POST /orders/` → Bestellung erstellen (Nur `customer_user` erlaubt).
    - `GET /orders/{id}/` → Details einer Bestellung abrufen.
    - `PATCH /orders/{id}/` → Nur der Business-User oder ein Admin darf `status` ändern.
    - `DELETE /orders/{id}/` → Nur Admins dürfen Bestellungen löschen.
    """
    queryset = Orders.objects.all()
    def get_permissions(self):
        """
        Setzt verschiedene Berechtigungen je nach HTTP-Methode:
        - `POST`: Nur Kunden (`IsCustomerForCreateOnly`).
        - `PATCH`: Nur Anbieter (`business_user`) oder Admins (`IsBusinessForPatchOnly`).
        - `DELETE`: Nur Admins (`IsAdminOrCustomPermission`).
        """
        if self.request.method == "POST":
            return [IsCustomerForCreateOnly()]
        if self.request.method == "PATCH":
            return [IsBusinessForPatchOnly()]
        if self.request.method == "DELETE":
            return [IsAdminOrCustomPermission()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        """
        Nutzt `OrderCreateSerializer` für `POST`, sonst `OrdersSerializer`.
        """
        if self.request.method == "POST":
            return OrderCreateSerializer
        return OrdersSerializer

    def get_queryset(self):
        """
        Gibt NUR die Bestellungen zurück, an denen der Benutzer beteiligt ist.
        """
        user = self.request.user

        if user.is_staff:
            return Orders.objects.all()  # Admins sehen ALLES

        return Orders.objects.filter(customer_user=user) | Orders.objects.filter(business_user=user)
    def create(self, request, *args, **kwargs):
        """
        Erstellt eine Bestellung basierend auf einem Angebot.
        """
        print("🛒 Neue Bestellung wird erstellt...")  # Debug-Log
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        order = serializer.save()  # Speichert die Bestellung

        # ✅ Rückgabe des erstellten Objekts als JSON
        output_serializer = OrdersSerializer(order, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """
        - Nur `status` darf per PATCH geändert werden.
        - Nur der `business_user` kann den Status ändern.
        - Admins dürfen ALLES ändern.
        """
        print("🔄 PATCH Request für Bestellung erkannt!")

        instance = self.get_object()

        new_status = request.data.get("status")
        valid_status_choices = [choice[0] for choice in Orders.status_choices]

        if new_status not in valid_status_choices:
            return Response(
                {"error": f"Ungültiger Status. Erlaubt: {valid_status_choices}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.status = new_status
        instance.save()
        serializer = self.get_serializer(instance)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """
        - NUR Admins dürfen Bestellungen löschen.
        """
        instance = self.get_object()

        instance.delete()
        return Response({}, status=status.HTTP_200_OK)
    
    
class ProfileDetailView(RetrieveUpdateAPIView):
    """
    API-View für das Abrufen und Aktualisieren eines Profils.
    """
    queryset = Profil.objects.all()
    serializer_class = ProfilSerializer
    permission_classes = [IsAuthenticated, IsOwnerOfProfile]

    def get_object(self):
        """
        Holt das `Profil` anhand der User-ID (`pk` ist die `user_id`).
        """
        obj = get_object_or_404(Profil, user__id=self.kwargs["pk"])
        
        # 🔍 Debugging: Prüfe, ob `has_object_permission` überhaupt aufgerufen wird
        self.check_object_permissions(self.request, obj)

        return obj

    def perform_update(self, serializer):
        """
        Speichert das Bild korrekt in das Profil-Modell und gibt Debugging-Infos aus.
        """
        print("🔄 perform_update() wird aufgerufen...")  # Debugging
        print(f"🔑 Request User: {self.request.user}")  
        print(f"👤 Profil gehört zu: {self.get_object().user}")
        
        print(self.request.FILES)  # Debugging
        # Überprüfe, ob eine Datei hochgeladen wurde
        file = self.request.FILES.get("file", None)
        print(f"📸 Hochgeladenes Bild: {file}")  # Debugging
        
        if file is not None:
            instance = serializer.instance
            print(f"✅ Speichere Bild für Benutzer {instance.user}")  # Debugging
            instance.file = file  # Falls das Feld `image` heißt
            instance.save()
        else:
            print("⚠️ Kein Bild hochgeladen, speichere normale Updates...")  # Debugging
            serializer.save()

    
        
class BusinessProfilesListView(generics.ListAPIView):
    """
    API view for listing all business profiles.

    - Uses `ProfilTypeSerializer` to serialize the data.
    - Returns only profiles where `type="business"`.
    """
    serializer_class = ProfilTypeSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        """
        Filters the queryset to return only business profiles.
        """
        return Profil.objects.filter(profile_type="business")


class CustomerProfilesListView(generics.ListAPIView):
    """
    API view for listing all customer profiles.
    
    - Uses `ProfilTypeSerializer` to serialize the data.
    - Returns only profiles where `type="customer"`.
    """
    serializer_class = ProfilTypeSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        """
        Filters the queryset to return only customer profiles.
        """
        return Profil.objects.filter(profile_type="customer")


  
class ReviewsViewSet(viewsets.ModelViewSet):
    """
    ViewSet für die Verwaltung von Bewertungen.
    
    - Alle Benutzer können Bewertungen sehen.
    - Nur `customer`-Nutzer können neue Bewertungen erstellen.
    - Eine Firma kann nur einmal von demselben Benutzer bewertet werden.
    - Nur der Ersteller oder ein Admin darf eine Bewertung bearbeiten oder löschen.
    """

    queryset = Reviews.objects.all()
    serializer_class = ReviewsSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["updated_at", "rating"]
    permission_classes = [IsAuthenticated, IsCustomerForCreateOnly, IsUniqueReviewer, IsOwnerCustomerOrAdmin]
    def get_queryset(self):
        """
        Gibt Bewertungen basierend auf Filter-Parametern zurück:
        - `business_user_id`: Bewertungen eines bestimmten Geschäftsbenutzers.
        - `reviewer_id`: Bewertungen eines bestimmten Erstellers.
        """
        queryset = Reviews.objects.all()
        business_user_id = self.request.query_params.get("business_user_id")
        reviewer_id = self.request.query_params.get("reviewer_id")

        if business_user_id:
            queryset = queryset.filter(business_user_id=business_user_id)
        if reviewer_id:
            queryset = queryset.filter(reviewer_id=reviewer_id)

        return queryset

    def perform_create(self, serializer):
        """
        Erstellt eine neue Bewertung:
        - Prüft, ob das Business bereits vom Benutzer bewertet wurde.
        - Prüft, ob der Benutzer überhaupt ein `customer`-Profil hat.
        """
        request_user = self.request.user
        
        serializer.save(reviewer=request_user)

    def perform_update(self, serializer):
        """
        Bearbeitet eine Bewertung:
        - Nur der Ersteller oder ein Admin darf eine Bewertung ändern.
        - Nur `rating` und `description` dürfen bearbeitet werden.
        """
        instance = self.get_object()
        request_user = self.request.user

        # Prüfe, ob der Benutzer der Ersteller oder ein Admin ist
        if instance.reviewer != request_user and not request_user.is_staff:
            return Response(
                {"error": "Nur der Ersteller oder ein Admin darf die Bewertung bearbeiten."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Nur bestimmte Felder dürfen aktualisiert werden
        allowed_fields = {"rating", "description"}
        invalid_fields = set(serializer.validated_data.keys()) - allowed_fields

        if invalid_fields:
            return Response(
                {"error": f"Diese Felder können nicht aktualisiert werden: {', '.join(invalid_fields)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer.save()

    def perform_destroy(self, instance):
        """
        Löscht eine Bewertung:
        - Nur der Ersteller oder ein Admin darf eine Bewertung löschen.
        """
        request_user = self.request.user
        if instance.reviewer != request_user and not request_user.is_staff:
            return Response(
                {"error": "Nur der Ersteller oder ein Admin darf die Bewertung löschen."},
                status=status.HTTP_403_FORBIDDEN
            )
        instance.delete()
        
class LoginAPIView(APIView):
    """
    API endpoint for user login.

    - Authenticates a user using username and password.
    - Returns an authentication token upon successful login.
    - Does not require authentication to access (`permission_classes = []`).
    """
    permission_classes = []
    
    def post(self, request):
        """
        Handles user login.

        - Retrieves `username` and `password` from request data.
        - Authenticates the user using Django's `authenticate()`.
        - Returns a 400 error if authentication fails.
        - If successful, generates or retrieves an authentication token.
        """
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)
        if user is None:
            return Response({"detail": "Falsche Anmeldedaten"}, status=status.HTTP_400_BAD_REQUEST)

        token, created = Token.objects.get_or_create(user=user)
        return Response({"user_id": user.id, "username": user.username, "email": user.email, "token": token.key})

class RegisterAPIView(APIView):
    """
    API endpoint for user registration.

    - Allows new users to create an account.
    - Validates username, email, and password.
    - Ensures unique usernames and emails.
    - Creates an authentication token upon successful registration.
    """
    permission_classes = []
    def post(self, request):
        """
        Handles user registration.

        - Retrieves `username`, `email`, `password`, and `repeated_password` from the request.
        - Ensures all fields are provided.
        - Validates email format.
        - Ensures passwords match.
        - Checks for unique username and email.
        - Creates a new user and an associated profile.
        - Generates an authentication token for the new user.
        """
        username = request.data.get("username")
        password = request.data.get("password")
        repeated_password = request.data.get("repeated_password")
        email = request.data.get("email")
        type = request.data.get("type")
        print("🔑 Registrierungsdaten:", username, email, type)
        # Validate required fields
        if not username:
            return Response({"error": "Username ist erforderlich."}, status=status.HTTP_400_BAD_REQUEST)
        if not email:
            return Response({"error": "Email ist erforderlich."}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({"error": "Passwort ist erforderlich."}, status=status.HTTP_400_BAD_REQUEST)
        if not type:
            return Response({"error": "Type ist erforderlich."}, status=status.HTTP_400_BAD_REQUEST)
        # Validate email format
        try:
            validate_email(email)
        except ValidationError:
            return Response({"error": "Ungültige E-Mail-Adresse."}, status=status.HTTP_400_BAD_REQUEST)
        # Ensure passwords match
        if password != repeated_password:
            return Response({"password": "Das Passwort ist nicht gleich mit dem wiederholten Passwort"}, status=status.HTTP_400_BAD_REQUEST)
        # Ensure unique username and email
        if User.objects.filter(username=username).exists():
            return Response({"error": "Dieser Benutzername ist bereits vergeben."}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({"error": "Diese E-Mail-Adresse wird bereits verwendet."}, status=status.HTTP_400_BAD_REQUEST)
        # Create user and associated profile
        user = User.objects.create_user(username=username, password=password, email=email)
        Profil.objects.create(user=user, profile_type=type)  # Profil für den User erstellen
        token, _ = Token.objects.get_or_create(user=user)  # Token erstellen

        return Response({
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "profile_type": type,
            "token": token.key
        }, status=status.HTTP_201_CREATED)

        
class BaseInfoViewSet(viewsets.ViewSet):
    """
    ViewSet for retrieving general platform statistics.

    - Does not require authentication (`permission_classes = []`).
    - Provides aggregated data such as:
        - Total number of reviews.
        - Average rating across all reviews.
        - Total number of offers.
        - Total number of business profiles.
    """
    permission_classes = []
    
    def list(self, request):
        """
        Returns platform-wide statistics.

        - `review_count`: Total number of reviews.
        - `average_rating`: Average rating across all reviews (rounded to 2 decimal places).
        - `offer_count`: Total number of offers available.
        - `business_profile_count`: Total number of registered business profiles.
        """
        review_count = Reviews.objects.count()
        average_rating = Reviews.objects.aggregate(avg_rating=Avg("rating"))["avg_rating"] or 0
        offer_count = Offers.objects.count()
        business_profile_count = Profil.objects.filter(profile_type="business").count()

        return Response({
            "review_count": review_count,
            "average_rating": round(average_rating, 2),  # Durchschnittliche Bewertung auf 2 Dezimalstellen runden
            "offer_count": offer_count,
            "business_profile_count": business_profile_count
        })

       
class BusinessOrderCountViewSet(viewsets.ViewSet):
    """
    ViewSet for retrieving the count of ongoing orders for a specific business user.

    - Accepts a `pk` (user ID) as a parameter.
    - Returns the number of orders with `status="in_progress"` for the given business user.
    - Returns an error response if the business user is not found.
    """
    def list(self, request, pk=None):
        """
        Returns the count of ongoing orders for the specified business user.

        - If the business user does not exist, returns a 404 error.
        - Counts orders where `status="in_progress"` and `business_user_id=pk`.
        """
        business_user = User.objects.filter(pk=pk).first()
        if not business_user:
            return Response({"error": "Business user not found."}, status=status.HTTP_404_NOT_FOUND)
        order_count = Orders.objects.filter(business_user_id=pk, status="in_progress").count()
        return Response({"order_count": order_count})
        
    
class BusinessCompletedOrderCountViewSet(viewsets.ViewSet):
    """
    ViewSet for retrieving the count of completed orders for a specific business user.

    - Accepts a `pk` (user ID) as a parameter.
    - Returns the number of orders with `status="completed"` for the given business user.
    - Returns an error response if the business user is not found.
    """
    def list(self, request, pk=None):
        """
        Returns the count of completed orders for the specified business user.

        - If the business user does not exist, returns a 404 error.
        - Counts orders where `status="completed"` and `business_user_id=pk`.
        """
        business_user = User.objects.filter(pk=pk).first()
        if not business_user:
            return Response({"error": "Business user not found."}, status=status.HTTP_404_NOT_FOUND)
        completed_count = Orders.objects.filter(business_user_id=pk, status="completed").count()
        return Response({"completed_order_count": completed_count})