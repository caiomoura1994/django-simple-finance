from ofxparse import OfxParser
from typing import List
from finances.models import Transaction, Category, Account
from .base import TransactionProcessor
from decimal import Decimal
from django.utils.text import slugify

class OFXTransactionService(TransactionProcessor):
    """Processador para arquivos OFX (Open Financial Exchange)"""

    def process(self, file_path: str, owner) -> List[Transaction]:
        """
        Processa o arquivo OFX e retorna uma lista de transações
        
        Args:
            file_path (str): Caminho do arquivo OFX
            owner: Usuário dono das transações
            
        Returns:
            List[Transaction]: Lista de transações processadas
        """
        try:
            with open(file_path, 'rb') as file:
                ofx = OfxParser.parse(file)
            
            transactions = []
            
            # Processar cada conta no arquivo OFX
            for account_ofx in ofx.accounts:
                # Criar ou obter a conta
                account_name = account_ofx.account_id
                if hasattr(account_ofx, 'desc') and account_ofx.desc:
                    account_name = account_ofx.desc

                account, _ = Account.objects.get_or_create(
                    owner=owner,
                    name=account_name,
                    defaults={
                        'slug': slugify(account_name),
                        'description': f'Conta importada do OFX - {account_ofx.account_type}',
                        'balance': Decimal('0.00')
                    }
                )

                # Processar transações da conta
                for ofx_transaction in account_ofx.statement.transactions:
                    # Determinar o tipo de transação
                    amount = Decimal(str(ofx_transaction.amount))
                    transaction_type = 'INCOME' if amount > 0 else 'EXPENSE'

                    # Criar ou obter categoria baseada no tipo de transação do OFX
                    category_name = ofx_transaction.type if ofx_transaction.type else 'Outros'
                    category, _ = Category.objects.get_or_create(
                        owner=owner,
                        name=category_name,
                        defaults={
                            'slug': slugify(category_name),
                            'description': f'Categoria importada do OFX'
                        }
                    )

                    # Criar transação
                    description = ofx_transaction.payee
                    if ofx_transaction.memo and ofx_transaction.memo != ofx_transaction.payee:
                        description = f"{ofx_transaction.payee} - {ofx_transaction.memo}"

                    transaction = Transaction(
                        owner=owner,
                        date=ofx_transaction.date,
                        description=description,
                        amount=abs(amount),
                        kind_of_transaction=transaction_type,
                        category=category,
                        account=account
                    )
                    transactions.append(transaction)

            return transactions

        except Exception as e:
            raise ValueError(f"Erro ao processar arquivo OFX: {str(e)}")

    @classmethod
    def process_ofx(cls, file_path: str, owner) -> List[Transaction]:
        """Método de classe para processar OFX sem instanciar"""
        processor = cls()
        return processor.process(file_path, owner) 