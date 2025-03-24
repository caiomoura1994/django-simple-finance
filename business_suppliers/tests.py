from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from business_suppliers.models import Supplier, SupplierTransaction
from finances.models import Transaction, Category, Account
from django.urls import reverse
from rest_framework import status
from decimal import Decimal
from django.utils import timezone

class SupplierViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            slug='test-supplier',
            description='Test description',
            email='test@supplier.com',
            phone='1234567890',
            owner=self.user
        )
    
    def tearDown(self):
        Supplier.objects.all().delete()
        User.objects.all().delete()

    def test_list_suppliers(self):
        url = reverse('supplier-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 1)
    
    def test_create_supplier(self):
        url = reverse('supplier-list')
        data = {
            'name': 'New Supplier',
            'description': 'Test description',
            'email': 'new@supplier.com',
            'phone': '9876543210'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Supplier')
        self.assertEqual(response.data['slug'], 'new-supplier')
        self.assertEqual(response.data['email'], 'new@supplier.com')
        self.assertEqual(response.data['phone'], '9876543210')
    
    def test_retrieve_supplier(self):
        url = reverse('supplier-detail', kwargs={'slug': self.supplier.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Supplier')
        self.assertEqual(response.data['email'], 'test@supplier.com')
        self.assertEqual(response.data['phone'], '1234567890')
    
    def test_update_supplier(self):
        url = reverse('supplier-detail', kwargs={'slug': self.supplier.slug})
        data = {
            'name': 'Updated Supplier',
            'description': 'Updated description',
            'email': 'updated@supplier.com',
            'phone': '5555555555'
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Supplier')
        self.assertEqual(response.data['slug'], 'updated-supplier')
        self.assertEqual(response.data['email'], 'updated@supplier.com')
        self.assertEqual(response.data['phone'], '5555555555')
    
    def test_delete_supplier(self):
        url = reverse('supplier-detail', kwargs={'slug': self.supplier.slug})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Supplier.objects.filter(slug=self.supplier.slug).exists())

class SupplierTransactionViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create supplier
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            slug='test-supplier',
            owner=self.user
        )
        
        # Create category and account
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category',
            owner=self.user
        )
        
        self.account = Account.objects.create(
            name='Test Account',
            slug='test-account',
            balance=1000.00,
            owner=self.user
        )
        
        # Create transaction
        self.transaction = Transaction.objects.create(
            kind_of_transaction='EXPENSE',
            amount=100.00,
            date=timezone.now(),
            description='Test transaction',
            category=self.category,
            account=self.account,
            owner=self.user
        )
        
        # Create supplier transaction
        self.supplier_transaction = SupplierTransaction.objects.create(
            supplier=self.supplier,
            transaction=self.transaction,
            owner=self.user
        )
    
    def tearDown(self):
        SupplierTransaction.objects.all().delete()
        Transaction.objects.all().delete()
        Category.objects.all().delete()
        Account.objects.all().delete()
        Supplier.objects.all().delete()
        User.objects.all().delete()


    def test_create_supplier_transaction(self):
        url = reverse('supplier-transaction-list', kwargs={'supplier_slug': self.supplier.slug})
        data = {
            'transaction': {
                'kind_of_transaction': 'INCOME',
                'amount': '150.00',
                'date': timezone.now().date().isoformat(),
                'description': 'New test transaction',
                'category': self.category.id,
                'account': self.account.id,
            }
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['transaction']['amount'], '150.00')
        self.assertEqual(response.data['transaction']['description'], 'New test transaction')
    
    # def test_delete_supplier_transaction(self):
    #     kwargs={'supplier_slug': self.supplier.slug, 'pk': self.supplier_transaction.id}
    #     url = reverse('supplier-transaction-detail', kwargs=kwargs)
    #     response = self.client.delete(url)
    #     self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
    #     self.assertFalse(SupplierTransaction.objects.filter(id=self.supplier_transaction.id).exists())
    
    # def test_list_supplier_transactions(self):
    #     kwargs={'supplier_slug': self.supplier.slug}
    #     url = reverse('supplier-transaction-list', kwargs=kwargs)
    #     response = self.client.get(url)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(len(response.data['results']), 1)
    #     self.assertEqual(response.data['results'][0]['amount'], '100.00')
    #     self.assertEqual(response.data['results'][0]['description'], 'Test transaction')
    
    # def test_get_supplier_transaction(self):
    #     kwargs={'supplier_slug': self.supplier.slug, 'pk': self.supplier_transaction.id}
    #     url = reverse('supplier-transaction-detail', kwargs=kwargs)
    #     response = self.client.get(url)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(response.data['amount'], '100.00')
    #     self.assertEqual(response.data['description'], 'Test transaction')
