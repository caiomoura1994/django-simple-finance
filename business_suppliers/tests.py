from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from business_suppliers.models import Supplier
from django.urls import reverse
from rest_framework import status

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
