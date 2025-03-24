from rest_framework import serializers
from business_suppliers.models import Supplier, SupplierTransaction
from finances.transactions.transaction_serializers import TransactionSerializer
from django.utils.text import slugify
from finances.models import Transaction

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'email',
            'phone',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['owner', 'slug']

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        validated_data['slug'] = slugify(validated_data['name'])
        return super().create(validated_data) 

    def update(self, instance, validated_data):
        validated_data['slug'] = slugify(validated_data['name'])
        return super().update(instance, validated_data)

class SupplierTransactionSerializer(serializers.ModelSerializer):
    transaction = TransactionSerializer()
    
    class Meta:
        model = SupplierTransaction
        fields = ['id', 'supplier', 'transaction', 'created_at', 'updated_at']
        read_only_fields = ['id', 'supplier', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate that the transaction belongs to the same owner as the supplier."""
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("User context is required")
            
        supplier = data.get('supplier')
        if supplier and supplier.owner != request.user:
            raise serializers.ValidationError("Supplier does not belong to the current user")
            
        return data
    
    def create(self, validated_data):
        """Create a new supplier transaction with nested transaction."""
        transaction_data = validated_data.pop('transaction')
        supplier = validated_data.get('supplier')
        # Create the transaction first
        transaction = Transaction.objects.create(
            **transaction_data,
            owner=supplier.owner
        )
        # Create the supplier transaction
        supplier_transaction = SupplierTransaction.objects.create(
            transaction=transaction,
            supplier=supplier,
            owner=supplier.owner
        )
        return supplier_transaction
