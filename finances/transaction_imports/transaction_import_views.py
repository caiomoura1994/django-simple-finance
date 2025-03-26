from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from finances.models import TransactionImport
from .transaction_import_serializers import TransactionImportSerializer
from .tasks import process_transaction_import
from .processors.excel_processor_service import ExcelTransactionService
import io

class TransactionImportViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionImportSerializer
    permission_classes = [IsAuthenticated]
    queryset = TransactionImport.objects.all()
    
    def get_queryset(self):
        return TransactionImport.objects.filter(owner=self.request.user)
    
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        import_obj = self.get_object()
        
        if import_obj.status != TransactionImport.ImportStatus.PENDING:
            return Response(
                {'error': 'Import already processed or in progress'},
                status=status.HTTP_400_BAD_REQUEST
            )

        task = process_transaction_import.delay(import_obj.id)
        import_obj.celery_task_id = task.id
        import_obj.status = TransactionImport.ImportStatus.PROCESSING
        import_obj.save()
        
        return Response({
            'message': 'Import processing started',
            'task_id': task.id
        })
    
    @action(detail=False, methods=['get'])
    def download_template(self, request):
        """Download template Excel para importação"""
        df = ExcelTransactionService.create_template()
        
        # Criar buffer para o arquivo Excel
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        
        # Criar resposta HTTP
        response = HttpResponse(
            excel_buffer.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="transaction_import_template.xlsx"'
        return response 