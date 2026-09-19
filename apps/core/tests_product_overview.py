from django.test import TestCase
from django.urls import reverse

from apps.core.product_overview import load_product_overview


class ProductOverviewLoaderTests(TestCase):
    def test_load_product_overview_returns_chapters(self):
        document = load_product_overview()
        self.assertGreaterEqual(len(document.chapters), 10)
        self.assertEqual(document.chapters[0].number, 1)
        self.assertIn('Introduction', document.chapters[0].title)
        self.assertTrue(document.chapters[0].html_content)

    def test_toc_matches_chapters(self):
        document = load_product_overview()
        self.assertEqual(len(document.toc), len(document.chapters))
        for item, chapter in zip(document.toc, document.chapters):
            self.assertEqual(item['anchor'], chapter.anchor)
            self.assertEqual(item['title'], chapter.title)


class ProductOverviewViewTests(TestCase):
    def test_product_overview_page_returns_200(self):
        response = self.client.get(reverse('product-overview'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mgask Product Overview')
        self.assertContains(response, 'Chapter 1')
        self.assertContains(response, 'Customer App')
        self.assertContains(response, 'Contents')
        self.assertNotContains(response, 'Signature')
        self.assertNotContains(response, 'Download PDF')

    def test_product_overview_page_includes_all_chapters(self):
        document = load_product_overview()
        response = self.client.get(reverse('product-overview'))
        for chapter in document.chapters:
            self.assertContains(response, chapter.anchor)
