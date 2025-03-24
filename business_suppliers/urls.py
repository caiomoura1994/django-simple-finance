from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from business_suppliers.views import SupplierViewSet, SupplierTransactionViewSet

# Create the main router
router = DefaultRouter()
router.register(r'', SupplierViewSet, basename='supplier')

# Create the nested router for supplier transactions
supplier_router = routers.NestedSimpleRouter(router, r'', lookup='supplier')
supplier_router.register(r'transactions', SupplierTransactionViewSet, basename='supplier-transaction')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(supplier_router.urls)),
] 