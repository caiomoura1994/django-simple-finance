from rest_framework.permissions import IsAuthenticated
from business_suppliers.models import Supplier, SupplierTransaction
from business_suppliers.serializers import SupplierSerializer, SupplierTransactionSerializer
from rest_framework import viewsets, mixins

class SupplierViewSet(viewsets.ModelViewSet):
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'
    
    def get_queryset(self):
        return Supplier.objects.filter(owner=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class SupplierTransactionViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    serializer_class = SupplierTransactionSerializer
    permission_classes = [IsAuthenticated]
    queryset = SupplierTransaction.objects.none()
    def get_queryset(self):
        # if self.request.method == 'GET':
        #     return Transaction.objects.filter(
        #         owner=self.request.user,
        #         supplier_transaction__supplier__slug=self.kwargs['supplier_slug'],
        #     )
        return SupplierTransaction.objects.filter(supplier__owner=self.request.user, supplier__slug=self.kwargs['supplier_slug'])

    def perform_create(self, serializer):
        supplier = Supplier.objects.get(slug=self.kwargs['supplier_slug'])
        serializer.save(supplier=supplier)
