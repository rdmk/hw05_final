from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа123',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст12',
        )

    def test_models_have_correct_object_names(self):
        """Проверка: правильно ли отображается значение поля __str__"""
        post = self.post
        expected = post.text[:15]
        self.assertEqual(expected, str(post))

    def test_models_have_correct_group_names(self):
        """Проверка: правильно ли отображается значение поля __str__"""
        group = self.group
        excepted = group.title[:15]
        self.assertEqual(excepted, str(group))
