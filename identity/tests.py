from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from unittest import skip

class AuthenticationTests(TestCase):
    def tearDown(self):
        User.objects.all().delete()

    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('identity:register')
        self.login_url = reverse('identity:login')
        self.profile_url = reverse('identity:profile')
        self.change_password_url = reverse('identity:change_password')
        self.logout_url = reverse('identity:logout')

        # Create a test user
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

        # Create token for test user
        self.token = Token.objects.create(user=self.test_user)

        # Valid registration data
        self.valid_register_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpass123!',
            'password2': 'newpass123!',
            'first_name': 'New',
            'last_name': 'User'
        }

    def test_user_registration_success(self):
        """Test successful user registration"""
        response = self.client.post(self.register_url, self.valid_register_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('token', response.data)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_user_registration_invalid_data(self):
        """Test registration with invalid data"""
        # Test with mismatched passwords
        invalid_data = self.valid_register_data.copy()
        invalid_data['password2'] = 'wrongpass123!'
        response = self.client.post(self.register_url, invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

        # Test with existing username
        invalid_data = self.valid_register_data.copy()
        invalid_data['username'] = 'testuser'
        response = self.client.post(self.register_url, invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

        # Test with existing email
        invalid_data = self.valid_register_data.copy()
        invalid_data['email'] = 'test@example.com'
        response = self.client.post(self.register_url, invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_user_login_success(self):
        """Test successful user login"""
        login_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        login_data = {
            'username': 'testuser',
            'password': 'wrongpass123'
        }
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_profile_access(self):
        """Test profile access and update"""
        # Get profile without authentication
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Login and get authentication token
        login_response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpass123'
        })
        token = login_response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

        # Get profile with authentication
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')

        # Update profile
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name'
        }
        response = self.client.put(self.profile_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Updated')
        self.assertEqual(response.data['last_name'], 'Name')

    def test_change_password(self):
        """Test password change functionality"""
        # Login first
        login_response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpass123'
        })
        token = login_response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

        # Try changing password
        change_password_data = {
            'old_password': 'testpass123',
            'new_password': 'newtestpass123!'
        }
        response = self.client.put(self.change_password_url, change_password_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

        # Verify old password no longer works
        self.client.credentials()  # Clear credentials
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Verify new password works
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'newtestpass123!'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout(self):
        """Test logout functionality"""
        # Login first
        login_response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpass123'
        })
        token = login_response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

        # Try logout
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify token is deleted by trying to access protected endpoint
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

