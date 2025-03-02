from os import read
from rest_framework import serializers
from django.contrib.auth.models import User
from coderr_app.models import Offers, OfferDetails, Orders, Profil, Reviews
from django.db.models import Min
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['pk', 'username', 'first_name', 'last_name', 'email']

class OfferDetailsSerializer(serializers.ModelSerializer):
    features = serializers.ListField(child=serializers.CharField())
    class Meta:
        model = OfferDetails
        fields = ['id', 'title', 'revisions', 'delivery_time_in_days', 'price', 'features', 'offer_type']
        extra_kwargs = {
            'offer': {'read_only': True}
        }
              
class OffersSerializer(serializers.ModelSerializer):
    details = OfferDetailsSerializer(many=True, source='offer_details')
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    min_delivery_time = serializers.IntegerField(read_only=True)
    user_details = UserSerializer(source="user", read_only=True)
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Offers
        fields = '__all__'

    def create(self, validated_data):
        details_data = validated_data.pop('offer_details', [])
        offer = Offers.objects.create(**validated_data)
        for detail_data in details_data:
            OfferDetails.objects.create(offer=offer, **detail_data)
        
        # Aggregiere die Werte aus den zugehörigen OfferDetails
        aggregated = OfferDetails.objects.filter(offer=offer).aggregate(
            min_price=Min("price"),
            min_delivery_time=Min("delivery_time_in_days")
        )
        # Aktualisiere das Offer-Objekt
        offer.min_price = aggregated.get('min_price') or 0
        offer.min_delivery_time = aggregated.get('min_delivery_time') or 0
        offer.save()
        return offer
    
    def update(self, instance, validated_data):
        
        details_data = validated_data.pop('offer_details', [])
        instance.title = validated_data.get('title', instance.title)
        instance.description = validated_data.get('description', instance.description)
        instance.save()
        # Lösche alle alten OfferDetails
        instance.offer_details.all().delete()
        for detail_data in details_data:
            OfferDetails.objects.create(offer=instance, **detail_data)
        # Aggregiere die Werte aus den zugehörigen OfferDetails
        aggregated = OfferDetails.objects.filter(offer=instance).aggregate(
            min_price=Min("price"),
            min_delivery_time=Min("delivery_time_in_days")
        )
        # Aktualisiere das Offer-Objekt
        instance.min_price = aggregated.get('min_price') or 0
        instance.min_delivery_time = aggregated.get('min_delivery_time') or 0
        instance.save()
        return instance
   
class OrdersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Orders
        fields = '__all__'
        
    

class OrderCreateSerializer(serializers.ModelSerializer):
    # Der Client liefert nur die ID des OfferDetails, das er wählen möchte.
    offer_detail_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Orders
        fields = ['offer_detail_id']  # Nur dieser Schlüssel wird im Input erwartet

    def create(self, validated_data):
        offer_detail_id = validated_data.pop('offer_detail_id')
        try:
            offer_detail = OfferDetails.objects.get(id=offer_detail_id)
        except OfferDetails.DoesNotExist:
            raise serializers.ValidationError("OfferDetail not found")

        request = self.context.get('request')
        if request is None:
            raise serializers.ValidationError("Request context not provided")

        # Hole das Profil des Kunden (Customer User) anhand des request.user
        try:
            customer_profile = Profil.objects.get(user=request.user)
        except Profil.DoesNotExist:
            raise serializers.ValidationError("Customer profile not found")

        # Erstelle die Order basierend auf den Daten des ausgewählten OfferDetail
        order = Orders.objects.create(
            customer_user=customer_profile,                    # Der Kunde, der den Request gesendet hat
            business_user=offer_detail.offer.user,             # Angenommen, der Ersteller des Angebots ist der Business User
            title=offer_detail.offer.title,                    # Z. B. der Titel des Angebots
            revisions=offer_detail.revisions,                  # Anzahl der Revisionen aus dem OfferDetail
            delivery_time_in_days=offer_detail.delivery_time_in_days,
            price=offer_detail.price,
            features=offer_detail.features,
            offer_type=offer_detail.offer_type,
            status="in_progress"  # Initialer Status
        )
        return order


class ProfilSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())  # Zeigt nur die ID des Users
    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    
    class Meta:
        model = Profil
        fields = [
            "user", "username", "first_name", "last_name", "file",
            "location", "tel", "description", "working_hours",
            "type", "email", "created_at"
        ]
        read_only_fields = ["created_at"]
        
class ProfilTypeSingleSerializer(serializers.ModelSerializer):
    user = UserSerializer() 
    class Meta:
        model = Profil
        fields = [
            "user", "file",
            "location", "tel", "description", "working_hours",
            "type", "created_at"
        ]
        read_only_fields = ["created_at"]


class ProfilTypeSerializer(serializers.ModelSerializer):
    user = UserSerializer() 
    
    class Meta:
        model = Profil
        fields = [
            "user", "file",
            "location", "tel", "description", "working_hours",
            "type", "created_at"
        ]
        read_only_fields = ["created_at"]

class ReviewsSerializer(serializers.ModelSerializer):
    business_user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    reviewer = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Reviews
        fields = '__all__'