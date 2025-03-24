from django.db import models
from django.contrib.auth.models import User
from core.base_model import BaseModel
from finances.models import Transaction

class Supplier(BaseModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_business_suppliers')
    
    class Meta:
        ordering = ['name']
        unique_together = ['owner', 'slug']

    def __str__(self):
        return f"{self.pk} - {self.name}"

class SupplierTransaction(BaseModel):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='transactions')
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name='supplier_transaction')

    class Meta:
        ordering = ['-transaction__date']
        unique_together = ['supplier', 'transaction']

    def __str__(self):
        return f"{self.supplier.name} - {self.transaction.description[:30]}"
