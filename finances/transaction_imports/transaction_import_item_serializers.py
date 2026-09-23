from rest_framework import serializers

from finances.accounts.account_serializers import AccountSerializer
from finances.categories.category_serializers import CategorySerializer
from finances.models import Category, TransactionImportItem


class TransactionImportItemSerializer(serializers.ModelSerializer):
    account_details = AccountSerializer(source="account", read_only=True)
    suggested_category_details = CategorySerializer(
        source="suggested_category",
        read_only=True,
    )

    class Meta:
        model = TransactionImportItem
        fields = [
            "id",
            "transaction_import",
            "transaction",
            "kind_of_transaction",
            "amount",
            "date",
            "description",
            "account",
            "account_details",
            "suggested_category",
            "suggested_category_details",
            "categorization_source",
            "review_status",
            "ai_confidence",
            "ai_reasoning",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ApproveTransactionImportItemSerializer(serializers.Serializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    remember_choice = serializers.BooleanField(default=True)

    def validate_category(self, category):
        if category.owner != self.context["request"].user:
            raise serializers.ValidationError("Invalid category selected")
        return category
