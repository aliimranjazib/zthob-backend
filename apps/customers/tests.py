from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal

from apps.customers.models import FabricFavorite
from apps.tailors.models import Fabric, FabricCategory, TailorProfile

User = get_user_model()


class FabricFavoriteModelTest(TestCase):
    """Test cases for FabricFavorite model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='USER'
        )
        
        self.tailor_user = User.objects.create_user(
            username='testtailor',
            email='tailor@example.com',
            password='testpass123',
            role='TAILOR'
        )
        
        self.tailor_profile, _ = TailorProfile.objects.get_or_create(
            user=self.tailor_user,
            defaults={'shop_name': 'Test Tailor Shop'}
        )
        
        self.fabric_category = FabricCategory.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            name='Test Fabric',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
            category=self.fabric_category
        )
    
    def test_create_fabric_favorite(self):
        """Test creating a fabric favorite."""
        favorite = FabricFavorite.objects.create(
            user=self.user,
            fabric=self.fabric
        )
        
        self.assertEqual(favorite.user, self.user)
        self.assertEqual(favorite.fabric, self.fabric)
        self.assertIsNotNone(favorite.created_at)
    
    def test_unique_together_constraint(self):
        """Test that a user cannot favorite the same fabric twice."""
        FabricFavorite.objects.create(
            user=self.user,
            fabric=self.fabric
        )
        
        # Try to create duplicate
        with self.assertRaises(Exception):  # IntegrityError
            FabricFavorite.objects.create(
                user=self.user,
                fabric=self.fabric
            )
    
    def test_fabric_favorite_str(self):
        """Test string representation of FabricFavorite."""
        favorite = FabricFavorite.objects.create(
            user=self.user,
            fabric=self.fabric
        )
        
        expected_str = f"{self.user.username} favorited {self.fabric.name}"
        self.assertEqual(str(favorite), expected_str)
    
    def test_fabric_favorite_ordering(self):
        """Test that favorites are ordered by created_at descending."""
        # Create multiple favorites
        favorite1 = FabricFavorite.objects.create(
            user=self.user,
            fabric=self.fabric
        )
        
        # Create another fabric
        fabric2 = Fabric.objects.create(
            tailor=self.tailor_profile,
            name='Test Fabric 2',
            price=Decimal('200.00'),
            stock=5,
            is_active=True,
            category=self.fabric_category
        )
        
        favorite2 = FabricFavorite.objects.create(
            user=self.user,
            fabric=fabric2
        )
        
        # Get all favorites
        favorites = list(FabricFavorite.objects.filter(user=self.user))
        
        # Most recent should be first
        self.assertEqual(favorites[0], favorite2)
        self.assertEqual(favorites[1], favorite1)
    
    def test_cascade_delete_on_fabric_deletion(self):
        """Test that favorites are deleted when fabric is deleted."""
        favorite = FabricFavorite.objects.create(
            user=self.user,
            fabric=self.fabric
        )
        
        # Delete fabric
        self.fabric.delete()
        
        # Favorite should be deleted
        self.assertFalse(FabricFavorite.objects.filter(id=favorite.id).exists())
    
    def test_cascade_delete_on_user_deletion(self):
        """Test that favorites are deleted when user is deleted."""
        favorite = FabricFavorite.objects.create(
            user=self.user,
            fabric=self.fabric
        )
        
        # Delete user
        self.user.delete()
        
        # Favorite should be deleted
        self.assertFalse(FabricFavorite.objects.filter(id=favorite.id).exists())


class FabricFavoriteAPITest(TestCase):
    """Test cases for Fabric Favorite API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create customer user
        self.customer = User.objects.create_user(
            username='testcustomer',
            email='customer@example.com',
            password='testpass123',
            role='USER'
        )
        
        # Create another customer user
        self.other_customer = User.objects.create_user(
            username='othercustomer',
            email='other@example.com',
            password='testpass123',
            role='USER'
        )
        
        # Create tailor user
        self.tailor_user = User.objects.create_user(
            username='testtailor',
            email='tailor@example.com',
            password='testpass123',
            role='TAILOR'
        )
        
        self.tailor_profile, _ = TailorProfile.objects.get_or_create(
            user=self.tailor_user,
            defaults={'shop_name': 'Test Tailor Shop'}
        )
        
        # Create fabric category
        self.fabric_category = FabricCategory.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        # Create active fabric
        self.fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            name='Test Fabric',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
            category=self.fabric_category
        )
        
        # Create inactive fabric
        self.inactive_fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            name='Inactive Fabric',
            price=Decimal('50.00'),
            stock=5,
            is_active=False,
            category=self.fabric_category
        )
    
    def test_toggle_favorite_requires_authentication(self):
        """Test that toggle favorite endpoint requires authentication."""
        url = f'/api/customers/fabrics/{self.fabric.id}/favorite/'
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_toggle_favorite_add_favorite(self):
        """Test adding a fabric to favorites."""
        self.client.force_authenticate(user=self.customer)
        url = f'/api/customers/fabrics/{self.fabric.id}/favorite/'
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertTrue(response.data['data']['is_favorited'])
        self.assertEqual(response.data['data']['fabric_id'], self.fabric.id)
        self.assertIsNotNone(response.data['data']['favorited_at'])
        
        # Verify favorite was created
        self.assertTrue(
            FabricFavorite.objects.filter(
                user=self.customer,
                fabric=self.fabric
            ).exists()
        )
    
    def test_toggle_favorite_remove_favorite(self):
        """Test removing a fabric from favorites."""
        # First add to favorites
        FabricFavorite.objects.create(
            user=self.customer,
            fabric=self.fabric
        )
        
        self.client.force_authenticate(user=self.customer)
        url = f'/api/customers/fabrics/{self.fabric.id}/favorite/'
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertFalse(response.data['data']['is_favorited'])
        self.assertEqual(response.data['data']['fabric_id'], self.fabric.id)
        self.assertIsNone(response.data['data']['favorited_at'])
        
        # Verify favorite was removed
        self.assertFalse(
            FabricFavorite.objects.filter(
                user=self.customer,
                fabric=self.fabric
            ).exists()
        )
    
    def test_toggle_favorite_fabric_not_found(self):
        """Test toggle favorite with non-existent fabric."""
        self.client.force_authenticate(user=self.customer)
        url = '/api/customers/fabrics/99999/favorite/'
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data['success'])
        self.assertIn('not found', response.data['message'].lower())
    
    def test_toggle_favorite_inactive_fabric(self):
        """Test that inactive fabrics cannot be favorited."""
        self.client.force_authenticate(user=self.customer)
        url = f'/api/customers/fabrics/{self.inactive_fabric.id}/favorite/'
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data['success'])
    
    def test_list_favorites_requires_authentication(self):
        """Test that list favorites endpoint requires authentication."""
        url = '/api/customers/favorites/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_list_favorites_empty(self):
        """Test listing favorites when user has no favorites."""
        self.client.force_authenticate(user=self.customer)
        url = '/api/customers/favorites/'
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 0)
    
    def test_list_favorites_with_favorites(self):
        """Test listing favorites when user has favorites."""
        # Create multiple favorites
        FabricFavorite.objects.create(
            user=self.customer,
            fabric=self.fabric
        )
        
        # Create another fabric and favorite it
        fabric2 = Fabric.objects.create(
            tailor=self.tailor_profile,
            name='Test Fabric 2',
            price=Decimal('200.00'),
            stock=5,
            is_active=True,
            category=self.fabric_category
        )
        
        FabricFavorite.objects.create(
            user=self.customer,
            fabric=fabric2
        )
        
        self.client.force_authenticate(user=self.customer)
        url = '/api/customers/favorites/'
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 2)
        
        # Verify fabric data is included
        self.assertIn('fabric', response.data['data'][0])
        self.assertIn('created_at', response.data['data'][0])
    
    def test_list_favorites_only_user_favorites(self):
        """Test that users only see their own favorites."""
        # Create favorite for customer
        FabricFavorite.objects.create(
            user=self.customer,
            fabric=self.fabric
        )
        
        # Create favorite for other customer
        FabricFavorite.objects.create(
            user=self.other_customer,
            fabric=self.fabric
        )
        
        self.client.force_authenticate(user=self.customer)
        url = '/api/customers/favorites/'
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(
            response.data['data'][0]['fabric']['id'],
            self.fabric.id
        )
    
    def test_list_favorites_ordered_by_created_at(self):
        """Test that favorites are ordered by created_at descending."""
        # Create first favorite
        favorite1 = FabricFavorite.objects.create(
            user=self.customer,
            fabric=self.fabric
        )
        
        # Create second fabric and favorite
        fabric2 = Fabric.objects.create(
            tailor=self.tailor_profile,
            name='Test Fabric 2',
            price=Decimal('200.00'),
            stock=5,
            is_active=True,
            category=self.fabric_category
        )
        
        favorite2 = FabricFavorite.objects.create(
            user=self.customer,
            fabric=fabric2
        )
        
        self.client.force_authenticate(user=self.customer)
        url = '/api/customers/favorites/'
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Most recent should be first
        self.assertEqual(
            response.data['data'][0]['fabric']['id'],
            fabric2.id
        )
        self.assertEqual(
            response.data['data'][1]['fabric']['id'],
            self.fabric.id
        )


