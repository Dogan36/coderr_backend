
from django.db import models

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
    revisions = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_time_in_days = models.IntegerField(default=0)
    features = models.JSONField(default=list, blank=True, null=True)
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
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    offer_type_choices = [
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
    ]
    customer_user = models.ForeignKey('Profil', on_delete=models.CASCADE)
    business_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='business_user')
    title = models.CharField(max_length=100)
    revisions = models.IntegerField(default=0)
    status = models.CharField(max_length=50, choices=status_choices, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    offer_type = models.CharField(max_length=50, choices=offer_type_choices, default='basic')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.title

class Profil(models.Model):
    type_choices = [
        ('customer', 'Customer'),
        ('business', 'Business'),
    ]
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE)
    location = models.CharField(max_length=100)
    file =  models.FileField(upload_to='uploads/', blank=True, null=True)
    tel = models.CharField(max_length=100)
    description = models.CharField(max_length=100, blank=True, null=True)
    working_hours = models.CharField(max_length=100, blank=True, null=True)
    type = models.CharField(max_length=50, choices=type_choices, default='customer')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.user.username

  
class Reviews(models.Model):
    business_user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    reviewer = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='reviewer')
    rating = models.IntegerField()
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
