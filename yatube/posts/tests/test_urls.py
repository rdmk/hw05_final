from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='test-title',
            slug='test-slug',
            description='test-decsr',
        )
        cls.user = User.objects.create_user(username='Test_user')
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
            pk='1234',
        )
        cls.static_urls = {
            '/': HTTPStatus.OK,
            '/create/': HTTPStatus.OK,
            f'/group/{cls.group.slug}/': HTTPStatus.OK,
            f'/profile/{cls.user.username}/': HTTPStatus.OK,
            f'/posts/{cls.post.pk}/': HTTPStatus.OK,
            f'/posts/{cls.post.pk}/edit/': HTTPStatus.OK,
        }
        cls.templates_url_names = {
            '/': 'posts/index.html',
            '/create/': 'posts/create_or_update.html',
            f'/group/{cls.group.slug}/': 'posts/group_list.html',
            f'/profile/{cls.user.username}/': 'posts/profile.html',
            f'/posts/{cls.post.pk}/': 'posts/post_detail.html',
            f'/posts/{cls.post.pk}/edit/': 'posts/create_or_update.html',
        }
        cls.redirects_urls = {
            '/create/':
                '/auth/login/?next=/create/',
            f'/posts/{cls.post.pk}/edit/':
                f'/auth/login/?next=/posts/{cls.post.pk}/edit/',
            f'/posts/{cls.post.pk}/comment/':
                f'/auth/login/?next=/posts/{cls.post.pk}/comment/'
        }

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client(self.user)
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_urls_exists_at_desired_location(self):
        """Проверка страниц на доступность."""
        for address, response_on_url in self.static_urls.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, response_on_url)

    def test_unexisting_page(self):
        """Проверка: при запросе на существующую страницу вернется 404"""
        response = self.authorized_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for address, template in self.templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_auth_user_can_not_edit_someone_elses_post(self):
        """Страница по адресу posts/n/edit/ перенаправит авторизованного
        пользователя на страницу этого поста, если он не является автором.
        """
        test_user = User.objects.create_user(username='New_test_user')
        authorized_client = Client(test_user)
        authorized_client.force_login(test_user)
        response = authorized_client.get(
            f'/posts/{self.post.pk}/edit/',
            follow=True
        )
        self.assertRedirects(
            response,
            f'/posts/{self.post.pk}/'
        )

    def test_guest_client_redirect(self):
        """Проверка: перенаправление гостевого пользователя
        при создании или редактирования поста.
        """
        for address, redirect in self.redirects_urls.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.FOUND)
                self.assertRedirects(response, redirect)

    def test_add_comment_by_auth_client(self):
        """Проверка: добавление комментариев доступно только
        авторизованному пользователю.
        """
        response = self.authorized_client.get(
            f'/posts/{self.post.pk}/comment/',
            follow=True
        )
        self.assertTemplateUsed(response, 'posts/post_detail.html')
