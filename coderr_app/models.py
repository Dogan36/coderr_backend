from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from decimal import Decimal
def default_features():
    return []
class Offers(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    image = models.FileField(upload_to='uploads/', blank=True, null=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    min_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_delivery_time = models.IntegerField(default=0)

    def __str__(self):
        return self.title

class OfferDetails(models.Model):
    offer = models.ForeignKey(Offers, on_delete=models.CASCADE, related_name='offer_details')
    title = models.CharField(max_length=100)
    revisions = models.IntegerField(default=0, validators=[MinValueValidator(-1)] )
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    delivery_time_in_days = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    features = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    offer_type_choices = [
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
    ]
    offer_type = models.CharField(max_length=50, choices=offer_type_choices, default='basic')

    def __str__(self):
        return f"{self.offer.title} - {self.offer_type}"
    
class Orders(models.Model):
    status_choices = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    offer_type_choices = [
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
    ]
    customer_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='customer_orders')
    business_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='business_user')
    title = models.CharField(max_length=100)
    revisions = models.IntegerField(default=0, validators=[MinValueValidator(-1)])
    status = models.CharField(max_length=50, choices=status_choices, default='in_progress')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    offer_type = models.CharField(max_length=50, choices=offer_type_choices, default='basic')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(Decimal("0.00"))])
    delivery_time_in_days = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    features = models.JSONField(default=default_features)

    def __str__(self):
        return f"Order {self.id}: {self.title} ({self.status})"

class Profil(models.Model):
    type_choices = [
        ('customer', 'Customer'),
        ('business', 'Business'),
    ]
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE)
    location = models.CharField(max_length=100)
    file =  models.FileField(upload_to='uploads/', blank=True, null=True)
    tel = models.CharField(max_length=100, blank=True, default="")
    description = models.CharField(max_length=100, blank=True, default="")
    working_hours = models.CharField(max_length=100, blank=True, default="")
    profile_type = models.CharField(max_length=50, choices=type_choices, default='customer')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.user.username

  
class Reviews(models.Model):
    business_user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    reviewer = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='reviewer')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
