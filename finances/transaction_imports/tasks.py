from celery import shared_task
from finances.models import TransactionImport
import os
from .processors import ProcessorFactory
from loguru import logger

@shared_task(bind=True)
def process_transaction_import(self, import_id):
    logger.info(f"Starting to process transaction import {import_id}")
    try:
        import_obj = TransactionImport.objects.get(id=import_id)
        file_path = import_obj.file.path
        file_extension = os.path.splitext(file_path)[1]
        
        logger.info(f"Processing import {import_id} - File: {file_path}, Extension: {file_extension}, Owner: {import_obj.owner.id}")
        
        # Obter o processador apropriado
        processor = ProcessorFactory.get_processor(file_extension)
        logger.debug(f"Using processor: {processor.__class__.__name__}")
        
        # Processar as transações
        transactions = processor.process(file_path, import_obj.owner)
        logger.info(f"Processed {len(transactions)} transactions from file")
        
        # Contar total de transações
        import_obj.total_items = len(transactions)
        import_obj.save()
        
        # Processar cada transação
        errors_count = 0
        for idx, transaction in enumerate(transactions):
            try:
                transaction.save()
                import_obj.processed_items += 1
                import_obj.save()
            except Exception as e:
                errors_count += 1
                logger.error(f"Error processing transaction {idx+1}/{len(transactions)} in import {import_id}: {str(e)}", exc_info=True)
                import_obj.error_message += f"Error processing transaction: {str(e)}\n"
                import_obj.save()
        
        if errors_count > 0:
            logger.warning(f"Import {import_id} completed with {errors_count} errors out of {len(transactions)} transactions")
        else:
            logger.info(f"Import {import_id} completed successfully - {len(transactions)} transactions processed")
        
        # Marcar como concluído
        import_obj.status = TransactionImport.ImportStatus.COMPLETED
        import_obj.save()
        
        # Limpar arquivo temporário
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.debug(f"Temporary file removed: {file_path}")
            
    except TransactionImport.DoesNotExist:
        logger.error(f"TransactionImport with id {import_id} does not exist")
        raise
    except Exception as e:
        logger.error(f"Error processing import {import_id}: {str(e)}", exc_info=True)
        try:
            import_obj = TransactionImport.objects.get(id=import_id)
            import_obj.status = TransactionImport.ImportStatus.FAILED
            import_obj.error_message = str(e)
            import_obj.save()
            
            # Limpar arquivo temporário em caso de erro
            if hasattr(import_obj, 'file') and import_obj.file:
                file_path = import_obj.file.path
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Temporary file removed after error: {file_path}")
        except Exception as save_error:
            logger.error(f"Failed to update import {import_id} status after error: {str(save_error)}")
        raise
