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

    - `details`: Nested serializer for offer details (`OfferDetailsSerializer`).
    - `min_price`: Minimum price of the associated offer details (calculated).
    - `min_delivery_time`: Minimum delivery time of the associated offer details (calculated).
    - `user_details`: Nested serializer for user information (`UserSerializer`).
    - `user`: Read-only field representing the offer creator.
    """
    details = OfferDetailsSerializer(many=True, source='offer_details')
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    min_delivery_time = serializers.IntegerField(read_only=True)
    user_details = UserSerializer(source="user", read_only=True)
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Offers
        fields = '__all__'

    def create(self, validated_data):
        """
        Creates an offer along with its associated offer details.

        - Extracts `offer_details` data and removes it from `validated_data`.
        - Creates an `Offers` instance.
        - Iterates through `offer_details` and creates `OfferDetails` instances linked to the offer.
        - Aggregates the minimum price and delivery time from related `OfferDetails`.
        - Saves the updated `min_price` and `min_delivery_time` to the offer.
        """
        details_data = validated_data.pop('offer_details', [])
        offer = Offers.objects.create(**validated_data)
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
    
    def update(self, instance, validated_data):
        """
        Updates an offer and its associated offer details.

        - Extracts `offer_details` from `validated_data`.
        - Updates the offer's `title` and `description`.
        - Deletes existing `OfferDetails` and recreates them with new data.
        - Aggregates and updates `min_price` and `min_delivery_time`.
        """
        details_data = validated_data.pop('offer_details', [])
        instance.title = validated_data.get('title', instance.title)
        instance.description = validated_data.get('description', instance.description)
        instance.save()
        
         # Delete old OfferDetails and replace them with new ones
        instance.offer_details.all().delete()
        for detail_data in details_data:
            OfferDetails.objects.create(offer=instance, **detail_data)
            
        # Aggregate values from related OfferDetails
        aggregated = OfferDetails.objects.filter(offer=instance).aggregate(
            min_price=Min("price"),
            min_delivery_time=Min("delivery_time_in_days")
        )
        
        # Update the Offer object with new values
        instance.min_price = aggregated.get('min_price') or 0
        instance.min_delivery_time = aggregated.get('min_delivery_time') or 0
        instance.save()
        return instance

   
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
        
        # Retrieve the selected OfferDetails instance
        try:
            offer_detail = OfferDetails.objects.get(id=offer_detail_id)
        except OfferDetails.DoesNotExist:
            raise serializers.ValidationError("OfferDetail not found")
        
        # Ensure the request context is provided
        request = self.context.get('request')
        if request is None:
            raise serializers.ValidationError("Request context not provided")

        # Retrieve the customer's profile based on the request user
        try:
            customer_profile = Profil.objects.get(user=request.user)
        except Profil.DoesNotExist:
            raise serializers.ValidationError("Customer profile not found")
        print("🔍 Customer Profile:", customer_profile)
        # Create the order with data from the selected OfferDetail
        order = Orders.objects.create(
            customer_user=customer_profile,
            business_user=offer_detail.offer.user,
            title=offer_detail.offer.title,
            revisions=offer_detail.revisions,
            delivery_time_in_days=offer_detail.delivery_time_in_days,
            price=offer_detail.price,
            features=offer_detail.features,
            offer_type=offer_detail.offer_type,
            status="in_progress"
        )
        return order




class ProfilDetailSerializer(serializers.ModelSerializer):
    """
    Serializer für GET-Anfragen.
    - Zeigt User-Daten als einzelne Felder, nicht verschachtelt.
    """
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())  
    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    file = serializers.SerializerMethodField()  
    type = serializers.SerializerMethodField()  # Gibt `profile_type` als `type` zurück

    class Meta:
        model = Profil
        fields = [
            "user", "username", "first_name", "last_name", "email",
            "file", "location", "tel", "description",
            "working_hours", "type", "created_at"
        ]
        read_only_fields = ["created_at"]

    def get_file(self, obj):
        """Gibt nur den Dateinamen zurück"""
        return "media/uploads/" + os.path.basename(obj.file.name) if obj.file else None
    
    def get_type(self, obj):
        """Gibt `profile_type` als `type` zurück"""
        return obj.profile_type  # Intern wird `profile_type` verwendet

class ProfilUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer für PATCH-Anfragen.
    - User-Daten werden als `user`-Objekt erwartet.
    """
    user = UserSerializer()  
    file = serializers.SerializerMethodField()  

    class Meta:
        model = Profil
        fields = [
            "user", "file", "location", "tel", "description",
            "working_hours", "profile_type"  # Geändert von `type` zu `profile_type`
        ]

    def get_file(self, obj):
        """Gibt nur den Dateinamen zurück"""
        return "media/uploads/" + os.path.basename(obj.file.name) if obj.file else None

    def update(self, instance, validated_data):
        """
        Aktualisiert `Profil`- und `User`-Daten.
        """
        print("🔍 Validated Data:", validated_data)

        # User-Daten herausziehen und User-Objekt aktualisieren
        user_data = validated_data.pop("user", None)
        if user_data:
            user = instance.user
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save()

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        """
        Ändert die Response, sodass `user` nur als ID zurückgegeben wird.
        """
        rep = super().to_representation(instance)
        rep["user"] = instance.user.pk  
        rep["type"] = instance.profile_type  # Geändert, um `profile_type` als `type` zurückzugeben
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
        Ändert die API-Response, sodass `profile_type` als `type` zurückgegeben wird.
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
        Ändert die API-Response, sodass `profile_type` als `type` zurückgegeben wird.
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
    business_user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    reviewer = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Reviews
        fields = '__all__'