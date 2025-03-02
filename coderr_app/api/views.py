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
from coderr_app.api.permissions import IsStaffForDeleteOnly, IsCustomerForCreateOnly

class LargeResultsSetPagination(PageNumberPagination):
    page_size = 6
    page_size_query_param = 'page_size'
    max_page_size = 100

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)  # Setzt den eingeloggten User automatisch

class OffersViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Offers.objects.all()
    serializer_class = OffersSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['title', 'description']
    filterset_fields = ['user']
    pagination_class = LargeResultsSetPagination
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        
    def perform_update(self, serializer):
        image = self.request.FILES.get('image', None)
        if image is not None:
            instance = serializer.instance
            instance.image = image
            instance.save()
        else:
            serializer.save()
    def get_queryset(self):
        queryset = Offers.objects.all()
        creator_id = self.request.query_params.get("creator_id")
        min_price = self.request.query_params.get("min_price")
        max_delivery_time = self.request.query_params.get("max_delivery_time")
        ordering = self.request.query_params.get("ordering")
        
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
        queryset = self.filter_queryset(self.get_queryset())  # Suchfilter anwenden
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
class OfferDetailsViewSet(viewsets.ModelViewSet):
    queryset = OfferDetails.objects.all()
    serializer_class = OfferDetailsSerializer


class OrdersViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsStaffForDeleteOnly, IsCustomerForCreateOnly]
    queryset = Orders.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrdersSerializer

    def create(self, request, *args, **kwargs):
        # Verwende den OrderCreateSerializer für den Input
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        # Serialisiere das erstellte Order-Objekt für die Antwort
        output_serializer = OrdersSerializer(order, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)
    
    def get_queryset(self):
        """Falls `customer_id` in der URL ist, filtere die Bestellungen nach dem Kunden."""
        queryset = Orders.objects.all()
        id = self.request.user.id

        queryset = queryset.filter(customer_user=id) | queryset.filter(business_user=id)
        return queryset
    
    
    
# 🔹 1. GET /profile/<int:pk>/  (Detailansicht & Update)
class ProfileDetailView(generics.RetrieveUpdateAPIView):
    queryset = Profil.objects.all()
    serializer_class = ProfilSerializer

    def get(self, request, pk, *args, **kwargs):
        profil = get_object_or_404(Profil, user__id=pk)
        serializer = self.get_serializer(profil)
        return Response(serializer.data, status=status.HTTP_200_OK)
    def perform_update(self, serializer):
        image = self.request.FILES.get('image', None)
        if image is not None:
            instance = serializer.instance
            instance.file = image  # Direkt das Bild setzen
            instance.save()
        else:
            serializer.save()
            
    def patch(self, request, pk, *args, **kwargs):
        profil = get_object_or_404(Profil, user__id=pk)
        serializer = self.get_serializer(profil, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 🔹 2. GET /profiles/business/  (Liste aller Business-Profile)
class BusinessProfilesListView(generics.ListAPIView):
    serializer_class = ProfilTypeSerializer

    def get_queryset(self):
        return Profil.objects.filter(type="business")

# 🔹 3. GET /profiles/customer/  (Liste aller Kunden-Profile)
class CustomerProfilesListView(generics.ListAPIView):
    serializer_class = ProfilTypeSerializer
    def get_queryset(self):
        return Profil.objects.filter(type="customer")
    
class ReviewsViewSet(viewsets.ModelViewSet):
    queryset = Reviews.objects.all()
    serializer_class = ReviewsSerializer
    permission_classes = [IsAuthenticated, IsCustomerForCreateOnly]
    
    def perform_create(self, serializer):
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
        instance = self.get_object()
        if self.request.user != instance.reviewer:
            return Response("Nur der Reviewer darf die Bewertung ändern.")
        serializer.save()
        
    def perform_destroy(self, instance):
        if self.request.user != instance.reviewer and not self.request.user.is_staff:
            return Response("Nur der Reviewer oder ein Admin darf die Bewertung löschen.")
        instance.delete()
        
class LoginAPIView(APIView):
    permission_classes = []
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)
        if user is None:
            return Response({"detail": "Falsche Anmeldedaten"}, status=status.HTTP_400_BAD_REQUEST)

        token, created = Token.objects.get_or_create(user=user)
        return Response({"user_id": user.id, "username": user.username, "email": user.email, "token": token.key})

class RegisterAPIView(APIView):
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        repeated_password = request.data.get("repeated_password")
        email = request.data.get("email")

        if not username:
            return Response({"error": "Username ist erforderlich."}, status=status.HTTP_400_BAD_REQUEST)
        if not email:
            return Response({"error": "Email ist erforderlich."}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({"error": "Passwort ist erforderlich."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_email(email)
        except ValidationError:
            return Response({"error": "Ungültige E-Mail-Adresse."}, status=status.HTTP_400_BAD_REQUEST)
        
        if password != repeated_password:
            return Response({"password": "Das Passwort ist nicht gleich mit dem wiederholten Passwort"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({"error": "Dieser Benutzername ist bereits vergeben."}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({"error": "Diese E-Mail-Adresse wird bereits verwendet."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, password=password, email=email)
        Profil.objects.create(user=user)  # Profil für den User erstellen
        token, _ = Token.objects.get_or_create(user=user)  # Token erstellen

        return Response({
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "token": token.key
        }, status=status.HTTP_201_CREATED)
        
class BaseInfoViewSet(viewsets.ViewSet):
    permission_classes = []
    def list(self, request):
        review_count = Reviews.objects.count()
        average_rating = Reviews.objects.aggregate(avg_rating=Avg("rating"))["avg_rating"] or 0
        offer_count = Offers.objects.count()
        business_profile_count = Profil.objects.filter(type="business").count()

        return Response({
            "review_count": review_count,
            "average_rating": round(average_rating, 2),  # Durchschnittliche Bewertung auf 2 Dezimalstellen runden
            "offer_count": offer_count,
            "business_profile_count": business_profile_count
        })
        
class BusinessOrderCountViewSet(viewsets.ViewSet):
    def list(self, request, pk=None):
        business_user = User.objects.filter(pk=pk).first()
        if not business_user:
            return Response({"error": "Business user not found."}, status=status.HTTP_404_NOT_FOUND)
        order_count = Orders.objects.filter(business_user_id=pk, status="in_progress").count()
        return Response({"order_count": order_count})
        
    
class BusinessCompletedOrderCountViewSet(viewsets.ViewSet):
    def list(self, request, pk=None):
        business_user = User.objects.filter(pk=pk).first()
        if not business_user:
            return Response({"error": "Business user not found."}, status=status.HTTP_404_NOT_FOUND)
        completed_count = Orders.objects.filter(business_user_id=pk, status="completed").count()
        return Response({"completed_order_count": completed_count})