from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from finances.models import Transaction, Category, Account
from django.urls import reverse
from rest_framework import status
from decimal import Decimal
from django.utils import timezone

class TransactionViewSetTest(TestCase):
    def tearDown(self):
        Transaction.objects.all().delete()
        Category.objects.all().delete()
        Account.objects.all().delete()
        User.objects.all().delete()

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test category and account
        self.category = Category.objects.create(
            name='Test Category',
            owner=self.user
        )
        
        self.account = Account.objects.create(
            name='Test Account',
            balance=1000.00,
            owner=self.user
        )
        
        # Create a test transaction
        self.transaction = Transaction.objects.create(
            kind_of_transaction='EXPENSE',
            amount=100.00,
            date=timezone.now().date(),
            description='Test transaction',
            category=self.category,
            account=self.account,
            owner=self.user
        )

    def test_list_transactions(self):
        url = reverse('transaction-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 1)

    def test_create_transaction(self):
        url = reverse('transaction-list')
        data = {
            'kind_of_transaction': 'INCOME',
            'amount': '150.00',
            'date': timezone.now().date().isoformat(),
            'description': 'New test transaction',
            'category': self.category.id,
            'account': self.account.id
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['amount'], '150.00')
        self.assertEqual(response.data['description'], 'New test transaction')

    def test_retrieve_transaction(self):
        url = reverse('transaction-detail', args=[self.transaction.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['amount'], '100.00')


    def test_summary_endpoint(self):
        # Create an income transaction
        Transaction.objects.create(
            kind_of_transaction='INCOME',
            amount=500.00,
            date=timezone.now().date(),
            description='Test income',
            category=self.category,
            account=self.account,
            owner=self.user
        )

        url = reverse('transaction-summary')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_income'], Decimal('500.00'))
        self.assertEqual(response.data['total_expenses'], Decimal('100.00'))
        self.assertEqual(response.data['balance'], Decimal('400.00'))

    def test_by_category_endpoint(self):
        url = reverse('transaction-by-category')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)

    def test_by_account_endpoint(self):
        url = reverse('transaction-by-account')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)

    def test_invalid_category(self):
        # Create another user and their category
        other_user = User.objects.create_user(username='other', password='pass123')
        other_category = Category.objects.create(name='Other Category', owner=other_user)
        
        url = reverse('transaction-list')
        data = {
            'kind_of_transaction': 'EXPENSE',
            'amount': '150.00',
            'date': timezone.now().date().isoformat(),
            'description': 'Test transaction',
            'category': other_category.id,
            'account': self.account.id
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('category', response.data) 