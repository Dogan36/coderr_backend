from email.mime import image
from django.db.models import Min, Max, DecimalField, IntegerField
from django.db.models.functions import Coalesce
from rest_framework import viewsets, generics, status, filters, mixins
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from ..models import Offers, OfferDetails, Orders, Profil, Reviews
from .serializers import OffersSerializer, OfferDetailsSerializer, OrdersSerializer, ProfilDetailSerializer, ProfilUpdateSerializer, ReviewsSerializer, UserSerializer, ProfilTypeSerializer, OrderCreateSerializer
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
from coderr_app.api.permissions import IsBusinessForCreateOnly, IsStaffForDeleteOnly, IsCustomerForCreateOnly

class LargeResultsSetPagination(PageNumberPagination):
    """
    Custom pagination class for handling large datasets.
    
    - `page_size`: Default number of items per page (6).
    - `page_size_query_param`: Allows clients to request a different page size.
    - `max_page_size`: Maximum limit a client can request (100).
    """
    page_size = 6
    page_size_query_param = 'page_size'
    max_page_size = 6

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
    ViewSet for managing offers.

    - Requires authentication and restricts offer creation to business users only.
    - Supports search and filtering based on `title`, `description`, and `user`.
    - Provides pagination with `LargeResultsSetPagination`.
    - Allows file uploads using `MultiPartParser`.

    Permissions:
    - Only authenticated users can access.
    - Only business users can create offers.
    """
    queryset = Offers.objects.all()
    permission_classes = [IsAuthenticated, IsBusinessForCreateOnly]
    serializer_class = OffersSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['title', 'description']
    filterset_fields = ['user']
    pagination_class = LargeResultsSetPagination
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    
    def perform_create(self, serializer):
        """
        Handles the creation of a new offer.
        
        - Automatically assigns the authenticated user as the offer creator.
        - Handles optional image upload.
        """
        serializer.save(user=self.request.user)
        image = self.request.FILES.get('image', None)
        if image is not None:
            instance = serializer.instance
            instance.image = image
            instance.save()
            
    def perform_update(self, serializer):
        """
        Handles updating an existing offer.
        
        - Supports image updates if a new file is provided.
        """
        image = self.request.FILES.get('image', None)
        if image is not None:
            instance = serializer.instance
            instance.image = image
            instance.save()
        else:
            serializer.save()
            
    def get_queryset(self):
        """
        Custom queryset filtering:
        
        - `creator_id`: Filters offers by user ID.
        - `min_price`: Filters offers with a minimum price.
        - `max_delivery_time`: Filters offers with a maximum delivery time.
        - `ordering`: Supports sorting by `created_at` or `updated_at`.
        """
        queryset = Offers.objects.all()
        creator_id = self.request.query_params.get("creator_id")
        min_price = self.request.query_params.get("min_price")
        max_delivery_time = self.request.query_params.get("max_delivery_time")
        ordering = self.request.query_params.get("ordering", "created_at")
        if ordering:
            if ordering == "updated_at" or ordering == "-updated_at":
                queryset = queryset.order_by(ordering).reverse()
            else:
                queryset = queryset.order_by(ordering)
        if creator_id:
            queryset = queryset.filter(user_id=creator_id)  # `user_id`, weil `user` ein ForeignKey ist
        if min_price:
             queryset = queryset.filter(min_price__gte=float(min_price))
        if max_delivery_time:
            queryset = queryset.filter(min_delivery_time__lte=int(max_delivery_time))
        return queryset
    
    def list(self, request, *args, **kwargs):
        """
        Custom list view to support pagination.

        - Uses Django's built-in pagination.
        - Applies search and filter criteria before returning results.
        """
        queryset = self.filter_queryset(self.get_queryset())  # Suchfilter anwenden
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    
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
    ViewSet for managing orders.

    - Only authenticated users can access.
    - Only customers can create orders (`IsCustomerForCreateOnly`).
    - Only staff members can delete orders (`IsStaffForDeleteOnly`).
    - Users can only see orders where they are either the customer or the business user.
    """
    permission_classes = [IsAuthenticated, IsStaffForDeleteOnly, IsCustomerForCreateOnly]
    queryset = Orders.objects.all()
    
    def get_serializer_class(self):
        """
        Uses `OrderCreateSerializer` for creating orders.
        Otherwise, `OrdersSerializer` is used for retrieving, updating, and listing orders.
        """
        if self.action == 'create':
            return OrderCreateSerializer
        return OrdersSerializer

    def create(self, request, *args, **kwargs):
        """
        Handles order creation.

        - Uses `OrderCreateSerializer` to validate input.
        - Saves the new order.
        - Returns the created order in the response using `OrdersSerializer`.
        """
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        # Serialisiere das erstellte Order-Objekt für die Antwort
        output_serializer = OrdersSerializer(order, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)
    
    def get_queryset(self):
        """
        Custom queryset filtering:
        
        - Users can only view orders where they are either the customer or the business user.
        - Staff users can access all orders.
        """
        queryset = Orders.objects.all()
        print("🔍 Query-Parameter:", queryset.values())
        id = self.request.user.id
        print("🔍 User-ID:", id)
        queryset = queryset.filter(customer_user_id=id) | queryset.filter(business_user_id=id)
        print("🔍 Query-Set:", queryset)
        return queryset
    
    
