from .excel_processor_service import ExcelTransactionService
from .base import TransactionProcessor

class ProcessorFactory:
    """Fábrica para criar processadores de transações"""
    
    PROCESSORS = {
        '.xlsx': ExcelTransactionService,
        '.xls': ExcelTransactionService,
    }
    
    @classmethod
    def get_processor(cls, file_extension: str) -> TransactionProcessor:
        """
        Retorna o processador apropriado para o tipo de arquivo
        
        Args:
            file_extension (str): Extensão do arquivo (ex: .xlsx, .xls)
            
        Returns:
            TransactionProcessor: Instância do processador apropriado
            
        Raises:
            ValueError: Se não houver processador para a extensão
        """
        processor_class = cls.PROCESSORS.get(file_extension.lower())
        if not processor_class:
            supported_extensions = ', '.join(cls.PROCESSORS.keys())
            raise ValueError(
                f"Extensão {file_extension} não suportada. "
                f"Extensões suportadas: {supported_extensions}"
            )
        
        return processor_class() 