class FabricCatalogSerializerFavoriteTest(TestCase):
    """Test cases for FabricCatalogSerializer with favorite fields."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create customer user
        self.customer = User.objects.create_user(
            username='testcustomer',
            email='customer@example.com',
            password='testpass123',
            role='USER'
        )
        
        # Create tailor user
        self.tailor_user = User.objects.create_user(
            username='testtailor',
            email='tailor@example.com',
            password='testpass123',
            role='TAILOR'
        )
        
        self.tailor_profile, _ = TailorProfile.objects.get_or_create(
            user=self.tailor_user,
            defaults={'shop_name': 'Test Tailor Shop'}
        )
        
        # Create fabric category
        self.fabric_category = FabricCategory.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        # Create fabric
        self.fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            name='Test Fabric',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
            category=self.fabric_category
        )
    
    def test_fabric_catalog_includes_is_favorited_for_authenticated_user(self):
        """Test that is_favorited is included for authenticated users."""
        # Add to favorites
        FabricFavorite.objects.create(
            user=self.customer,
            fabric=self.fabric
        )
        
        self.client.force_authenticate(user=self.customer)
        url = '/api/customers/allfabrics/'
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        fabric_data = response.data['data'][0]
        
        self.assertIn('is_favorited', fabric_data)
        self.assertTrue(fabric_data['is_favorited'])
        self.assertIn('favorite_count', fabric_data)
    
    def test_fabric_catalog_is_favorited_false_when_not_favorited(self):
        """Test that is_favorited is False when fabric is not favorited."""
        self.client.force_authenticate(user=self.customer)
        url = '/api/customers/allfabrics/'
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        fabric_data = response.data['data'][0]
        
        self.assertIn('is_favorited', fabric_data)
        self.assertFalse(fabric_data['is_favorited'])
    
    def test_fabric_catalog_is_favorited_false_for_unauthenticated_user(self):
        """Test that is_favorited is False for unauthenticated users."""
        # Add to favorites
        FabricFavorite.objects.create(
            user=self.customer,
            fabric=self.fabric
        )
        
        url = '/api/customers/allfabrics/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        fabric_data = response.data['data'][0]
        
        self.assertIn('is_favorited', fabric_data)
        self.assertFalse(fabric_data['is_favorited'])
    
    def test_fabric_catalog_favorite_count(self):
        """Test that favorite_count is accurate."""
        # Add multiple favorites from different users
        customer2 = User.objects.create_user(
            username='customer2',
            email='customer2@example.com',
            password='testpass123',
            role='USER'
        )
        
        FabricFavorite.objects.create(
            user=self.customer,
            fabric=self.fabric
        )
        
        FabricFavorite.objects.create(
            user=customer2,
            fabric=self.fabric
        )
        
        self.client.force_authenticate(user=self.customer)
        url = '/api/customers/allfabrics/'
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        fabric_data = response.data['data'][0]
        
        self.assertEqual(fabric_data['favorite_count'], 2)
    
    def test_fabric_catalog_favorite_count_zero(self):
        """Test that favorite_count is 0 when no favorites exist."""
        self.client.force_authenticate(user=self.customer)
        url = '/api/customers/allfabrics/'
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        fabric_data = response.data['data'][0]
        
        self.assertEqual(fabric_data['favorite_count'], 0)
