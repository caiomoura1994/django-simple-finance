from rest_framework import serializers
from business_suppliers.models import Supplier
from django.utils.text import slugify
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