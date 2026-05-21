import datetime
import uuid

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User, Permission

from catalog.models import Author, Book, BookInstance, Genre
from catalog import models as catalog_models


def crear_libro_de_prueba():
    test_author = Author.objects.create(first_name='John', last_name='Smith')
    test_genre = Genre.objects.create(name='Fantasy')

    datos_libro = {
        'title': 'Book Title',
        'summary': 'My book summary',
        'isbn': 'ABCDEFG',
        'author': test_author,
    }

    Language = getattr(catalog_models, 'Language', None)

    if Language is not None:
        campos_book = [campo.name for campo in Book._meta.fields]
        if 'language' in campos_book:
            test_language = Language.objects.create(name='English')
            datos_libro['language'] = test_language

    test_book = Book.objects.create(**datos_libro)
    test_book.genre.set([test_genre])
    test_book.save()

    return test_book


class AuthorListViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        number_of_authors = 13

        for author_num in range(number_of_authors):
            Author.objects.create(
                first_name=f'Christian {author_num}',
                last_name=f'Surname {author_num}',
            )

    def test_view_url_exists_at_desired_location(self):
        resp = self.client.get('/catalog/authors/')
        self.assertEqual(resp.status_code, 200)

    def test_view_url_accessible_by_name(self):
        resp = self.client.get(reverse('authors'))
        self.assertEqual(resp.status_code, 200)

    def test_view_uses_correct_template(self):
        resp = self.client.get(reverse('authors'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'catalog/author_list.html')

    def test_pagination_is_ten(self):
        resp = self.client.get(reverse('authors'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('is_paginated' in resp.context)
        self.assertTrue(resp.context['is_paginated'])
        self.assertEqual(len(resp.context['author_list']), 10)

    def test_lists_all_authors(self):
        resp = self.client.get(reverse('authors') + '?page=2')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('is_paginated' in resp.context)
        self.assertTrue(resp.context['is_paginated'])
        self.assertEqual(len(resp.context['author_list']), 3)


class LoanedBookInstancesByUserListViewTest(TestCase):

    def setUp(self):
        test_user1 = User.objects.create_user(username='testuser1', password='12345')
        test_user2 = User.objects.create_user(username='testuser2', password='12345')

        test_book = crear_libro_de_prueba()

        number_of_book_copies = 30

        for book_copy in range(number_of_book_copies):
            return_date = timezone.now().date() + datetime.timedelta(days=book_copy % 5)

            if book_copy % 2:
                the_borrower = test_user1
            else:
                the_borrower = test_user2

            BookInstance.objects.create(
                book=test_book,
                imprint='Unlikely Imprint, 2016',
                due_back=return_date,
                borrower=the_borrower,
                status='m'
            )

    def test_redirect_if_not_logged_in(self):
        resp = self.client.get(reverse('my-borrowed'))
        self.assertRedirects(resp, '/accounts/login/?next=/catalog/mybooks/')

    def test_logged_in_uses_correct_template(self):
        self.client.login(username='testuser1', password='12345')
        resp = self.client.get(reverse('my-borrowed'))

        self.assertEqual(str(resp.context['user']), 'testuser1')
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'catalog/bookinstance_list_borrowed_user.html')

    def test_only_borrowed_books_in_list(self):
        self.client.login(username='testuser1', password='12345')
        resp = self.client.get(reverse('my-borrowed'))

        self.assertEqual(str(resp.context['user']), 'testuser1')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('bookinstance_list' in resp.context)
        self.assertEqual(len(resp.context['bookinstance_list']), 0)

        get_ten_books = BookInstance.objects.all()[:10]

        for copy in get_ten_books:
            copy.status = 'o'
            copy.save()

        resp = self.client.get(reverse('my-borrowed'))

        self.assertEqual(str(resp.context['user']), 'testuser1')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('bookinstance_list' in resp.context)

        for bookitem in resp.context['bookinstance_list']:
            self.assertEqual(resp.context['user'], bookitem.borrower)
            self.assertEqual('o', bookitem.status)

    def test_pages_ordered_by_due_date(self):
        for copy in BookInstance.objects.all():
            copy.status = 'o'
            copy.save()

        self.client.login(username='testuser1', password='12345')
        resp = self.client.get(reverse('my-borrowed'))

        self.assertEqual(str(resp.context['user']), 'testuser1')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['bookinstance_list']), 10)

        last_date = None

        for copy in resp.context['bookinstance_list']:
            if last_date is not None:
                self.assertTrue(last_date <= copy.due_back)

            last_date = copy.due_back


