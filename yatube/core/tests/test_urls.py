from django.test import Client, TestCase


class CoreURLTests(TestCase):
    def test_404_template(self):
        guest_client = Client()
        response = guest_client.get('/unexistingpage/')
        self.assertTemplateUsed(response, 'core/404.html')
