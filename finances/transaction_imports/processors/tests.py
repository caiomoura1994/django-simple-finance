from django.test import TestCase
from django.contrib.auth.models import User
from finances.models import Transaction, Category, Account
from .excel_processor_service import ExcelTransactionService
from .ofx_processor_service import OFXTransactionService
from .factory import ProcessorFactory
import pandas as pd
import tempfile
import os
from decimal import Decimal
from datetime import datetime
from unittest.mock import patch, Mock

class BaseProcessorTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def tearDown(self):
        Transaction.objects.all().delete()
        Category.objects.all().delete()
        Account.objects.all().delete()
        User.objects.all().delete()

class ExcelProcessorTest(BaseProcessorTest):
    def setUp(self):
        super().setUp()
        self.processor = ExcelTransactionService()

    def create_test_excel(self, data=None):
        if data is None:
            data = {
                'date': ['2024-03-26'],
                'description': ['Test Transaction'],
                'amount': [100.00],
                'kind_of_transaction': ['EXPENSE'],
                'category': ['Test Category'],
                'account': ['Test Account']
            }
        
        df = pd.DataFrame(data)
        temp_file = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        df.to_excel(temp_file.name, index=False)
        return temp_file.name

    def test_create_template(self):
        """Testa a criação do template Excel"""
        df = ExcelTransactionService.create_template()
        self.assertListEqual(
            list(df.columns),
            ['date', 'description', 'amount', 'kind_of_transaction', 'category', 'account']
        )

    def test_validate_columns(self):
        """Testa a validação de colunas"""
        # Teste com colunas válidas
        df = pd.DataFrame(columns=ExcelTransactionService.REQUIRED_COLUMNS)
        try:
            ExcelTransactionService.validate_columns(df)
        except ValueError:
            self.fail("validate_columns() levantou ValueError inesperadamente!")

        # Teste com colunas faltando
        df = pd.DataFrame(columns=['date', 'amount'])
        with self.assertRaises(ValueError):
            ExcelTransactionService.validate_columns(df)

    def test_process_valid_excel(self):
        """Testa o processamento de um arquivo Excel válido"""
        file_path = self.create_test_excel()
        try:
            transactions = self.processor.process(file_path, self.user)
            self.assertEqual(len(transactions), 1)
            
            transaction = transactions[0]
            self.assertEqual(transaction.description, 'Test Transaction')
            self.assertEqual(transaction.amount, Decimal('100.00'))
            self.assertEqual(transaction.kind_of_transaction, 'EXPENSE')
            self.assertEqual(transaction.category.name, 'Test Category')
            self.assertEqual(transaction.account.name, 'Test Account')
        finally:
            os.unlink(file_path)

    def test_process_invalid_data(self):
        """Testa o processamento com dados inválidos"""
        # Teste com data inválida
        data = {
            'date': ['invalid-date'],
            'description': ['Test'],
            'amount': [100.00],
            'kind_of_transaction': ['EXPENSE'],
            'category': ['Test Category'],
            'account': ['Test Account']
        }
        file_path = self.create_test_excel(data)
        try:
            with self.assertRaises(ValueError):
                self.processor.process(file_path, self.user)
        finally:
            os.unlink(file_path)

