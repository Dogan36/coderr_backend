from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OffersViewSet, OfferDetailsViewSet, OrdersViewSet, ReviewsViewSet, ProfileDetailView, BusinessProfilesListView, CustomerProfilesListView, RegisterAPIView, LoginAPIView, BaseInfoViewSet, BusinessOrderCountViewSet, BusinessCompletedOrderCountViewSet

router = DefaultRouter()
router.register(r'offers', OffersViewSet)
router.register(r'offerdetails', OfferDetailsViewSet)
router.register(r'orders', OrdersViewSet)
router.register(r'reviews', ReviewsViewSet)
router.register(r'base-info', BaseInfoViewSet, basename='base-info')
urlpatterns = [
    path('', include(router.urls)),
    path("profile/<int:pk>/", ProfileDetailView.as_view(), name="profile-detail"),
    path("profiles/business/", BusinessProfilesListView.as_view(), name="business-profiles"),
    path("profiles/customer/", CustomerProfilesListView.as_view(), name="customer-profiles"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("registration/", RegisterAPIView.as_view(), name="register"),
    path('order-count/<int:pk>/', BusinessOrderCountViewSet.as_view({'get': 'list'}), name='order-count'),
    path('completed-order-count/<int:pk>/', BusinessCompletedOrderCountViewSet.as_view({'get': 'list'}), name='completed-order-count'),
    
]

