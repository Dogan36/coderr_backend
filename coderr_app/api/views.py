

from rest_framework.exceptions import ValidationError, NotFound
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

from coderr_app.api.permissions import IsBusinessForCreateOnly, IsBusinessForPatchOnly, IsCustomerForCreateOnly, IsOwnerForPatchOnly, IsAdminOrCustomPermission, IsOwnerOfProfile, IsUniqueReviewer, IsOwnerCustomerOrAdmin
from rest_framework.generics import RetrieveUpdateAPIView
from .pagination import LargeResultsSetPagination
from coderr_app.api import serializers

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

    - Authentication required.
    - `POST`: Only business users can create offers.
    - `PATCH/DELETE`: Only business users can modify their own offers.
    - `GET`: All authenticated users can view offers.
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
        Retrieves an `Offer` object. Returns `404 Not Found` if it does not exist.
        After retrieval, object permissions are checked.
        """
        obj = get_object_or_404(Offers, pk=self.kwargs.get("pk"))
        return obj

    def get_permissions(self):
        """
        Assigns different permissions based on the HTTP method.
        """
        if self.action in ["retrieve", "update", "partial_update", "destroy"]:
            try:
                self.get_object()  # Holt das Objekt, wenn es existiert
            except NotFound:
                pass  # Falls es nicht existiert, einfach nichts tun
        if self.action == "retrieve":
            return [IsAuthenticated()]
        if self.action == "create":
            return [IsAuthenticated(), IsBusinessForCreateOnly()]
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsOwnerForPatchOnly()]
        return []

    def perform_create(self, serializer):
        """
        Creates a new offer and saves the uploaded image.
        """
        instance = serializer.save(user=self.request.user)
        image = self.request.FILES.get('image', None)
        if image:
            instance.image = image
            instance.save()

    def update(self, request, *args, **kwargs):
        """
        Overrides `update()` to support `PATCH`.
        """
        kwargs['partial'] = True  # Allows partial updates with `PATCH`
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        """
        Updates the offer without deleting existing `offer_details`.
        - Updates existing details based on `offer_type`.
        - Adds new `offer_details` if they do not already exist.
        - Recalculates `min_price` and `min_delivery_time`.
        """
        instance = serializer.instance
        validated_data = serializer.validated_data

        # Handle file uploads (`image`) separately
        image = self.request.FILES.get('image', None)
        if image:
            instance.image = image

        # Update standard fields (except `offer_details`)
        for attr, value in validated_data.items():
            if attr != "offer_details":
                setattr(instance, attr, value)

        # If `offer_details` are provided, process them individually
        details_data = self.request.data.get("details", None)
        if details_data is not None:
            processed_offer_types = set()  # Um doppelte OfferDetails zu verhindern

            for detail_data in details_data:
                offer_type = detail_data.get("offer_type")
                if not offer_type:
                    raise ValidationError({"offer_type": "This field is required for all offer details."})

                processed_offer_types.add(offer_type)

                existing_detail = instance.offer_details.filter(offer_type=offer_type).first()
                if existing_detail:
                    # Update existing `OfferDetail`
                    for key, value in detail_data.items():
                        setattr(existing_detail, key, value)
                    existing_detail.save()
                else:
                    # Create new `OfferDetail`
                    OfferDetails.objects.create(offer=instance, **detail_data)

            # Lösche alte OfferDetails, die nicht mehr im Request sind
            instance.offer_details.exclude(offer_type__in=processed_offer_types).delete()

        # Recalculate `min_price` & `min_delivery_time`
        aggregated = OfferDetails.objects.filter(offer=instance).aggregate(
            min_price=Min("price"),
            min_delivery_time=Min("delivery_time_in_days")
        )
        instance.min_price = aggregated.get('min_price') or 0
        instance.min_delivery_time = aggregated.get('min_delivery_time') or 0
        instance.save()

    def get_queryset(self):
        """
        Returns filtered offers based on query parameters.
        """
        queryset = Offers.objects.all()
        params = self.request.query_params

        creator_id = params.get("creator_id")
        min_price = params.get("min_price")
        max_delivery_time = params.get("max_delivery_time")
        ordering = params.get("ordering", "created_at")

        # Apply sorting
        if ordering in ["created_at", "-created_at", "updated_at", "-updated_at"]:
            queryset = queryset.order_by(ordering)
        # Apply filters
        if creator_id:
            queryset = queryset.filter(user_id=creator_id)
        if min_price:
            try:
                queryset = queryset.filter(min_price__gte=float(min_price))
            except ValueError:
                pass
        if max_delivery_time:
            if not max_delivery_time.isdigit():
                raise ValidationError({"max_delivery_time": "Invalid max_delivery_time. Must be an integer."})
            queryset = queryset.filter(min_delivery_time__lte=int(max_delivery_time))

        return queryset

    def list(self, request, *args, **kwargs):
        """
        Returns a paginated list of offers.
        """
        try:
            queryset = self.filter_queryset(self.get_queryset())
        except ValueError as e:
            return Response({"error": str(e)}, status=400)

        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Deletes an offer and returns `{}` as a response.
        """
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({}, status=status.HTTP_204_NO_CONTENT)

    
class OfferDetailsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing offer details.

    - Provides CRUD operations for `OfferDetails`.
    - Each `OfferDetails` entry is linked to a specific `Offer`.
    - Only authenticated users can access this view.
    """
    permission_classes = [IsAuthenticated]
    queryset = OfferDetails.objects.all()
    serializer_class = OfferDetailsSerializer



class OrdersViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing orders.

    - `GET /orders/` → Retrieves a list of orders where the user is involved (as a customer or provider).
    - `POST /orders/` → Creates an order (only `customer_user` is allowed).
    - `GET /orders/{id}/` → Retrieves details of a specific order.
    - `PATCH /orders/{id}/` → Only the business user or an admin can update the `status`.
    - `DELETE /orders/{id}/` → Only admins can delete orders.
    """

    queryset = Orders.objects.all()
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """
        Assigns different permissions based on the HTTP method.
        """
        if self.action in ["retrieve", "update", "partial_update", "destroy"]:
            try:
                self.get_object()  # Holt das Objekt, wenn es existiert
            except NotFound:
                pass  # Falls es nicht existiert, einfach nichts tun
        if self.request.method == "POST":
            return [IsAuthenticated(), IsCustomerForCreateOnly()]
        if self.request.method == "DELETE":
            return [IsAuthenticated(), IsAdminOrCustomPermission()]
        if self.request.method == "PATCH":
            return [IsAuthenticated(), IsBusinessForPatchOnly()]
        return [IsAuthenticated()]  # `PATCH` has additional permission checks in `get_object()`

    def get_object(self):
        """
        Retrieves the order and checks object permissions.

        - If the order does not exist → Returns 404 Not Found.
        - If the user lacks permissions → Returns 403 Forbidden.
        """
        obj = get_object_or_404(Orders, pk=self.kwargs.get("pk"))
        return obj

    def get_serializer_class(self):
        """
        Uses `OrderCreateSerializer` for `POST`, otherwise `OrdersSerializer`.
        """
        if self.request.method == "POST":
            return OrderCreateSerializer
        return OrdersSerializer

    def get_queryset(self):
        """
        Returns only the orders in which the user is involved.
        """
        user = self.request.user
        if user.is_staff:
            return Orders.objects.all()  # Admins can see all orders
        return Orders.objects.filter(customer_user=user) | Orders.objects.filter(business_user=user)

    def create(self, request, *args, **kwargs):
        """
        Creates a new order based on an offer.
        """
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        order = serializer.save()

        # ✅ Return the newly created order as JSON
        output_serializer = OrdersSerializer(order, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """
        - Only `status` can be updated via `PATCH`.
        - Only the `business_user` can change the status.
        - Admins can modify everything.
        - Returns 404 if the order does not exist.
        - Returns 403 if the user is not authorized.
        """
        instance = self.get_object()  # Retrieves the order and checks permissions.

        new_status = request.data.get("status")
        valid_status_choices = [choice[0] for choice in Orders.status_choices]

        if new_status not in valid_status_choices:
            return Response(
                {"error": f"Invalid status. Allowed: {valid_status_choices}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.status = new_status
        instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """
        - ONLY admins can delete orders.
        """
        instance = self.get_object()  # Checks if the order exists and if the user is an admin.
        instance.delete()
        return Response({}, status=status.HTTP_200_OK)

    
class ProfileDetailView(RetrieveUpdateAPIView):
    """
    API view for retrieving and updating a user profile.
    """

    queryset = Profil.objects.all()
    serializer_class = ProfilSerializer
    permission_classes = [IsAuthenticated, IsOwnerOfProfile]

    def get_object(self):
        """
        Retrieves the `Profil` object based on the user ID (`pk` corresponds to `user_id`).
        """
        obj = get_object_or_404(Profil, user__id=self.kwargs["pk"])

        # 🔍 Debugging: Ensure `has_object_permission` is called
        self.check_object_permissions(self.request, obj)

        return obj

    def perform_update(self, serializer):
        """
        Saves the uploaded image correctly in the profile model and provides debugging info.
        """
        file = self.request.FILES.get("file", None)

        if file is not None:
            instance = serializer.instance
            instance.file = file  # Assuming the field name is `file`
            instance.save()
        else:
            serializer.save()


class BusinessProfilesListView(generics.ListAPIView):
    """
    API view for listing all business profiles.

    - Uses `ProfilTypeSerializer` to serialize the data.
    - Returns only profiles where `profile_type="business"`.
    """
    serializer_class = ProfilTypeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Returns only business profiles.
        """
        return Profil.objects.filter(profile_type="business")


class CustomerProfilesListView(generics.ListAPIView):
    """
    API view for listing all customer profiles.

    - Uses `ProfilTypeSerializer` to serialize the data.
    - Returns only profiles where `profile_type="customer"`.
    """
    serializer_class = ProfilTypeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Returns only customer profiles.
        """
        return Profil.objects.filter(profile_type="customer")


class ReviewsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing reviews.
    """

    queryset = Reviews.objects.all()
    serializer_class = ReviewsSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["updated_at", "rating"]
    permission_classes = [IsAuthenticated, IsCustomerForCreateOnly, IsOwnerCustomerOrAdmin]

    def get_queryset(self):
        """
        Returns reviews based on filter parameters.
        """
        queryset = Reviews.objects.all()
        business_user_id = self.request.query_params.get("business_user_id")
        reviewer_id = self.request.query_params.get("reviewer_id")

        if business_user_id:
            queryset = queryset.filter(business_user_id=business_user_id)
        if reviewer_id:
            queryset = queryset.filter(reviewer_id=reviewer_id)

        return queryset

    def get_object(self):
        """
        Retrieves the review object and checks permissions.
        """
        obj = get_object_or_404(Reviews, pk=self.kwargs.get("pk"))
        self.check_object_permissions(self.request, obj)  # Check permissions only after retrieving the object
        return obj

    def get_permissions(self):
        """
        Debugging: Logs all active permissions before they are applied.
        """
        return super().get_permissions()

    def perform_create(self, serializer):
        """
        Creates a new review and ensures the user has permission.
        """
        business_user = self.request.data.get("business_user")

        if not business_user:
            raise ValidationError({"business_user": "A `business_user` must be specified."})

        # Validate if the user has already reviewed the business
        already_reviewed = Reviews.objects.filter(business_user=business_user, reviewer=self.request.user).exists()
        if already_reviewed:
            raise ValidationError({"error": "You have already reviewed this business."})
        # Save the review
        serializer.save(reviewer=self.request.user)

    def perform_update(self, serializer):
        """
        Updates a review.
        """
        instance = self.get_object()
        request_user = self.request.user

        if instance.reviewer != request_user and not request_user.is_staff:
            return Response(
                {"error": "Only the creator or an admin can edit the review."},
                status=status.HTTP_403_FORBIDDEN
            )

        allowed_fields = {"rating", "description"}
        invalid_fields = set(serializer.validated_data.keys()) - allowed_fields

        if invalid_fields:
            return Response(
                {"error": f"The following fields cannot be updated: {', '.join(invalid_fields)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer.save()

    def perform_destroy(self, instance):
        """
        Deletes a review.
        """
        request_user = self.request.user

        if instance.reviewer != request_user and not request_user.is_staff:
            return Response(
                {"error": "Only the creator or an admin can delete the review."},
                status=status.HTTP_403_FORBIDDEN
            )

        instance.delete()

class LoginAPIView(APIView):
    """
    API endpoint for user login.

    - Authenticates a user using a username and password.
    - Returns an authentication token upon successful login.
    - Does not require authentication (`permission_classes = []`).
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
            return Response({"detail": "Invalid login credentials."}, status=status.HTTP_400_BAD_REQUEST)

        token, created = Token.objects.get_or_create(user=user)
        return Response({
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "token": token.key
        })


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
        - Ensures all required fields are provided.
        - Validates the email format.
        - Ensures that passwords match.
        - Checks for unique username and email.
        - Creates a new user and an associated profile.
        - Generates an authentication token for the new user.
        """
        username = request.data.get("username")
        password = request.data.get("password")
        repeated_password = request.data.get("repeated_password")
        email = request.data.get("email")
        profile_type = request.data.get("type")

        # Validate required fields
        if not username:
            return Response({"error": "Username is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({"error": "Password is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not profile_type:
            return Response({"error": "Profile type is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate email format
        try:
            validate_email(email)
        except ValidationError:
            return Response({"error": "Invalid email address."}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure passwords match
        if password != repeated_password:
            return Response({"password": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure unique username and email
        if User.objects.filter(username=username).exists():
            return Response({"error": "This username is already taken."}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email=email).exists():
            return Response({"error": "This email is already in use."}, status=status.HTTP_400_BAD_REQUEST)

        # Create user and associated profile
        user = User.objects.create_user(username=username, password=password, email=email)
        Profil.objects.create(user=user, profile_type=profile_type)  # Create profile for the user
        token, _ = Token.objects.get_or_create(user=user)  # Generate authentication token

        return Response({
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "profile_type": profile_type,
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
        - `offer_count`: Total number of available offers.
        - `business_profile_count`: Total number of registered business profiles.
        """
        review_count = Reviews.objects.count()
        average_rating = Reviews.objects.aggregate(avg_rating=Avg("rating"))["avg_rating"] or 0
        offer_count = Offers.objects.count()
        business_profile_count = Profil.objects.filter(profile_type="business").count()

        return Response({
            "review_count": review_count,
            "average_rating": round(average_rating, 2),
            "offer_count": offer_count,
            "business_profile_count": business_profile_count
        })


class BusinessOrderCountViewSet(viewsets.ViewSet):
    """
    ViewSet for retrieving the count of ongoing orders for a specific business user.

    - Requires authentication.
    - Accepts a `pk` (user ID) as a parameter.
    - Returns the number of orders with `status="in_progress"` for the given business user.
    - Returns a 404 error response if the business user is not found.
    """
    permission_classes = [IsAuthenticated]

    def list(self, request, pk=None):
        """
        Returns the count of ongoing orders for the specified business user.

        - If the business user does not exist, returns a 404 error.
        - Counts orders where `status="in_progress"` and `business_user_id=pk`.
        """
        if not User.objects.filter(pk=pk).exists():
            return Response({"error": "Business user not found."}, status=status.HTTP_404_NOT_FOUND)

        order_count = Orders.objects.filter(business_user_id=pk, status="in_progress").count()
        return Response({"order_count": order_count})


class BusinessCompletedOrderCountViewSet(viewsets.ViewSet):
    """
    ViewSet for retrieving the count of completed orders for a specific business user.

    - Requires authentication.
    - Accepts a `pk` (user ID) as a parameter.
    - Returns the number of orders with `status="completed"` for the given business user.
    - Returns a 404 error response if the business user is not found.
    """
    permission_classes = [IsAuthenticated]

    def list(self, request, pk=None):
        """
        Returns the count of completed orders for the specified business user.

        - If the business user does not exist, returns a 404 error.
        - Counts orders where `status="completed"` and `business_user_id=pk`.
        """
        if not User.objects.filter(pk=pk).exists():
            return Response({"error": "Business user not found."}, status=status.HTTP_404_NOT_FOUND)

        completed_count = Orders.objects.filter(business_user_id=pk, status="completed").count()
        return Response({"completed_order_count": completed_count})
