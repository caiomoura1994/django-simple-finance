from rest_framework import serializers
from finances.models import Account
from django.utils.text import slugify

class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['id', 'name', 'description', 'slug', 'balance', 'is_active']
        read_only_fields = ['slug', 'balance']

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        validated_data['slug'] = slugify(validated_data['name'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data['owner'] = self.context['request'].user
        validated_data['slug'] = slugify(validated_data['name'])
        return super().update(instance, validated_data) 