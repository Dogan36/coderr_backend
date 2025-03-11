from os import read
from rest_framework import serializers
from django.contrib.auth.models import User
from coderr_app.models import Offers, OfferDetails, Orders, Profil, Reviews
from django.db.models import Min

import os

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model.

    - Serializes basic user information.
    - Includes primary key (`pk`), username, first name, last name, and email.
    """
    class Meta:
        model = User
        fields = ['pk', 'username', 'first_name', 'last_name', 'email']


class OfferDetailsSerializer(serializers.ModelSerializer):
    """
    Serializer for the OfferDetails model.

    - Serializes details of an offer package.
    - `features` is stored as a list of strings.
    - The `offer` field is read-only, ensuring it is not modified directly via the serializer.
    """
    features = serializers.ListField(child=serializers.CharField())
    class Meta:
        model = OfferDetails
        fields = ['id', 'title', 'revisions', 'delivery_time_in_days', 'price', 'features', 'offer_type']
        extra_kwargs = {
            'offer': {'read_only': True}
        }
 
              
class OffersSerializer(serializers.ModelSerializer):
    """
    Serializer for the Offers model.
    """
    details = OfferDetailsSerializer(many=True, source='offer_details')
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    min_delivery_time = serializers.IntegerField(read_only=True)
    user_details = UserSerializer(source="user", read_only=True)
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Offers
        fields = '__all__'

    def validate(self, data):
        """
        Validates that exactly 3 offer details are provided, but only for POST requests.
        """
        request = self.context.get("request")  # Zugriff auf die HTTP-Methode

        details_data = data.get('offer_details', [])

        # **Check for POST only if length of details_data == 3**
        if request and request.method == "POST" and len(details_data) != 3:
            raise serializers.ValidationError({"offer_details": "Es müssen genau 3 Offer Details gesendet werden."})

        return data


    def create(self, validated_data):
        """
        Creates an offer along with its associated offer details.
        """
        details_data = validated_data.pop('offer_details', [])
        offer = Offers.objects.create(**validated_data)

        # Create OfferDetails instances
        for detail_data in details_data:
            OfferDetails.objects.create(offer=offer, **detail_data)

        # Aggregate values from related OfferDetails
        aggregated = OfferDetails.objects.filter(offer=offer).aggregate(
            min_price=Min("price"),
            min_delivery_time=Min("delivery_time_in_days")
        )

        # Update the Offer object with calculated values
        offer.min_price = aggregated.get('min_price') or 0
        offer.min_delivery_time = aggregated.get('min_delivery_time') or 0
        offer.save()
        return offer
    
    
class OrdersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Orders
        fields = '__all__'
        
    

class OrderCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating an order.

    - The client only provides `offer_detail_id`, which refers to an `OfferDetails` instance.
    - Retrieves the related offer details and business user.
    - Automatically assigns the authenticated user as the `customer_user`.
    - Creates an order with the attributes from the selected offer detail.
    """
    offer_detail_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Orders
        fields = ['offer_detail_id']

    def create(self, validated_data):
        """
        Creates an order based on the selected `OfferDetails`.

        - Retrieves the `OfferDetails` instance using the provided ID.
        - Ensures that the request contains a valid authenticated user.
        - Retrieves the customer's profile (`Profil`).
        - Assigns the business user, title, revisions, delivery time, price, and features from `OfferDetails`.
        - Creates a new `Orders` instance with `status="in_progress"`.
        """
        offer_detail_id = validated_data.pop('offer_detail_id')
        
        # 🔍 1. Get Offer Details
        try:
            offer_detail = OfferDetails.objects.get(id=offer_detail_id)
        except OfferDetails.DoesNotExist:
            raise serializers.ValidationError("OfferDetail not found")

        # 🔍 2. Check request object and user
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError({"error": "Invalid request context or unauthenticated user"})

        # 🔍 3. Get User
        request_user = self.context['request'].user
        
        # 📝 4. Prepare order data
        order_data = {
            "customer_user": request_user,
            "business_user": offer_detail.offer.user,
            "title": offer_detail.offer.title,
            "revisions": offer_detail.revisions,
            "delivery_time_in_days": offer_detail.delivery_time_in_days,
            "price": offer_detail.price,
            "features": offer_detail.features,
            "offer_type": offer_detail.offer_type,
            "status": "in_progress",
        }

        # ✅ 5. Create Order
        order = Orders.objects.create(**order_data)
        return order



