from abc import ABC, abstractmethod
from typing import List
from finances.models import Transaction

class TransactionProcessor(ABC):
    """Interface base para processadores de transações"""
    
    @abstractmethod
    def process(self, file_path: str, owner) -> List[Transaction]:
        """
        Processa o arquivo e retorna uma lista de transações
        
        Args:
            file_path (str): Caminho do arquivo a ser processado
            owner: Usuário dono das transações
            
        Returns:
            List[Transaction]: Lista de transações processadas
            
        Raises:
            ValueError: Se houver erro no processamento
        """
        pass 