class ProfileDetailView(generics.RetrieveUpdateAPIView):
    """
    API view for retrieving and updating user profiles.

    - Allows retrieving (`GET`) a profile based on the user's ID.
    - Allows partial updates (`PATCH`) and full updates (`PUT`).
    - Handles profile image updates.
    """
    
    queryset = Profil.objects.all()

    def get_serializer_class(self):
        """
        Verwendet je nach Anfrage `ProfilDetailSerializer` oder `ProfilUpdateSerializer`.
        """
        if self.request.method == "PATCH":
            return ProfilUpdateSerializer
        return ProfilDetailSerializer

    def get_object(self):
        return get_object_or_404(Profil, user__id=self.kwargs["pk"])

    def patch(self, request, *args, **kwargs):
        """
        Aktualisiert Profil- und User-Daten über `FormData`, inklusive Bild-Upload.
        """
        instance = self.get_object()

        # Konvertiere `QueryDict` in normales Dict
        data = request.POST.dict()
        files = request.FILES  # Enthält hochgeladene Dateien

        print("📩 FormData Request-Daten:", data)
        print("🖼️ Hochgeladene Datei:", files.get("file"))

        # User-Felder in `user` verschieben
        user_fields = ["username", "first_name", "last_name", "email"]
        user_data = {key: data.pop(key) for key in user_fields if key in data}

        # Korrekte JSON-Struktur erstellen
        if user_data:
            data["user"] = user_data

        # Serializer mit `data` aufrufen (ohne `files`)
        serializer = self.get_serializer(instance, data=data, partial=True)

        if serializer.is_valid():
            self.perform_update(serializer)  # Bild wird in `perform_update()` gespeichert
            return Response(serializer.data, status=status.HTTP_200_OK)

        print("❌ Serializer-Fehler:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def perform_update(self, serializer):
        """
        Speichert das Profil-Update, einschließlich des Bild-Uploads.
        """
        image = self.request.FILES.get("file")  # Datei aus `request.FILES` abrufen

        if image:
            serializer.instance.file = image  # Datei im `file`-Feld speichern
            serializer.instance.save()

        serializer.save()

class BusinessProfilesListView(generics.ListAPIView):
    """
    API view for listing all business profiles.

    - Uses `ProfilTypeSerializer` to serialize the data.
    - Returns only profiles where `type="business"`.
    """
    serializer_class = ProfilTypeSerializer

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
    def get_queryset(self):
        """
        Filters the queryset to return only customer profiles.
        """
        return Profil.objects.filter(profile_type="customer")


  
class ReviewsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing reviews.

    - Customers can create reviews (restricted via `IsCustomerForCreateOnly`).
    - Users can only see reviews they wrote (customers) or received (business users).
    - Prevents duplicate reviews for the same business.
    - Only reviewers or admins can update or delete reviews.
    """
    queryset = Reviews.objects.all()
    serializer_class = ReviewsSerializer
    permission_classes = [IsAuthenticated, IsCustomerForCreateOnly]
    def get_queryset(self):
        """
        Returns a filtered queryset based on the user's profile type.

        - Customers see only the reviews they created.
        - Business users see only reviews about their business.
        - If the user has no profile, they receive an empty queryset.
        """
        user = self.request.user
        try:
            profil = Profil.objects.get(user=user)
        except Profil.DoesNotExist:
            return Reviews.objects.none()
        queryset = Reviews.objects.none()
        if profil.profile_type == "customer":
            return Reviews.objects.filter(reviewer=user)
        elif profil.profile_type == "business":
            return Reviews.objects.filter(business_user=user)
        ordering = self.request.query_params.get("ordering")
        if ordering:
            if ordering == "created_at" or ordering == "-created_at":
                queryset = queryset.order_by(ordering).reverse()
            else:
                queryset = queryset.order_by(ordering)
        return queryset
    
    def perform_create(self, serializer):
        """
        Ensures that:
        - Only customers can create reviews.
        - A business can be reviewed only once by the same user.
        """
        request_user = self.request.user
        try:
            profil = Profil.objects.get(user=request_user)
        except Profil.DoesNotExist:
            return Response("Du benötigst ein Profil, um eine Bewertung abzugeben.")
        business_user = serializer.validated_data["business_user"]
        if Reviews.objects.filter(business_user=business_user, reviewer=request_user).exists():
            return Response("Du kannst ein Business nur einmal bewerten.")
        serializer.save(reviewer=request_user)
    
    def perform_update(self, serializer):
        """
        Ensures that only the original reviewer can update their review.
        """
        instance = self.get_object()
        if self.request.user != instance.reviewer:
            return Response("Nur der Reviewer darf die Bewertung ändern.")
        serializer.save()
        
    def perform_destroy(self, instance):
        """
        Ensures that only the reviewer or an admin can delete a review.
        """
        if self.request.user != instance.reviewer and not self.request.user.is_staff:
            return Response("Nur der Reviewer oder ein Admin darf die Bewertung löschen.")
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