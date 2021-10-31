import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Follow, Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='test-title',
            slug='test-slug',
            description='test-decsr',
        )
        cls.user = User.objects.create_user(username='Test_user')
        cls.user_follower = User.objects.create_user(username='Follower')
        cls.post_list = []
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        for i in range(13):
            cls.post_list.append(Post(
                text=f'Текст № {i}',
                author=cls.user,
                group=cls.group,
                id=i,
                image=uploaded
            ))
        cls.test_posts = Post.objects.bulk_create(cls.post_list, 13)
        cls.index_url = reverse(
            'posts:index'
        )
        cls.group_list_url = reverse(
            'posts:group_list', kwargs={'slug': cls.group.slug}
        )
        cls.templates_pages_names = {
            cls.index_url: 'posts/index.html',
            cls.group_list_url: 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': cls.user}): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={
                    'post_id': '0'}): 'posts/post_detail.html',
            reverse(
                'posts:post_edit',
                kwargs={
                    'post_id': '0'}): 'posts/create_or_update.html',
            reverse(
                'posts:post_create'): 'posts/create_or_update.html'
        }
        cls.reverse_page_names_post = {
            cls.index_url: cls.group.slug,
            cls.group_list_url: cls.group.slug,
            reverse('posts:profile', kwargs={
                'username': cls.user}): cls.group.slug
        }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client_follower = Client(self.user_follower)
        self.authorized_client = Client(self.user)
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for reverse_name, template in self.templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(self.index_url)
        object = response.context['page_obj'][0]
        post_id = object.id
        post_text = object.text
        post_author = object.author
        post_group = object.group
        self.assertEqual(post_text, self.test_posts[post_id].text)
        self.assertEqual(post_author, self.user)
        self.assertEqual(post_group, self.group)

    def test_group_page_show_correct_context(self):
        """Шаблон group сформирован с правильным контекстом."""
        response = self.authorized_client.get(self.group_list_url)
        object = response.context['page_obj'][0]
        post_title = object.group.title
        post_slug = object.group.slug
        post_description = object.group.description
        self.assertEqual(post_title, self.group.title)
        self.assertEqual(post_slug, self.group.slug)
        self.assertEqual(post_description, self.group.description)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user})
        )
        for object in response.context['page_obj']:
            post_id = object.id
            post_text = object.text
            post_author = object.author
            post_group = object.group
            self.assertEqual(post_text, self.test_posts[post_id].text)
            self.assertEqual(post_author, self.user)
            self.assertEqual(post_group, self.group)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail',
                    kwargs={'post_id': self.test_posts[0].id}
                    )
        )
        self.assertEqual(response.context['post'].text,
                         self.test_posts[0].text)
        self.assertEqual(response.context['post'].author,
                         self.user)
        self.assertEqual(response.context['post'].group,
                         self.group)

    def test_post_edit_page_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        post_example = self.test_posts[0]
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': post_example.id})
        )
        self.assertEqual(response.context['post'].text, post_example.text)
        self.assertEqual(response.context['post'].group, self.group)

    def test_pages_with_paginator(self):
        """Тестирование страниц с паджинатором."""
        pages_with_paginator = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user})
        ]
        # Подсчет кол-ва страниц
        num = (len(self.test_posts) // 10) + 1
        for page in pages_with_paginator:
            # Если одна страница в паджинаторе, то подсчитываем кол-во постов
            if num == 1:
                response = self.authorized_client.get(
                    page + '?page=' + str(num)
                )
                self.assertEqual(
                    len(response.context['page_obj']),
                    len(self.test_posts)
                )
            # Если несколько страниц, то проверяем количество на первой и
            # последних страницах
            else:
                response_first = self.authorized_client.get(
                    page + '?page=' + '1'
                )
                response_last = self.authorized_client.get(
                    page + '?page=' + str(num)
                )
                self.assertEqual(
                    len(response_first.context['page_obj']),
                    10
                )
                self.assertEqual(
                    len(response_last.context['page_obj']),
                    (len(self.test_posts) % 10)
                )

    def test_post_in_index_group_profile_create(self):
        """Проверка:созданный пост появился на главной, в группе, в профиле."""
        for value, expected in self.reverse_page_names_post.items():
            response = self.authorized_client.get(value)
            for object in response.context['page_obj']:
                post_group = object.group.slug
                with self.subTest(value=value):
                    self.assertEqual(post_group, expected)

    def test_post_not_in_foreign_group(self):
        """Проверка: созданный пост не появился в чужой группе."""
        test_group = Group.objects.create(
            title='test-title 2',
            slug='test-slug_2',
            description='test-decsr 2',
        )
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': test_group.slug})
        )
        for object in response.context['page_obj']:
            post_slug = object.group.slug
            self.assertNotEqual(post_slug, self.group.slug)

    def test_index_page_show_correct_context_with_image(self):
        """Шаблон index сформирован с правильным контекстом,
        в том числе и картинка.
        """
        response = self.authorized_client.get(self.index_url)
        object = response.context['page_obj'][0]
        post_id = object.id
        post_text = object.text
        post_author = object.author
        post_group = object.group
        post_gif = object.image
        self.assertEqual(post_text, self.test_posts[post_id].text)
        self.assertEqual(post_author, self.user)
        self.assertEqual(post_group, self.group)
        self.assertEqual(post_gif, self.test_posts[post_id].image)

    def test_group_page_show_correct_context_with_image(self):
        """Шаблон group_page сформирован с правильным контекстом,
        в том числе и картинка.
        """
        response = self.authorized_client.get(self.group_list_url)
        object = response.context['page_obj'][0]
        post_title = object.group.title
        post_slug = object.group.slug
        post_description = object.group.description
        post_gif = object.image
        self.assertEqual(post_title, self.group.title)
        self.assertEqual(post_slug, self.group.slug)
        self.assertEqual(post_description, self.group.description)
        self.assertEqual(post_gif, self.test_posts[-1].image)

    def test_profile_page_show_correct_context_with_image(self):
        """Шаблон profile сформирован с правильным контекстом,
        в том числе и картинка.
        """
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user})
        )
        object = response.context['page_obj'][0]
        post_id = object.id
        post_text = object.text
        post_author = object.author
        post_group = object.group
        post_gif = object.image
        self.assertEqual(post_text, self.test_posts[post_id].text)
        self.assertEqual(post_author, self.user)
        self.assertEqual(post_group, self.group)
        self.assertEqual(post_gif, self.test_posts[-1].image)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом,
        в том числе и картинка.
        """
        response = self.authorized_client.get(
            reverse('posts:post_detail',
                    kwargs={'post_id': self.test_posts[0].id}
                    )
        )
        self.assertEqual(response.context['post'].text,
                         self.test_posts[0].text)
        self.assertEqual(response.context['post'].author,
                         self.user)
        self.assertEqual(response.context['post'].group,
                         self.group)
        self.assertEqual(response.context['post'].image,
                         self.test_posts[0].image)

    def test_comment_in_post(self):
        """Проверка: созданный комментарий
        появился на странице поста.
        """
        test_comment = Comment.objects.create(
            post=self.test_posts[0],
            author=self.user,
            text="Тестовый коммент"
        )
        response = self.authorized_client.get(
            reverse('posts:post_detail',
                    kwargs={'post_id': self.test_posts[0].id}
                    )
        )
        object = response.context['comment'][0]
        comment_author = object.author
        comment_text = object.text
        self.assertEqual(comment_author, test_comment.author)
        self.assertEqual(comment_text, test_comment.text)

    def test_index_page_cache(self):
        """Тестирование кэша."""
        posts_count = Post.objects.count()
        response = self.authorized_client.get(self.index_url).content
        Post.objects.create(
            text="Тест кэша",
            author=self.user
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(
            response,
            self.authorized_client.get(self.index_url).content
        )
        cache.clear()
        self.assertNotEqual(
            response,
            self.authorized_client.get(self.index_url).content
        )

    def test_follow(self):
        """Проверка: авторизованный пользователь может подписаться
        на другого пользователя.
        """
        follow_count = Follow.objects.count()
        self.authorized_client_follower.force_login(self.user_follower)
        self.authorized_client_follower.get(
            reverse('posts:profile_follow', kwargs={'username': self.user})
        )
        self.assertEqual(Follow.objects.count(), follow_count + 1)
        self.assertTrue(
            Follow.objects.filter(
                user=self.user_follower,
                author=self.user
            ).exists()
        )

    def test_unfollow(self):
        """Проверка: авторизованный пользователь может отписаться
        на другого пользователя.
        """
        self.authorized_client_follower.force_login(self.user_follower)
        self.authorized_client_follower.get(
            reverse('posts:profile_follow', kwargs={'username': self.user})
        )
        follow_count = Follow.objects.count()
        self.authorized_client_follower.get(
            reverse('posts:profile_unfollow', kwargs={'username': self.user})
        )
        self.assertEqual(Follow.objects.count(), follow_count - 1)
        self.assertFalse(
            Follow.objects.filter(
                user=self.user_follower,
                author=self.user
            ).exists()
        )

    def test_follow_page_if_follower(self):
        """Проверка на наличие нового поста в ленте подписок,
        если пользователь подписан на автора.
        """
        self.authorized_client_follower.force_login(self.user_follower)
        self.authorized_client_follower.get(
            reverse('posts:profile_follow', kwargs={'username': self.user})
        )
        post = Post.objects.create(
            text="Тест подписки",
            author=self.user
        )
        response = self.authorized_client_follower.get(reverse(
            'posts:follow_index')
        )
        object = response.context['page_obj'][0]
        post_text = object.text
        post_author = object.author
        self.assertEqual(post_text, post.text)
        self.assertEqual(post_author, self.user)

    def test_follow_page_if_not_follower(self):
        """Проверка на отсутствие нового поста в ленте подписок,
        если пользователь не подписан на автора.
        """
        self.authorized_client_follower.force_login(self.user_follower)
        Post.objects.create(
            text="Тест подписки",
            author=self.user,
            pk=6666
        )
        response = self.authorized_client_follower.get(reverse(
            'posts:follow_index')
        )
        self.assertEqual(len(response.context['page_obj']), 0)
