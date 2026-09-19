import tempfile
from pathlib import Path
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from apps.core.product_overview import load_product_overview, get_client_pdf_path


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

    def test_product_overview_page_includes_all_chapters(self):
        document = load_product_overview()
        response = self.client.get(reverse('product-overview'))
        for chapter in document.chapters:
            self.assertContains(response, chapter.anchor)

    def test_product_overview_pdf_returns_200_when_file_exists(self):
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(b'%PDF-1.4\n% minimal test pdf\n')
            pdf_path = Path(tmp.name)

        try:
            with mock.patch(
                'apps.core.views_product_overview.get_client_pdf_path',
                return_value=pdf_path,
            ):
                response = self.client.get(reverse('product-overview-pdf'))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'application/pdf')
        finally:
            pdf_path.unlink(missing_ok=True)

    def test_product_overview_pdf_returns_404_when_missing(self):
        missing = Path('/nonexistent/Mgask-Product-Overview.pdf')
        with mock.patch(
            'apps.core.views_product_overview.get_client_pdf_path',
            return_value=missing,
        ):
            response = self.client.get(reverse('product-overview-pdf'))
        self.assertEqual(response.status_code, 404)
