import pandas as pd
from datetime import datetime
from finances.models import Transaction, Category, Account
from .base import TransactionProcessor
from typing import List
from django.utils import timezone
from decimal import Decimal
from loguru import logger

class ExcelTransactionService(TransactionProcessor):
    REQUIRED_COLUMNS = [
        'date',
        'description',
        'amount',
        'kind_of_transaction',
        'category',
        'account'
    ]

    @classmethod
    def create_template(cls) -> pd.DataFrame:
        """Cria um template Excel com as colunas necessárias e dados de exemplo"""
        now = timezone.now()
        
        example_data = {
            'date': [
                now.strftime('%Y-%m-%d'),  # Hoje
                (now - timezone.timedelta(days=1)).strftime('%Y-%m-%d'),  # Ontem
                (now - timezone.timedelta(days=2)).strftime('%Y-%m-%d'),  # 2 dias atrás
                now.strftime('%Y-%m-%d'),  # Hoje
                now.strftime('%Y-%m-%d'),  # Hoje
            ],
            'description': [
                'Compra no Supermercado',
                'Salário',
                'Conta de Luz',
                'Academia',
                'Venda de Produto',
            ],
            'amount': [
                150.75,  # Supermercado
                5000.00,  # Salário
                89.90,   # Conta de Luz
                99.90,   # Academia
                250.00,  # Venda
            ],
            'kind_of_transaction': [
                'EXPENSE',  # Supermercado
                'INCOME',   # Salário
                'EXPENSE',  # Conta de Luz
                'EXPENSE',  # Academia
                'INCOME',   # Venda
            ],
            'category': [
                'Alimentação',
                'Salário',
                'Moradia',
                'Saúde',
                'Vendas',
            ],
            'account': [
                'Conta Principal',
                'Conta Salário',
                'Conta Principal',
                'Cartão de Crédito',
                'Conta Principal',
            ]
        }
        df = pd.DataFrame(example_data)
        return df

    @classmethod
    def validate_columns(cls, df: pd.DataFrame) -> None:
        """Valida se todas as colunas necessárias estão presentes"""
        missing_columns = [col for col in cls.REQUIRED_COLUMNS if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing required columns: {', '.join(missing_columns)}")
            raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(missing_columns)}")
        logger.debug(f"Column validation passed - Found {len(df.columns)} columns")

    @classmethod
    def validate_data(cls, df: pd.DataFrame) -> None:
        """Valida os dados do DataFrame"""
        logger.debug(f"Validating {len(df)} rows of data")
        # Validar datas
        try:
            df['date'] = pd.to_datetime(df['date'])
        except Exception as e:
            logger.error(f"Error converting dates: {str(e)}")
            raise ValueError(f"Erro ao converter datas: {str(e)}")

        # Validar valores
        try:
            df['amount'] = pd.to_numeric(df['amount'])
        except Exception as e:
            logger.error(f"Error converting amounts: {str(e)}")
            raise ValueError(f"Erro ao converter valores: {str(e)}")

        # Validar tipo de transação
        invalid_types = df[~df['kind_of_transaction'].isin(['INCOME', 'EXPENSE'])]['kind_of_transaction'].unique()
        if len(invalid_types) > 0:
            logger.warning(f"Invalid transaction types found: {', '.join(invalid_types)}")
            raise ValueError(f"Tipos de transação inválidos: {', '.join(invalid_types)}")

        # Validar se há valores vazios
        for column in cls.REQUIRED_COLUMNS:
            if df[column].isnull().any():
                null_count = df[column].isnull().sum()
                logger.error(f"Column {column} contains {null_count} null values")
                raise ValueError(f"A coluna {column} contém valores vazios")
        
        logger.debug("Data validation passed")

    def process(self, file_path: str, owner) -> List[Transaction]:
        """Processa o arquivo Excel e retorna uma lista de transações"""
        logger.info(f"Processing Excel file: {file_path} for user {owner.id}")
        try:
            # Ler o arquivo Excel
            df = pd.read_excel(file_path, engine='openpyxl')
            logger.debug(f"Excel file read successfully - {len(df)} rows found")
            
            # Validar estrutura e dados
            self.validate_columns(df)
            self.validate_data(df)
            
            transactions = []
            categories_created = 0
            accounts_created = 0
            
            # Processar cada linha
            for idx, row in df.iterrows():
                # Criar ou obter categoria
                category, created = Category.objects.get_or_create(
                    owner=owner,
                    name=row['category'],
                    defaults={
                        'slug': row['category'].lower().replace(' ', '-'),
                        'description': f'Categoria criada automaticamente pela importação'
                    }
                )
                if created:
                    categories_created += 1

                # Criar ou obter conta
                account, created = Account.objects.get_or_create(
                    owner=owner,
                    name=row['account'],
                    defaults={
                        'slug': row['account'].lower().replace(' ', '-'),
                        'description': f'Conta criada automaticamente pela importação',
                        'balance': Decimal('0.00')
                    }
                )
                if created:
                    accounts_created += 1

                # Criar transação
                transaction = Transaction(
                    owner=owner,
                    date=row['date'],
                    description=row['description'],
                    amount=abs(Decimal(str(row['amount']))),
                    kind_of_transaction=row['kind_of_transaction'],
                    category=category,
                    account=account
                )
                transactions.append(transaction)

            logger.info(f"Excel processing completed - {len(transactions)} transactions created, {categories_created} categories created, {accounts_created} accounts created")
            return transactions

        except Exception as e:
            logger.error(f"Error processing Excel file {file_path} for user {owner.id}: {str(e)}", exc_info=True)
            raise ValueError(f"Erro ao processar arquivo Excel: {str(e)}")

    @classmethod
    def process_excel(cls, file_path: str, owner) -> List[Transaction]:
        """Método de classe para processar Excel sem instanciar"""
        processor = cls()
        return processor.process(file_path, owner) 