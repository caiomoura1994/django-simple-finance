from rest_framework import serializers

from finances.categories.category_serializers import CategorySerializer
from finances.models import TransactionCategoryRule


class TransactionCategoryRuleSerializer(serializers.ModelSerializer):
    category_details = CategorySerializer(source="category", read_only=True)

    class Meta:
        model = TransactionCategoryRule
        fields = [
            "id",
            "normalized_description",
            "kind_of_transaction",
            "category",
            "category_details",
            "times_applied",
            "last_used_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "normalized_description",
            "kind_of_transaction",
            "category_details",
            "times_applied",
            "last_used_at",
            "created_at",
            "updated_at",
        ]

    def validate_category(self, category):
        if category.owner != self.context["request"].user:
            raise serializers.ValidationError("Invalid category selected")
        return category