class ProfilSerializer(serializers.ModelSerializer):
    """
    Serializer for profil with user data.
    """
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())  
    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(required=False)  
    last_name = serializers.CharField(required=False)
    email = serializers.CharField(required=False)
    
    type = serializers.CharField(source="profile_type")  

    class Meta:
        model = Profil
        fields = [
            "user", "username", "first_name", "last_name", "email",
            "file", "location", "tel", "description",
            "working_hours", "type", "created_at"
        ]
        read_only_fields = ["created_at"]

    def update(self, instance, validated_data):
        # Extract user data from validated data
        user_data = {}
        for field in ["first_name", "last_name", "email"]:
            if field in validated_data:
                user_data[field] = validated_data.pop(field)

        # Updata the user instance
        if user_data:
            user = instance.user
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save()
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        """
        Makes sure `first_name`, `last_name` und `email` are available in the API response.
        """
        rep = super().to_representation(instance)
        rep["first_name"] = instance.user.first_name
        rep["last_name"] = instance.user.last_name
        rep["email"] = instance.user.email
        return rep

        
class ProfilTypeSingleSerializer(serializers.ModelSerializer):
    """
    Serializer for the Profil model.

    - `user`: Stores only the user ID.
    - `username`, `first_name`, `last_name`, `email`: Retrieved from the associated User model.
    - Other fields (`file`, `location`, `tel`, etc.) belong to the profile.
    - `created_at` is read-only.
    """
    user = UserSerializer()

    class Meta:
        model = Profil
        fields = [
            "user", "file",
            "location", "tel", "description", "working_hours",
            "profile_type", "created_at"  # Geändert von `type` zu `profile_type`
        ]
        read_only_fields = ["created_at"]

    def to_representation(self, instance):
        """
        Changes API-Response, so `profile_type` will be returend as `type`.	
        """
        rep = super().to_representation(instance)
        rep["type"] = instance.profile_type  # API gibt weiterhin `type` zurück
        return rep


class ProfilTypeSerializer(serializers.ModelSerializer):
    """
    Serializer for the Profil model with nested user details.

    - `user`: Uses `UserSerializer` to include full user details instead of just the ID.
    - `file`, `location`, `tel`, `description`, `working_hours`, and `type`: Profile-specific fields.
    - `created_at` is read-only.
    """
    user = UserSerializer()

    class Meta:
        model = Profil
        fields = [
            "user", "file",
            "location", "tel", "description", "working_hours",
            "profile_type", "created_at"  # Geändert von `type` zu `profile_type`
        ]
        read_only_fields = ["created_at"]

    def to_representation(self, instance):
        """
        Changes API-Response, so `profile_type` will be returend as `type`.	
        """
        rep = super().to_representation(instance)
        rep["type"] = instance.profile_type  # API gibt weiterhin `type` zurück
        return rep


class ReviewsSerializer(serializers.ModelSerializer):
    """
    Serializer for the Reviews model.

    - `business_user`: References the reviewed business (User ID).
    - `reviewer`: Automatically assigned and read-only (set in the view).
    - Serializes all fields of the `Reviews` model.
    """
    business_user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=True)
    reviewer = serializers.PrimaryKeyRelatedField(read_only=True)
    rating = serializers.IntegerField(required=True, min_value=1, max_value=5)
    description=serializers.CharField(required=True, allow_blank=False)
    class Meta:
        model = Reviews
        fields = '__all__'
        
        def validate_business_user(self, value):
            """Validates `business_user`"""
            if value is None:
                raise serializers.ValidationError("Ein `business_user` muss angegeben werden.")
            return value