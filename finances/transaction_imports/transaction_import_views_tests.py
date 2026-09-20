import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from django.urls import reverse
from rest_framework import status
from finances.models import TransactionImport
from django.conf import settings
import pandas as pd
import tempfile
import os
import shutil

@pytest.mark.django_db
class TransactionImportViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Ensure test media directory exists
        self.test_media_dir = os.path.join(settings.MEDIA_ROOT, 'test_files')
        os.makedirs(self.test_media_dir, exist_ok=True)
        
        # Create a test Excel file with proper content
        self.test_file_name = os.path.join(self.test_media_dir, 'test_import.xlsx')
        df = pd.DataFrame({
            'date': ['2024-03-26'],
            'description': ['Test Transaction'],
            'amount': [100.00],
            'kind_of_transaction': ['EXPENSE'],
            'category': ['Test Category'],
            'account': ['Test Account']
        })
        df.to_excel(self.test_file_name, index=False, engine='openpyxl')
        
        # Create a test import
        self.import_obj = TransactionImport.objects.create(
            source=TransactionImport.ImportSource.EXCEL,
            file=self.test_file_name,
            owner=self.user
        )

    def tearDown(self):
        # Clean up test files
        if os.path.exists(self.test_media_dir):
            shutil.rmtree(self.test_media_dir)
        TransactionImport.objects.all().delete()
        User.objects.all().delete()

    def test_list_imports(self):
        url = reverse('transactionimport-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 1)

    def test_create_import(self):
        url = reverse('transactionimport-list')
        with open(self.test_file_name, 'rb') as file:
            data = {
                'source': TransactionImport.ImportSource.EXCEL,
                'file': file
            }
            response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['source'], TransactionImport.ImportSource.EXCEL)
        self.assertEqual(response.data['status'], TransactionImport.ImportStatus.PENDING)

    @pytest.mark.celery
    def test_process_import(self):
        url = reverse('transactionimport-process', args=[self.import_obj.id])
        response = self.client.post(url)
        
        # Assert the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('task_id' in response.data)
        
        # Check if import status was updated
        self.import_obj.refresh_from_db()
        self.assertEqual(self.import_obj.status, TransactionImport.ImportStatus.PROCESSING.value)
        self.assertTrue(self.import_obj.celery_task_id)

    def test_download_template(self):
        url = reverse('transactionimport-download-template')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ) 