class RenewBookInstancesViewTest(TestCase):

    def setUp(self):
        test_user1 = User.objects.create_user(username='testuser1', password='12345')
        test_user2 = User.objects.create_user(username='testuser2', password='12345')

        permission = Permission.objects.get(codename='can_mark_returned')
        test_user2.user_permissions.add(permission)

        test_book = crear_libro_de_prueba()

        return_date = datetime.date.today() + datetime.timedelta(days=5)

        self.test_bookinstance1 = BookInstance.objects.create(
            book=test_book,
            imprint='Unlikely Imprint, 2016',
            due_back=return_date,
            borrower=test_user1,
            status='o'
        )

        self.test_bookinstance2 = BookInstance.objects.create(
            book=test_book,
            imprint='Unlikely Imprint, 2016',
            due_back=return_date,
            borrower=test_user2,
            status='o'
        )

    def test_redirect_if_not_logged_in(self):
        resp = self.client.get(
            reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk})
        )

        self.assertEqual(resp.status_code, 403)

    def test_redirect_if_logged_in_but_not_correct_permission(self):
        self.client.login(username='testuser1', password='12345')

        resp = self.client.get(
            reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk})
        )

        self.assertEqual(resp.status_code, 403)

    def test_logged_in_with_permission_borrowed_book(self):
        self.client.login(username='testuser2', password='12345')

        resp = self.client.get(
            reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance2.pk})
        )

        self.assertEqual(resp.status_code, 200)

    def test_logged_in_with_permission_another_users_borrowed_book(self):
        self.client.login(username='testuser2', password='12345')

        resp = self.client.get(
            reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk})
        )

        self.assertEqual(resp.status_code, 200)

    def test_HTTP404_for_invalid_book_if_logged_in(self):
        test_uid = uuid.uuid4()

        self.client.login(username='testuser2', password='12345')

        resp = self.client.get(
            reverse('renew-book-librarian', kwargs={'pk': test_uid})
        )

        self.assertEqual(resp.status_code, 404)

    def test_uses_correct_template(self):
        self.client.login(username='testuser2', password='12345')

        resp = self.client.get(
            reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk})
        )

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'catalog/book_renew_librarian.html')

    def test_form_renewal_date_initially_has_date_three_weeks_in_future(self):
        self.client.login(username='testuser2', password='12345')

        resp = self.client.get(
            reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk})
        )

        self.assertEqual(resp.status_code, 200)

        date_3_weeks_in_future = datetime.date.today() + datetime.timedelta(weeks=3)

        self.assertEqual(
            resp.context['form'].initial['renewal_date'],
            date_3_weeks_in_future
        )

    def test_redirects_to_all_borrowed_book_list_on_success(self):
        self.client.login(username='testuser2', password='12345')

        valid_date_in_future = datetime.date.today() + datetime.timedelta(weeks=2)

        resp = self.client.post(
            reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}),
            {'renewal_date': valid_date_in_future}
        )

        self.assertRedirects(resp, reverse('all-borrowed'))

    def test_form_invalid_renewal_date_past(self):
        self.client.login(username='testuser2', password='12345')

        date_in_past = datetime.date.today() - datetime.timedelta(weeks=1)

        resp = self.client.post(
            reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}),
            {'renewal_date': date_in_past}
        )

        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            'Fecha inválida: no puede ser una fecha pasada.',
            resp.context['form'].errors['renewal_date']
        )

    def test_form_invalid_renewal_date_future(self):
        self.client.login(username='testuser2', password='12345')

        invalid_date_in_future = datetime.date.today() + datetime.timedelta(weeks=5)

        resp = self.client.post(
            reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}),
            {'renewal_date': invalid_date_in_future}
        )

        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            'Fecha inválida: no puede ser mayor a 4 semanas.',
            resp.context['form'].errors['renewal_date']
        )


class AuthorCreateViewTest(TestCase):

    def setUp(self):
        test_user1 = User.objects.create_user(username='testuser1', password='12345')
        test_user2 = User.objects.create_user(username='testuser2', password='12345')

        permission = Permission.objects.get(codename='can_mark_returned')
        test_user2.user_permissions.add(permission)

    def test_redirect_if_not_logged_in(self):
        resp = self.client.get(reverse('author-create'))

        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith('/accounts/login/'))

    def test_redirect_if_logged_in_but_not_correct_permission(self):
        self.client.login(username='testuser1', password='12345')

        resp = self.client.get(reverse('author-create'))

        self.assertEqual(resp.status_code, 403)

    def test_logged_in_with_permission_uses_correct_template(self):
        self.client.login(username='testuser2', password='12345')

        resp = self.client.get(reverse('author-create'))

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'catalog/author_form.html')

    def test_initial_date_of_death(self):
        self.client.login(username='testuser2', password='12345')

        resp = self.client.get(reverse('author-create'))

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.context['form'].initial['date_of_death'],
            '12/10/2016'
        )

    def test_redirects_after_successful_author_create(self):
        self.client.login(username='testuser2', password='12345')

        resp = self.client.post(
            reverse('author-create'),
            {
                'first_name': 'Nuevo',
                'last_name': 'Autor',
                'date_of_birth': '2000-01-01',
                'date_of_death': '2016-10-12',
            }
        )

        nuevo_autor = Author.objects.get(first_name='Nuevo', last_name='Autor')

        self.assertRedirects(resp, nuevo_autor.get_absolute_url())