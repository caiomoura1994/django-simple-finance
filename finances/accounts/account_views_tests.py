from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from finances.models import Account
from django.urls import reverse
from rest_framework import status
from decimal import Decimal
class AccountViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.account = Account.objects.create(
            name='Test Account',
            slug='test-account',
            balance=1000.00,
            owner=self.user
        )
    def tearDown(self):
        Account.objects.all().delete()
        User.objects.all().delete()

    def test_list_accounts(self):
        url = reverse('account-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 1)

    def test_create_account(self):
        url = reverse('account-list')
        data = {
            'name': 'New Account',
            'description': 'Test description'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Account')
        self.assertEqual(response.data['slug'], 'new-account')
        self.assertEqual(response.data['balance'], '0.00')

    def test_retrieve_account(self):
        url = reverse('account-detail', kwargs={'slug': self.account.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Account')

    def test_update_account(self):
        url = reverse('account-detail', kwargs={'slug': self.account.slug})
        data = {
            'name': 'Updated Account',
            'description': 'Updated description'
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Account')
        self.assertEqual(response.data['slug'], 'updated-account')

    def test_delete_account(self):
        url = reverse('account-detail', kwargs={'slug': self.account.slug})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Account.objects.filter(slug=self.account.slug).exists())

    def test_adjust_balance(self):
        url = reverse('account-adjust-balance', kwargs={'slug': self.account.slug})
        data = {'amount': '2000.00'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(response.data['new_balance'], Decimal('2000.00'))
        
        # Test invalid amount
        data = {'amount': 'invalid'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) 