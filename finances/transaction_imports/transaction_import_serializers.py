from rest_framework import serializers
from finances.models import TransactionImport

class TransactionImportSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionImport
        fields = [
            'id',
            'source',
            'status',
            'file',
            'total_items',
            'processed_items',
            'error_message',
            'celery_task_id',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['owner', 'status', 'total_items', 'processed_items', 'error_message', 'celery_task_id']

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        validated_data['status'] = TransactionImport.ImportStatus.PENDING
        return super().create(validated_data) 