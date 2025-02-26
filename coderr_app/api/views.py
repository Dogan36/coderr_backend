from django.db.models import Min, Max, DecimalField, IntegerField
from django.db.models.functions import Coalesce
from rest_framework import viewsets, generics, status, filters
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from ..models import Offers, OfferDetails, Orders, Profil, Reviews
from .serializers import OffersSerializer, OfferDetailsSerializer, OrdersSerializer, ProfilSerializer, ReviewsSerializer, UserSerializer, ProfilTypeSerializer
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from django.db.models import Avg 


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)  # Setzt den eingeloggten User automatisch

class OffersViewSet(viewsets.ModelViewSet):
    queryset = Offers.objects.all()
    serializer_class = OffersSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['title', 'description']
    filterset_fields = ['user']
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)  # Setzt den eingeloggten User automatisch

    def get_queryset(self):
        """Falls `creator_id` in der URL ist, filtere die Angebote nach dem Ersteller."""
        queryset = Offers.objects.annotate(
        min_price=Min("offer_details__price"))
        queryset = Offers.objects.annotate(
        max_delivery_time=Min("offer_details__delivery_time_in_days"))
        creator_id = self.request.query_params.get("creator_id")
        min_price = self.request.query_params.get("min_price")
        max_delivery_time = self.request.query_params.get("max_delivery_time")
        if creator_id:
            queryset = queryset.filter(user_id=creator_id)  # `user_id`, weil `user` ein ForeignKey ist
        if min_price:
             queryset = queryset.filter(min_price__gte=float(min_price))
        if max_delivery_time:
            queryset = queryset.filter(max_delivery_time__lte=int(max_delivery_time))
        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())  # Suchfilter anwenden
        serializer = self.get_serializer(queryset, many=True)

        return Response({
            "count": len(serializer.data),  # Gesamtanzahl der Angebote
            "results": serializer.data  # Die eigentlichen Angebote
        })
class OfferDetailsViewSet(viewsets.ModelViewSet):
    queryset = OfferDetails.objects.all()
    serializer_class = OfferDetailsSerializer
    
class OrdersViewSet(viewsets.ModelViewSet):
    queryset = Orders.objects.all()
    serializer_class = OrdersSerializer
    
    
    
# 🔹 1. GET /profile/<int:pk>/  (Detailansicht & Update)
class ProfileDetailView(generics.RetrieveUpdateAPIView):
    queryset = Profil.objects.all()
    serializer_class = ProfilSerializer

    def get(self, request, pk, *args, **kwargs):
        profil = get_object_or_404(Profil, user__id=pk)
        serializer = self.get_serializer(profil)
        return Response(serializer.data, status=status.HTTP_200_OK)

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
    print(Profil.objects.filter(type="customer"))
    def get_queryset(self):
        return Profil.objects.filter(type="customer")
    
class ReviewsViewSet(viewsets.ModelViewSet):
    queryset = Reviews.objects.all()
    serializer_class = ReviewsSerializer
    
class LoginAPIView(APIView):
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

        if not username or not password or not email:
            return Response({"error": "Username, email, and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        if password != repeated_password:
            return Response({"password": "Das Passwort ist nicht gleich mit dem wiederholten Passwort"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already taken"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({"error": "Email already in use"}, status=status.HTTP_400_BAD_REQUEST)

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
        """Gibt die Anzahl aller Bestellungen für ein Business zurück."""
        order_count = Orders.objects.filter(business_user_id=pk).count()
        print(order_count)
        return Response({"order_count": order_count})
        
    
class BusinessCompletedOrderCountViewSet(viewsets.ViewSet):
    def list(self, request, pk=None):
        """Gibt die Anzahl der abgeschlossenen Bestellungen zurück."""
        completed_count = Orders.objects.filter(business_user_id=pk, status="completed").count()
        print(completed_count)
        return Response({"completed_order_count": completed_count})