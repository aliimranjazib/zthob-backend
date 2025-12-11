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


# ============================================================================
# ADDRESS API TESTS
# ============================================================================

class CustomerAddressAPITest(TestCase):
    """Comprehensive test cases for Customer Address APIs."""
    
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
    
    # ========== CREATE ADDRESS TESTS ==========
    
    def test_create_address_requires_authentication(self):
        """Test that creating address requires authentication."""
        url = '/api/customers/addresses/'
        data = {
            'address': 'ساهيوال، باكستان',
            'latitude': '30.668200',
            'longitude': '73.111356',
            'address_tag': 'home',
            'is_default': True
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_create_address_success(self):
        """Test successful address creation."""
        self.client.force_authenticate(user=self.customer)
        url = '/api/customers/addresses/'
        data = {
            'address': 'ساهيوال، باكستان',
            'latitude': '30.668200',
            'longitude': '73.111356',
            'address_tag': 'home',
            'is_default': True
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['address'], 'ساهيوال، باكستان')
        self.assertEqual(response.data['data']['address_tag'], 'home')
        self.assertTrue(response.data['data']['is_default'])
        
        # Verify address was created in database
        from apps.customers.models import Address
        address = Address.objects.get(user=self.customer)
        self.assertEqual(address.address, 'ساهيوال، باكستان')
        self.assertEqual(str(address.latitude), '30.668200')
        self.assertEqual(str(address.longitude), '73.111356')
    
    def test_create_address_without_address_field(self):
        """Test address creation fails without address field."""
        self.client.force_authenticate(user=self.customer)
        url = '/api/customers/addresses/'
        data = {
            'latitude': '30.668200',
            'longitude': '73.111356',
            'address_tag': 'home'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('address', response.data['errors'])
    
    def test_create_address_with_invalid_address_tag(self):
        """Test address creation fails with invalid address_tag."""
        self.client.force_authenticate(user=self.customer)
        url = '/api/customers/addresses/'
        data = {
            'address': 'Test Address',
            'address_tag': 'invalid_tag'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
    
    def test_create_address_sets_default(self):
        """Test that creating address with is_default=True sets it as default."""
        self.client.force_authenticate(user=self.customer)
        url = '/api/customers/addresses/'
        
        # Create first address as default
        data1 = {
            'address': 'Address 1',
            'is_default': True
        }
        response1 = self.client.post(url, data1)
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Create second address as default
        data2 = {
            'address': 'Address 2',
            'is_default': True
        }
        response2 = self.client.post(url, data2)
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        
        # Verify only second address is default
        from apps.customers.models import Address
        addresses = Address.objects.filter(user=self.customer)
        self.assertEqual(addresses.filter(is_default=True).count(), 1)
        self.assertEqual(addresses.filter(is_default=True).first().address, 'Address 2')
    
    # ========== LIST ADDRESSES TESTS ==========
    
    def test_list_addresses_requires_authentication(self):
        """Test that listing addresses requires authentication."""
        url = '/api/customers/addresses/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_list_addresses_empty(self):
        """Test listing addresses when user has no addresses."""
        self.client.force_authenticate(user=self.customer)
        url = '/api/customers/addresses/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 0)
    
    def test_list_addresses_with_addresses(self):
        """Test listing addresses when user has addresses."""
        from apps.customers.models import Address
        
        # Create addresses
        Address.objects.create(
            user=self.customer,
            address='Address 1',
            street='Address 1',
            city='Riyadh',
            country='Saudi Arabia',
            address_tag='home'
        )
        Address.objects.create(
            user=self.customer,
            address='Address 2',
            street='Address 2',
            city='Riyadh',
            country='Saudi Arabia',
            address_tag='office'
        )
        
        self.client.force_authenticate(user=self.customer)
        url = '/api/customers/addresses/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 2)
        self.assertEqual(response.data['data'][0]['address'], 'Address 1')
        self.assertEqual(response.data['data'][1]['address'], 'Address 2')
    
    def test_list_addresses_only_user_addresses(self):
        """Test that users only see their own addresses."""
        from apps.customers.models import Address
        
        # Create address for customer
        Address.objects.create(
            user=self.customer,
            address='Customer Address',
            street='Customer Address',
            city='Riyadh',
            country='Saudi Arabia'
        )
        
        # Create address for other customer
        Address.objects.create(
            user=self.other_customer,
            address='Other Address',
            street='Other Address',
            city='Riyadh',
            country='Saudi Arabia'
        )
        
        self.client.force_authenticate(user=self.customer)
        url = '/api/customers/addresses/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['address'], 'Customer Address')
    
    # ========== GET ADDRESS DETAIL TESTS ==========
    
    def test_get_address_detail_requires_authentication(self):
        """Test that getting address detail requires authentication."""
        url = '/api/customers/addresses/1/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_get_address_detail_success(self):
        """Test successful address detail retrieval."""
        from apps.customers.models import Address
        
        address = Address.objects.create(
            user=self.customer,
            address='Test Address',
            street='Test Address',
            city='Riyadh',
            country='Saudi Arabia',
            latitude='24.7136',
            longitude='46.6753',
            address_tag='home'
        )
        
        self.client.force_authenticate(user=self.customer)
        url = f'/api/customers/addresses/{address.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['address'], 'Test Address')
        self.assertEqual(response.data['data']['address_tag'], 'home')
    
    def test_get_address_detail_not_found(self):
        """Test getting non-existent address."""
        self.client.force_authenticate(user=self.customer)
        url = '/api/customers/addresses/99999/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data['success'])
    
    def test_get_address_detail_other_user_address(self):
        """Test that users cannot access other users' addresses."""
        from apps.customers.models import Address
        
        address = Address.objects.create(
            user=self.other_customer,
            address='Other Address',
            street='Other Address',
            city='Riyadh',
            country='Saudi Arabia'
        )
        
        self.client.force_authenticate(user=self.customer)
        url = f'/api/customers/addresses/{address.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    # ========== ADDRESS RESPONSE STRUCTURE TESTS ==========
    
    def test_address_response_structure(self):
        """Test that address response has correct structure."""
        from apps.customers.models import Address
        
        address = Address.objects.create(
            user=self.customer,
            address='ساهيوال، باكستان',
            street='ساهيوال، باكستان',
            city='Riyadh',
            country='Saudi Arabia',
            latitude='30.668200',
            longitude='73.111356',
            extra_info='Test info',
            is_default=True,
            address_tag='home'
        )
        
        self.client.force_authenticate(user=self.customer)
        url = f'/api/customers/addresses/{address.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        
        # Verify all required fields are present
        self.assertIn('id', data)
        self.assertIn('latitude', data)
        self.assertIn('longitude', data)
        self.assertIn('address', data)
        self.assertIn('extra_info', data)
        self.assertIn('is_default', data)
        self.assertIn('address_tag', data)
        
        # Verify values
        self.assertEqual(data['address'], 'ساهيوال، باكستان')
        self.assertEqual(data['address_tag'], 'home')
        self.assertTrue(data['is_default'])


class TailorAddressAPITest(TestCase):
    """Comprehensive test cases for Tailor Address APIs."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create tailor user
        self.tailor = User.objects.create_user(
            username='testtailor',
            email='tailor@example.com',
            password='testpass123',
            role='TAILOR'
        )
        
        # Create customer user (should not access tailor endpoints)
        self.customer = User.objects.create_user(
            username='testcustomer',
            email='customer@example.com',
            password='testpass123',
            role='USER'
        )
    
    # ========== GET TAILOR ADDRESS TESTS ==========
    
    def test_get_tailor_address_requires_authentication(self):
        """Test that getting tailor address requires authentication."""
        url = '/api/tailors/address/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_get_tailor_address_requires_tailor_role(self):
        """Test that only tailors can access tailor address endpoint."""
        self.client.force_authenticate(user=self.customer)
        url = '/api/tailors/address/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_get_tailor_address_not_found(self):
        """Test getting tailor address when none exists."""
        self.client.force_authenticate(user=self.tailor)
        url = '/api/tailors/address/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data['success'])
    
    def test_get_tailor_address_success(self):
        """Test successful tailor address retrieval."""
        from apps.customers.models import Address
        
        address = Address.objects.create(
            user=self.tailor,
            address='Tailor Shop Address',
            street='Tailor Shop Address',
            city='Riyadh',
            country='Saudi Arabia',
            address_tag='work',
            is_default=True
        )
        
        self.client.force_authenticate(user=self.tailor)
        url = '/api/tailors/address/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['address'], 'Tailor Shop Address')
        self.assertEqual(response.data['data']['address_tag'], 'work')
    
    # ========== CREATE TAILOR ADDRESS TESTS ==========
    
    def test_create_tailor_address_success(self):
        """Test successful tailor address creation."""
        self.client.force_authenticate(user=self.tailor)
        url = '/api/tailors/address/'
        data = {
            'address': 'New Tailor Address',
            'latitude': '24.7136',
            'longitude': '46.6753',
            'address_tag': 'work',
            'is_default': True
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['address'], 'New Tailor Address')
        
        # Verify old addresses were deleted (tailor can only have one address)
        from apps.customers.models import Address
        addresses = Address.objects.filter(user=self.tailor)
        self.assertEqual(addresses.count(), 1)
    
    def test_create_tailor_address_replaces_existing(self):
        """Test that creating new tailor address replaces existing one."""
        from apps.customers.models import Address
        
        # Create existing address
        old_address = Address.objects.create(
            user=self.tailor,
            address='Old Address',
            street='Old Address',
            city='Riyadh',
            country='Saudi Arabia',
            address_tag='work'
        )
        old_address_id = old_address.id
        
        # Create new address
        self.client.force_authenticate(user=self.tailor)
        url = '/api/tailors/address/'
        data = {
            'address': 'New Address',
            'address_tag': 'work'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify old address was deleted
        from apps.customers.models import Address
        self.assertFalse(Address.objects.filter(id=old_address_id).exists())
        self.assertEqual(Address.objects.filter(user=self.tailor).count(), 1)
        self.assertEqual(Address.objects.filter(user=self.tailor).first().address, 'New Address')
    
    # ========== UPDATE TAILOR ADDRESS TESTS ==========
    
    def test_update_tailor_address_success(self):
        """Test successful tailor address update."""
        from apps.customers.models import Address
        
        address = Address.objects.create(
            user=self.tailor,
            address='Original Address',
            street='Original Address',
            city='Riyadh',
            country='Saudi Arabia',
            address_tag='work'
        )
        
        self.client.force_authenticate(user=self.tailor)
        url = '/api/tailors/address/'
        data = {
            'address': 'Updated Address',
            'address_tag': 'work'
        }
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['address'], 'Updated Address')
        
        # Verify address was updated
        address.refresh_from_db()
        self.assertEqual(address.address, 'Updated Address')
    
    def test_update_tailor_address_not_found(self):
        """Test updating tailor address when none exists."""
        self.client.force_authenticate(user=self.tailor)
        url = '/api/tailors/address/'
        data = {
            'address': 'Updated Address'
        }
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data['success'])
    
    # ========== DELETE TAILOR ADDRESS TESTS ==========
    
    def test_delete_tailor_address_success(self):
        """Test successful tailor address deletion."""
        from apps.customers.models import Address
        
        Address.objects.create(
            user=self.tailor,
            address='Address to Delete',
            street='Address to Delete',
            city='Riyadh',
            country='Saudi Arabia'
        )
        
        self.client.force_authenticate(user=self.tailor)
        url = '/api/tailors/address/'
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify address was deleted
        self.assertEqual(Address.objects.filter(user=self.tailor).count(), 0)
    
    def test_delete_tailor_address_not_found(self):
        """Test deleting tailor address when none exists."""
        self.client.force_authenticate(user=self.tailor)
        url = '/api/tailors/address/'
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data['success'])


class RiderAddressAPITest(TestCase):
    """Comprehensive test cases for Rider Address APIs (in order details)."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create users
        self.customer = User.objects.create_user(
            username='testcustomer',
            email='customer@example.com',
            password='testpass123',
            role='USER'
        )
        
        self.tailor = User.objects.create_user(
            username='testtailor',
            email='tailor@example.com',
            password='testpass123',
            role='TAILOR'
        )
        
        self.rider = User.objects.create_user(
            username='testrider',
            email='rider@example.com',
            password='testpass123',
            role='RIDER'
        )
        
        # Create tailor profile
        from apps.tailors.models import TailorProfile
        self.tailor_profile = TailorProfile.objects.create(
            user=self.tailor,
            shop_name='Test Shop',
            shop_status=True
        )
        
        # Create fabric and category
        from apps.tailors.models import Fabric, FabricCategory
        self.category = FabricCategory.objects.create(name='Test', slug='test')
        self.fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            name='Test Fabric',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
            category=self.category
        )
    
    def test_rider_order_detail_includes_address(self):
        """Test that rider order detail includes address in correct format."""
        from apps.customers.models import Address
        from apps.orders.models import Order, OrderItem
        
        # Create address
        address = Address.objects.create(
            user=self.customer,
            address='ساهيوال، باكستان',
            street='ساهيوال، باكستان',
            city='Riyadh',
            country='Saudi Arabia',
            latitude='30.668200',
            longitude='73.111356',
            address_tag='home',
            is_default=True
        )
        
        # Create order
        order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
            rider=self.rider,
            delivery_address=address,
            status='accepted',
            payment_status='paid',
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )
        OrderItem.objects.create(
            order=order,
            fabric=self.fabric,
            quantity=1,
            unit_price=Decimal('100.00')
        )
        
        self.client.force_authenticate(user=self.rider)
        url = f'/api/riders/orders/{order.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify address structure matches customer format
        delivery_address = response.data['data']['delivery_address']
        self.assertIsNotNone(delivery_address)
        self.assertIn('id', delivery_address)
        self.assertIn('latitude', delivery_address)
        self.assertIn('longitude', delivery_address)
        self.assertIn('address', delivery_address)
        self.assertIn('extra_info', delivery_address)
        self.assertIn('is_default', delivery_address)
        self.assertIn('address_tag', delivery_address)
        
        # Verify address value
        self.assertEqual(delivery_address['address'], 'ساهيوال، باكستان')
        self.assertEqual(delivery_address['address_tag'], 'home')
        self.assertTrue(delivery_address['is_default'])
    
    def test_rider_order_list_includes_address(self):
        """Test that rider order list includes address in correct format."""
        from apps.customers.models import Address
        from apps.orders.models import Order, OrderItem
        
        # Create address
        address = Address.objects.create(
            user=self.customer,
            address='Test Address',
            street='Test Address',
            city='Riyadh',
            country='Saudi Arabia',
            latitude='24.7136',
            longitude='46.6753',
            address_tag='home'
        )
        
        # Create order
        order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
            delivery_address=address,
            status='accepted',
            payment_status='paid',
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )
        OrderItem.objects.create(
            order=order,
            fabric=self.fabric,
            quantity=1,
            unit_price=Decimal('100.00')
        )
        
        self.client.force_authenticate(user=self.rider)
        url = '/api/riders/orders/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify address structure
        if len(response.data['data']) > 0:
            order_data = response.data['data'][0]
            self.assertIn('delivery_address', order_data)
            
            delivery_address = order_data['delivery_address']
            self.assertIn('id', delivery_address)
            self.assertIn('address', delivery_address)
            self.assertEqual(delivery_address['address'], 'Test Address')
    
    def test_rider_order_detail_address_null_when_no_address(self):
        """Test that rider order detail returns null when order has no address."""
        from apps.orders.models import Order, OrderItem
        
        # Create order without address
        order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor,
            rider=self.rider,
            delivery_address=None,
            status='accepted',
            payment_status='paid',
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )
        OrderItem.objects.create(
            order=order,
            fabric=self.fabric,
            quantity=1,
            unit_price=Decimal('100.00')
        )
        
        self.client.force_authenticate(user=self.rider)
        url = f'/api/riders/orders/{order.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['data']['delivery_address'])
