from rest_framework.test import APIClient
from rest_framework.test import APITestCase
from finances.models import Category
from django.contrib.auth.models import User
from django.urls import reverse


class CategoryViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="testpassword")
        self.client.force_authenticate(user=self.user)
        self.category = Category.objects.create(name="Test Category", owner=self.user, slug="test-category")
    
    def tearDown(self):
        Category.objects.all().delete()
        User.objects.all().delete()

    def test_create_category(self):
        response = self.client.post(reverse('category-list'), data={'name': 'Test Category2'})
        assert response.status_code == 201
        assert Category.objects.count() == 2
        assert Category.objects.get(slug="test-category2").name == 'Test Category2'
        assert Category.objects.get(slug="test-category2").owner == self.user

    def test_list_categories(self):
        response = self.client.get(reverse('category-list'))
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]['name'] == 'Test Category'
        assert response.json()[0]['slug'] == 'test-category'

    def test_update_category(self):
        response = self.client.put(reverse('category-detail', args=[self.category.slug]), data={'name': 'Updated Category'})
        assert response.status_code == 200
        assert Category.objects.count() == 1
        assert Category.objects.get(slug="updated-category").name == 'Updated Category'

    def test_delete_category(self):
        response = self.client.delete(reverse('category-detail', args=[self.category.slug]))
        assert response.status_code == 204
        assert Category.objects.count() == 0

    def test_get_category(self):
        response = self.client.get(reverse('category-detail', args=[self.category.slug]))
        assert response.status_code == 200
        assert response.json()['name'] == 'Test Category'
        assert response.json()['slug'] == 'test-category'

