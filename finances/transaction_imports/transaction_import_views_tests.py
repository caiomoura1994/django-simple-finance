from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from django.urls import reverse
from rest_framework import status
from finances.models import TransactionImport
import tempfile
import os

class TransactionImportViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create a test file
        self.test_file = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        self.test_file.write(b'test content')
        self.test_file.close()
        
        # Create a test import
        self.import_obj = TransactionImport.objects.create(
            source=TransactionImport.ImportSource.EXCEL,
            file=self.test_file.name,
            owner=self.user
        )

    def tearDown(self):
        # Clean up the test file
        if os.path.exists(self.test_file.name):
            os.unlink(self.test_file.name)
        TransactionImport.objects.all().delete()
        User.objects.all().delete()

    def test_list_imports(self):
        url = reverse('transactionimport-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_import(self):
        url = reverse('transactionimport-list')
        with open(self.test_file.name, 'rb') as file:
            data = {
                'source': TransactionImport.ImportSource.EXCEL,
                'file': file
            }
            response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['source'], TransactionImport.ImportSource.EXCEL)
        self.assertEqual(response.data['status'], TransactionImport.ImportStatus.PENDING)

    def test_process_import(self):
        url = reverse('transactionimport-process', args=[self.import_obj.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('task_id' in response.data)

    def test_download_template(self):
        url = reverse('transactionimport-download-template')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ) 