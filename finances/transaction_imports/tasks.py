from celery import shared_task
from celery.utils.log import get_task_logger
from finances.models import TransactionImport
import os
from .processors import ProcessorFactory

logger = get_task_logger(__name__)

@shared_task(bind=True)
def process_transaction_import(self, import_id):
    import_obj = TransactionImport.objects.get(id=import_id)
    logger.info(f"Starting to process import {import_id}")
    file_path = import_obj.file.path
    try:
        file_extension = os.path.splitext(file_path)[1]
        
        # Obter o processador apropriado
        processor = ProcessorFactory.get_processor(file_extension)
        
        # Processar as transações
        transactions = processor.process(file_path, import_obj.owner)
        
        # Contar total de transações
        import_obj.total_items = len(transactions)
        import_obj.save()
        
        # Processar cada transação
        for transaction in transactions:
            try:
                transaction.save()
                import_obj.processed_items += 1
                import_obj.save()
            except Exception as e:
                logger.error(f"Error processing transaction: {str(e)}")
                import_obj.error_message += f"Error processing transaction: {str(e)}\n"
                import_obj.save()
        
        # Marcar como concluído
        import_obj.status = TransactionImport.ImportStatus.COMPLETED
        import_obj.save()
        
        # Limpar arquivo temporário
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        logger.error(f"Error processing import {import_id}: {str(e)}")
        import_obj.status = TransactionImport.ImportStatus.FAILED
        import_obj.error_message = str(e)
        import_obj.save()
        
        # Limpar arquivo temporário em caso de erro
        if os.path.exists(file_path):
            os.remove(file_path)
