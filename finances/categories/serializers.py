from rest_framework import serializers
from finances.models import Category
from django.utils.text import slugify

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'slug']
        read_only_fields = ['slug']

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        validated_data['slug'] = slugify(validated_data['name'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data['owner'] = self.context['request'].user
        validated_data['slug'] = slugify(validated_data['name'])
        return super().update(instance, validated_data)