class OFXProcessorTest(BaseProcessorTest):
    def setUp(self):
        super().setUp()
        self.processor = OFXTransactionService()

    def create_mock_ofx(self):
        """Cria um arquivo OFX mockado para testes"""
        ofx_content = """
        OFXHEADER:100
        DATA:OFXSGML
        VERSION:102
        SECURITY:NONE
        ENCODING:USASCII
        CHARSET:1252
        COMPRESSION:NONE
        OLDFILEUID:NONE
        NEWFILEUID:NONE
        
        <OFX>
            <SIGNONMSGSRSV1>
                <SONRS>
                    <STATUS>
                        <CODE>0</CODE>
                        <SEVERITY>INFO</SEVERITY>
                    </STATUS>
                    <DTSERVER>20240326120000</DTSERVER>
                    <LANGUAGE>POR</LANGUAGE>
                </SONRS>
            </SIGNONMSGSRSV1>
            <BANKMSGSRSV1>
                <STMTTRNRS>
                    <TRNUID>1</TRNUID>
                    <STATUS>
                        <CODE>0</CODE>
                        <SEVERITY>INFO</SEVERITY>
                    </STATUS>
                    <STMTRS>
                        <CURDEF>BRL</CURDEF>
                        <BANKACCTFROM>
                            <BANKID>123</BANKID>
                            <ACCTID>TEST-ACCOUNT</ACCTID>
                            <ACCTTYPE>CHECKING</ACCTTYPE>
                        </BANKACCTFROM>
                        <BANKTRANLIST>
                            <DTSTART>20240301</DTSTART>
                            <DTEND>20240326</DTEND>
                            <STMTTRN>
                                <TRNTYPE>DEBIT</TRNTYPE>
                                <DTPOSTED>20240326</DTPOSTED>
                                <TRNAMT>-50.00</TRNAMT>
                                <FITID>123456</FITID>
                                <PAYEE>Test Store</PAYEE>
                                <MEMO>Test Purchase</MEMO>
                            </STMTTRN>
                        </BANKTRANLIST>
                    </STMTRS>
                </STMTTRNRS>
            </BANKMSGSRSV1>
        </OFX>
        """
        temp_file = tempfile.NamedTemporaryFile(suffix='.ofx', delete=False)
        temp_file.write(ofx_content.encode())
        temp_file.close()
        return temp_file.name

    @patch('ofxparse.OfxParser.parse')
    def test_process_ofx(self, mock_parse):
        """Testa o processamento de arquivo OFX"""
        # Configurar o mock do parser OFX
        mock_account = Mock()
        mock_account.account_id = 'TEST-ACCOUNT'
        mock_account.account_type = 'CHECKING'
        mock_account.desc = None

        mock_transaction = Mock()
        mock_transaction.amount = Decimal('-50.00')
        mock_transaction.type = 'DEBIT'
        mock_transaction.date = datetime(2024, 3, 26)
        mock_transaction.payee = 'Test Store'
        mock_transaction.memo = 'Test Purchase'

        mock_statement = Mock()
        mock_statement.transactions = [mock_transaction]
        mock_account.statement = mock_statement

        mock_ofx = Mock()
        mock_ofx.accounts = [mock_account]
        mock_parse.return_value = mock_ofx

        # Testar processamento
        file_path = self.create_mock_ofx()
        try:
            transactions = self.processor.process(file_path, self.user)
            
            self.assertEqual(len(transactions), 1)
            transaction = transactions[0]
            
            self.assertEqual(transaction.description, 'Test Store - Test Purchase')
            self.assertEqual(transaction.amount, Decimal('50.00'))
            self.assertEqual(transaction.kind_of_transaction, 'EXPENSE')
            self.assertEqual(transaction.category.name, 'DEBIT')
            self.assertEqual(transaction.account.name, 'TEST-ACCOUNT')
        finally:
            os.unlink(file_path)

    def test_process_invalid_ofx(self):
        """Testa o processamento de arquivo OFX inválido"""
        temp_file = tempfile.NamedTemporaryFile(suffix='.ofx', delete=False)
        temp_file.write(b'Invalid OFX content')
        temp_file.close()
        
        try:
            with self.assertRaises(ValueError):
                self.processor.process(temp_file.name, self.user)
        finally:
            os.unlink(temp_file.name)

class ProcessorFactoryTest(TestCase):
    def test_get_excel_processor(self):
        """Testa obtenção do processador Excel"""
        processor = ProcessorFactory.get_processor('.xlsx')
        self.assertIsInstance(processor, ExcelTransactionService)
        
        processor = ProcessorFactory.get_processor('.xls')
        self.assertIsInstance(processor, ExcelTransactionService)

    def test_get_ofx_processor(self):
        """Testa obtenção do processador OFX"""
        processor = ProcessorFactory.get_processor('.ofx')
        self.assertIsInstance(processor, OFXTransactionService)
        
        processor = ProcessorFactory.get_processor('.qfx')
        self.assertIsInstance(processor, OFXTransactionService)

    def test_invalid_extension(self):
        """Testa extensão inválida"""
        with self.assertRaises(ValueError):
            ProcessorFactory.get_processor('.invalid') 