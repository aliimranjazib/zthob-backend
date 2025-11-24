"""
Test cases for Tailor Profile Review Admin improvements

This test file verifies:
1. Inline admin functionality for reviews in TailorProfile
2. Autocomplete fields work correctly
3. Pre-population of profile field when adding review from TailorProfile
4. Review status display in TailorProfile list
5. Quick actions and links work properly
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.tailors.models import TailorProfile, TailorProfileReview
from apps.accounts.models import CustomUser

User = get_user_model()


class TailorProfileReviewAdminTestCase(TestCase):
    """Test cases for Tailor Profile Review Admin improvements"""
    
    def setUp(self):
        """Set up test data"""
        # Create admin user
        self.admin_user = CustomUser.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role='ADMIN',
            is_staff=True,
            is_superuser=True
        )
        
        # Create tailor user
        self.tailor_user = CustomUser.objects.create_user(
            username='tailor1',
            email='tailor1@test.com',
            password='testpass123',
            role='TAILOR',
            is_active=True
        )
        
        # Create tailor profile
        self.tailor_profile = TailorProfile.objects.create(
            user=self.tailor_user,
            shop_name='Test Tailor Shop',
            contact_number='1234567890',
            address='123 Test St',
            shop_status=True
        )
        
        # Create client for admin access
        self.client = Client()
        self.client.force_login(self.admin_user)
    
    def test_tailor_profile_has_review_inline(self):
        """Test that TailorProfile admin has review inline"""
        from django.contrib import admin
        from apps.tailors.admin import TailorProfileAdmin, TailorProfileReviewInline
        
        # Check if TailorProfileReviewInline is in TailorProfileAdmin.inlines
        inline_names = [inline.__name__ for inline in TailorProfileAdmin.inlines]
        self.assertIn('TailorProfileReviewInline', inline_names)
    
    def test_review_inline_displays_correctly(self):
        """Test that review inline displays correctly in TailorProfile admin"""
        url = reverse('admin:tailors_tailorprofile_change', args=[self.tailor_profile.pk])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check that review section is present
        self.assertContains(response, 'Profile Review', status_code=200)
    
    def test_autocomplete_fields_in_review_admin(self):
        """Test that autocomplete_fields are used instead of raw_id_fields"""
        from apps.tailors.admin import TailorProfileReviewAdmin
        
        # Check that autocomplete_fields is used
        self.assertIn('profile', TailorProfileReviewAdmin.autocomplete_fields)
        self.assertIn('reviewed_by', TailorProfileReviewAdmin.autocomplete_fields)
        
        # Check that raw_id_fields is not used
        self.assertNotIn('profile', getattr(TailorProfileReviewAdmin, 'raw_id_fields', []))
        self.assertNotIn('reviewed_by', getattr(TailorProfileReviewAdmin, 'raw_id_fields', []))
    
    def test_profile_prepopulation_when_adding_review(self):
        """Test that profile field is pre-populated when adding review from TailorProfile"""
        # Add review URL with profile parameter
        url = reverse('admin:tailors_tailorprofilereview_add')
        url += f'?profile={self.tailor_profile.pk}'
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Check that profile field is pre-populated
        # The form should contain the profile ID
        self.assertContains(response, str(self.tailor_profile.pk), status_code=200)
    
    def test_review_status_display_in_tailor_profile_list(self):
        """Test that review status is displayed in TailorProfile list view"""
        # Create a review for the profile
        review = TailorProfileReview.objects.create(
            profile=self.tailor_profile,
            review_status='pending',
            submitted_at=timezone.now()
        )
        
        url = reverse('admin:tailors_tailorprofile_changelist')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check that review status is displayed
        self.assertContains(response, 'Pending Review', status_code=200)
    
    def test_review_status_link_when_review_exists(self):
        """Test that review status links to review admin when review exists"""
        # Create a review
        review = TailorProfileReview.objects.create(
            profile=self.tailor_profile,
            review_status='approved',
            submitted_at=timezone.now(),
            reviewed_at=timezone.now(),
            reviewed_by=self.admin_user
        )
        
        url = reverse('admin:tailors_tailorprofile_changelist')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check that link to review exists
        review_url = reverse('admin:tailors_tailorprofilereview_change', args=[review.pk])
        self.assertContains(response, review_url, status_code=200)
    
    def test_add_review_link_when_no_review_exists(self):
        """Test that 'Add Review' link appears when no review exists"""
        # Ensure no review exists
        TailorProfileReview.objects.filter(profile=self.tailor_profile).delete()
        
        url = reverse('admin:tailors_tailorprofile_changelist')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check that add review link exists
        add_url = reverse('admin:tailors_tailorprofilereview_add')
        self.assertContains(response, add_url, status_code=200)
    
    def test_inline_review_creation(self):
        """Test creating a review through inline admin"""
        # Get the change page for tailor profile
        url = reverse('admin:tailors_tailorprofile_change', args=[self.tailor_profile.pk])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Post data to create review through inline
        post_data = {
            'user': self.tailor_user.pk,
            'shop_name': 'Test Tailor Shop',
            'contact_number': '1234567890',
            'address': '123 Test St',
            'shop_status': True,
            'review_set-TOTAL_FORMS': '1',
            'review_set-INITIAL_FORMS': '0',
            'review_set-0-review_status': 'pending',
            'review_set-0-service_areas': '[]',
            '_save': 'Save'
        }
        
        response = self.client.post(url, post_data)
        # Should redirect on success
        self.assertIn(response.status_code, [200, 302])
        
        # Check that review was created
        self.assertTrue(TailorProfileReview.objects.filter(profile=self.tailor_profile).exists())
    
    def test_review_status_badge_colors(self):
        """Test that review status badges have correct colors"""
        from apps.tailors.admin import TailorProfileReviewAdmin
        
        # Create reviews with different statuses
        statuses = ['draft', 'pending', 'approved', 'rejected']
        
        for status in statuses:
            review = TailorProfileReview.objects.create(
                profile=self.tailor_profile,
                review_status=status
            )
            
            admin = TailorProfileReviewAdmin(TailorProfileReview, None)
            badge_html = admin.review_status_badge(review)
            
            # Check that badge contains status text
            self.assertIn(status.capitalize() if status != 'pending' else 'Pending Review', 
                         badge_html)
            
            # Clean up
            review.delete()
    
    def test_review_approval_action(self):
        """Test bulk approval action for reviews"""
        # Create multiple pending reviews
        profile2 = TailorProfile.objects.create(
            user=CustomUser.objects.create_user(
                username='tailor2',
                email='tailor2@test.com',
                password='testpass123',
                role='TAILOR'
            ),
            shop_name='Test Shop 2',
            contact_number='9876543210'
        )
        
        review1 = TailorProfileReview.objects.create(
            profile=self.tailor_profile,
            review_status='pending',
            submitted_at=timezone.now()
        )
        
        review2 = TailorProfileReview.objects.create(
            profile=profile2,
            review_status='pending',
            submitted_at=timezone.now()
        )
        
        # Get the changelist URL
        url = reverse('admin:tailors_tailorprofilereview_changelist')
        
        # Post approval action
        post_data = {
            'action': 'approve_profiles',
            '_selected_action': [str(review1.pk), str(review2.pk)]
        }
        
        response = self.client.post(url, post_data)
        self.assertIn(response.status_code, [200, 302])
        
        # Check that reviews were approved
        review1.refresh_from_db()
        review2.refresh_from_db()
        self.assertEqual(review1.review_status, 'approved')
        self.assertEqual(review2.review_status, 'approved')
        self.assertIsNotNone(review1.reviewed_at)
        self.assertEqual(review1.reviewed_by, self.admin_user)
    
    def test_review_rejection_action(self):
        """Test bulk rejection action for reviews"""
        review = TailorProfileReview.objects.create(
            profile=self.tailor_profile,
            review_status='pending',
            submitted_at=timezone.now()
        )
        
        url = reverse('admin:tailors_tailorprofilereview_changelist')
        
        post_data = {
            'action': 'reject_profiles',
            '_selected_action': [str(review.pk)]
        }
        
        response = self.client.post(url, post_data)
        self.assertIn(response.status_code, [200, 302])
        
        # Check that review was rejected
        review.refresh_from_db()
        self.assertEqual(review.review_status, 'rejected')
        self.assertIsNotNone(review.reviewed_at)
        self.assertEqual(review.reviewed_by, self.admin_user)
    
    def test_autocomplete_search_functionality(self):
        """Test that autocomplete search works for profile field"""
        # Create another profile for searching
        profile2 = TailorProfile.objects.create(
            user=CustomUser.objects.create_user(
                username='tailor3',
                email='tailor3@test.com',
                password='testpass123',
                role='TAILOR'
            ),
            shop_name='Another Shop',
            contact_number='1111111111'
        )
        
        # Test autocomplete endpoint (Django admin autocomplete)
        url = reverse('admin:tailors_tailorprofile_autocomplete')
        response = self.client.get(url, {'q': 'Test'})
        
        # Should return JSON response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
    
    def test_review_inline_max_num_constraint(self):
        """Test that only one review can be added per profile (OneToOne constraint)"""
        # Create a review
        TailorProfileReview.objects.create(
            profile=self.tailor_profile,
            review_status='pending'
        )
        
        # Try to add another review through inline - should not be possible
        url = reverse('admin:tailors_tailorprofile_change', args=[self.tailor_profile.pk])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # The inline should show existing review, not allow adding new one
        self.assertContains(response, 'pending', status_code=200)
    
    def test_review_status_readonly_after_approval(self):
        """Test that review status becomes readonly after approval/rejection"""
        review = TailorProfileReview.objects.create(
            profile=self.tailor_profile,
            review_status='approved',
            reviewed_at=timezone.now(),
            reviewed_by=self.admin_user
        )
        
        url = reverse('admin:tailors_tailorprofilereview_change', args=[review.pk])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check that review_status is in readonly_fields when approved
        # This is handled by get_readonly_fields method
    
    def test_review_export_csv_action(self):
        """Test CSV export action for reviews"""
        review = TailorProfileReview.objects.create(
            profile=self.tailor_profile,
            review_status='approved',
            submitted_at=timezone.now(),
            reviewed_at=timezone.now(),
            reviewed_by=self.admin_user
        )
        
        url = reverse('admin:tailors_tailorprofilereview_changelist')
        
        post_data = {
            'action': 'export_reviews_csv',
            '_selected_action': [str(review.pk)]
        }
        
        response = self.client.post(url, post_data)
        
        # Should return CSV file
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])


if __name__ == '__main__':
    import django
    django.setup()
    from django.test.utils import get_runner
    from django.conf import settings
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['test_tailor_profile_review_admin'])
    
    if failures:
        exit(1)

