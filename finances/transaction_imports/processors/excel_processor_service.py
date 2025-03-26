import pandas as pd
from datetime import datetime
from finances.models import Transaction, Category, Account
from .base import TransactionProcessor
from typing import List
from django.utils import timezone
from decimal import Decimal

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
        example_data = {
            'date': [timezone.now().strftime('%Y-%m-%d')],
            'description': ['Exemplo de transação'],
            'amount': [100.00],
            'kind_of_transaction': ['EXPENSE'],  # INCOME ou EXPENSE
            'category': ['Alimentação'],
            'account': ['Conta Principal']
        }
        df = pd.DataFrame(example_data)
        return df

    @classmethod
    def validate_columns(cls, df: pd.DataFrame) -> None:
        """Valida se todas as colunas necessárias estão presentes"""
        missing_columns = [col for col in cls.REQUIRED_COLUMNS if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(missing_columns)}")

    @classmethod
    def validate_data(cls, df: pd.DataFrame) -> None:
        """Valida os dados do DataFrame"""
        # Validar datas
        try:
            df['date'] = pd.to_datetime(df['date'])
        except Exception as e:
            raise ValueError(f"Erro ao converter datas: {str(e)}")

        # Validar valores
        try:
            df['amount'] = pd.to_numeric(df['amount'])
        except Exception as e:
            raise ValueError(f"Erro ao converter valores: {str(e)}")

        # Validar tipo de transação
        invalid_types = df[~df['kind_of_transaction'].isin(['INCOME', 'EXPENSE'])]['kind_of_transaction'].unique()
        if len(invalid_types) > 0:
            raise ValueError(f"Tipos de transação inválidos: {', '.join(invalid_types)}")

        # Validar se há valores vazios
        for column in cls.REQUIRED_COLUMNS:
            if df[column].isnull().any():
                raise ValueError(f"A coluna {column} contém valores vazios")

    def process(self, file_path: str, owner) -> List[Transaction]:
        """Processa o arquivo Excel e retorna uma lista de transações"""
        try:
            # Ler o arquivo Excel
            df = pd.read_excel(file_path)
            
            # Validar estrutura e dados
            self.validate_columns(df)
            self.validate_data(df)
            
            transactions = []
            
            # Processar cada linha
            for _, row in df.iterrows():
                # Criar ou obter categoria
                category, _ = Category.objects.get_or_create(
                    owner=owner,
                    name=row['category'],
                    defaults={
                        'slug': row['category'].lower().replace(' ', '-'),
                        'description': f'Categoria criada automaticamente pela importação'
                    }
                )

                # Criar ou obter conta
                account, _ = Account.objects.get_or_create(
                    owner=owner,
                    name=row['account'],
                    defaults={
                        'slug': row['account'].lower().replace(' ', '-'),
                        'description': f'Conta criada automaticamente pela importação',
                        'balance': Decimal('0.00')
                    }
                )

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

            return transactions

        except Exception as e:
            raise ValueError(f"Erro ao processar arquivo Excel: {str(e)}")

    @classmethod
    def process_excel(cls, file_path: str, owner) -> List[Transaction]:
        """Método de classe para processar Excel sem instanciar"""
        processor = cls()
        return processor.process(file_path, owner) 