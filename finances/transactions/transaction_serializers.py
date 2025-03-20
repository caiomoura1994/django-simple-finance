from rest_framework import serializers
from finances.models import Transaction
from finances.categories.category_serializers import CategorySerializer
from finances.accounts.account_serializers import AccountSerializer

class TransactionSerializer(serializers.ModelSerializer):
    category_details = CategorySerializer(source='category', read_only=True)
    account_details = AccountSerializer(source='account', read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id',
            'kind_of_transaction',
            'amount',
            'date',
            'description',
            'category',
            'category_details',
            'account',
            'account_details',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['owner']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero")
        return value

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)

    def validate(self, data):
        # Ensure the category belongs to the user
        if 'category' in data:
            category = data['category']
            if category.owner != self.context['request'].user:
                raise serializers.ValidationError({"category": "Invalid category selected"})
        
        # Ensure the account belongs to the user
        if 'account' in data:
            account = data['account']
            if account.owner != self.context['request'].user:
                raise serializers.ValidationError({"account": "Invalid account selected"})
        
        return data 