from ofxparse import OfxParser
from typing import List
from finances.models import Transaction, Category, Account
from .base import TransactionProcessor
from decimal import Decimal
from django.utils.text import slugify
from loguru import logger

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
        logger.info(f"Processing OFX file: {file_path} for user {owner.id}")
        try:
            with open(file_path, 'rb') as file:
                ofx = OfxParser.parse(file)
            
            logger.debug(f"OFX file parsed successfully - {len(ofx.accounts)} accounts found")
            transactions = []
            accounts_created = 0
            categories_created = 0
            
            # Processar cada conta no arquivo OFX
            for account_ofx in ofx.accounts:
                # Criar ou obter a conta
                account_name = account_ofx.account_id
                if hasattr(account_ofx, 'desc') and account_ofx.desc:
                    account_name = account_ofx.desc

                account, created = Account.objects.get_or_create(
                    owner=owner,
                    name=account_name,
                    defaults={
                        'slug': slugify(account_name),
                        'description': f'Conta importada do OFX - {account_ofx.account_type}',
                        'balance': Decimal('0.00')
                    }
                )
                if created:
                    accounts_created += 1
                    logger.debug(f"Account created: {account_name}")

                # Processar transações da conta
                account_transactions_count = len(account_ofx.statement.transactions) if hasattr(account_ofx, 'statement') and account_ofx.statement else 0
                logger.debug(f"Processing {account_transactions_count} transactions for account {account_name}")
                
                for ofx_transaction in account_ofx.statement.transactions:
                    # Determinar o tipo de transação
                    amount = Decimal(str(ofx_transaction.amount))
                    transaction_type = 'INCOME' if amount > 0 else 'EXPENSE'

                    # Criar ou obter categoria baseada no tipo de transação do OFX
                    category_name = ofx_transaction.type if ofx_transaction.type else 'Outros'
                    category, created = Category.objects.get_or_create(
                        owner=owner,
                        name=category_name,
                        defaults={
                            'slug': slugify(category_name),
                            'description': f'Categoria importada do OFX'
                        }
                    )
                    if created:
                        categories_created += 1

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

            logger.info(f"OFX processing completed - {len(transactions)} transactions created, {accounts_created} accounts created, {categories_created} categories created")
            return transactions

        except Exception as e:
            logger.error(f"Error processing OFX file {file_path} for user {owner.id}: {str(e)}", exc_info=True)
            raise ValueError(f"Erro ao processar arquivo OFX: {str(e)}")

    @classmethod
    def process_ofx(cls, file_path: str, owner) -> List[Transaction]:
        """Método de classe para processar OFX sem instanciar"""
        processor = cls()
        return processor.process(file_path, owner) 