from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.conf import settings
from finances.models import TransactionImport
from .transaction_import_serializers import TransactionImportSerializer, ProcessTransactionImportSerializer, UpdateStatusTransactionImportSerializer    
from .tasks import process_transaction_import
from .processors.excel_processor_service import ExcelTransactionService
import io
import os
from datetime import datetime
from drf_spectacular.utils import extend_schema
from loguru import logger

class TransactionImportViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionImportSerializer
    permission_classes = [IsAuthenticated]
    queryset = TransactionImport.objects.all()
    
    def get_queryset(self):
        return TransactionImport.objects.filter(owner=self.request.user)
    
    @extend_schema(
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'source': {'type': 'string', 'enum': ['EXCEL', 'OFX']},
                    'file': {'type': 'string', 'format': 'binary'}
                },
                'required': ['source', 'file']
            }
        },
        responses={201: TransactionImportSerializer},
        description='Create a new transaction import with a file upload'
    )
    @action(methods=['post'], detail=False)
    def import_transactions(self, request):
        logger.info(f"User {request.user.id} requested transaction import")
        try:
            serializer = ProcessTransactionImportSerializer(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            import_obj: TransactionImport = serializer.instance
            
            logger.info(f"Transaction import {import_obj.id} created - Source: {import_obj.source}, User: {request.user.id}")
            
            if import_obj.status != TransactionImport.ImportStatus.PENDING.value:
                logger.warning(f"Import {import_obj.id} already processed or in progress - Status: {import_obj.status}")
                return Response(
                    {'error': 'Import already processed or in progress'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            task = process_transaction_import.delay(import_obj.id)
            import_obj.celery_task_id = task.id
            import_obj.save()
            
            logger.info(f"Transaction import {import_obj.id} queued for processing - Task ID: {task.id}")
            
            return Response({
                'message': 'Import processing started',
                'task_id': task.id
            })
        except Exception as e:
            logger.error(f"Error creating transaction import for user {request.user.id}: {str(e)}", exc_info=True)
            raise
    
    @action(detail=False, methods=['get'])
    def download_template(self, request):
        """Download template Excel para importação"""
        logger.info(f"User {request.user.id} requested transaction import template download")
        try:
            df = ExcelTransactionService.create_template()
            
            # Criar diretório para templates se não existir
            template_dir = os.path.join(settings.BASE_DIR, 'media', 'templates', 'transactions')
            os.makedirs(template_dir, exist_ok=True)
            
            # Nome do arquivo com timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'transaction_import_template_{timestamp}.xlsx'
            file_path = os.path.join(template_dir, filename)
            
            # Salvar arquivo no disco
            df.to_excel(file_path, index=False, engine='openpyxl')
            logger.debug(f"Template saved to {file_path}")
            
            # Criar buffer para download
            excel_buffer = io.BytesIO()
            df.to_excel(excel_buffer, index=False, engine='openpyxl')
            excel_buffer.seek(0)
            
            # Criar resposta HTTP
            response = HttpResponse(
                excel_buffer.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            logger.info(f"Template downloaded successfully for user {request.user.id} - File: {filename}")
            return response
        except Exception as e:
            logger.error(f"Error generating template for user {request.user.id}: {str(e)}", exc_info=True)
            raise 
    
    def update_status(self, request, *args, **kwargs):
        serializer = UpdateStatusTransactionImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)