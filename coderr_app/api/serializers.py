from os import read
from rest_framework import serializers
from django.contrib.auth.models import User
from coderr_app.models import Offers, OfferDetails, Orders, Profil, Reviews

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['pk', 'username', 'first_name', 'last_name', 'email']

class OfferDetailsSerializer(serializers.ModelSerializer):
    features = serializers.ListField(child=serializers.CharField())
    class Meta:
        model = OfferDetails
        fields = '__all__'
              
class OffersSerializer(serializers.ModelSerializer):
    details = OfferDetailsSerializer(many=True, read_only=True, source='offer_details')  
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    max_delivery_time = serializers.IntegerField(read_only=True)
    user_details = UserSerializer(source="user", read_only=True)

    class Meta:
        model = Offers
        fields = '__all__'

   
class OrdersSerializer(serializers.ModelSerializer):
    customer_user = serializers.PrimaryKeyRelatedField(queryset=Profil.objects.all())
    business_user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    class Meta:
        model = Orders
        fields = '__all__'


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
    reviewer = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    class Meta:
        model = Reviews
        fields = '__all__'