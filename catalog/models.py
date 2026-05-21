from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from datetime import date
import uuid


class Genre(models.Model):
    """
    Modelo que representa un género literario.
    """
    name = models.CharField(
        max_length=200,
        help_text="Ingrese el nombre del género, por ejemplo: Ciencia ficción, Poesía, Historia."
    )

    def __str__(self):
        return self.name


class Book(models.Model):
    """
    Modelo que representa un libro, pero no una copia específica.
    """
    title = models.CharField(max_length=200)

    author = models.ForeignKey(
        'Author',
        on_delete=models.SET_NULL,
        null=True
    )

    summary = models.TextField(
        max_length=1000,
        help_text="Ingrese una breve descripción del libro"
    )

    isbn = models.CharField(
        'ISBN',
        max_length=13,
        help_text='13 caracteres ISBN'
    )

    genre = models.ManyToManyField(
        Genre,
        help_text="Seleccione un género para este libro"
    )

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('book-detail', args=[str(self.id)])

    def display_genre(self):
        """
        Crea una cadena para mostrar los géneros en el admin.
        """
        return ', '.join([genre.name for genre in self.genre.all()[:3]])

    display_genre.short_description = 'Genre'


class BookInstance(models.Model):
    """
    Modelo que representa una copia específica de un libro.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        help_text="ID único para esta copia del libro"
    )

    book = models.ForeignKey(
        'Book',
        on_delete=models.SET_NULL,
        null=True
    )

    imprint = models.CharField(max_length=200)

    due_back = models.DateField(
        null=True,
        blank=True
    )

    borrower = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    LOAN_STATUS = (
        ('m', 'Maintenance'),
        ('o', 'On loan'),
        ('a', 'Available'),
        ('r', 'Reserved'),
    )

    status = models.CharField(
        max_length=1,
        choices=LOAN_STATUS,
        blank=True,
        default='m',
        help_text='Disponibilidad del libro'
    )

    class Meta:
        ordering = ["due_back"]
        permissions = (("can_mark_returned", "Set book as returned"),)

    @property
    def is_overdue(self):
        if self.due_back and date.today() > self.due_back:
            return True
        return False

    def __str__(self):
        return f'{self.id} ({self.book.title})'


class Author(models.Model):
    """
    Modelo que representa un autor.
    """
    first_name = models.CharField(max_length=100)

    last_name = models.CharField(max_length=100)

    date_of_birth = models.DateField(
        null=True,
        blank=True
    )

    # ✅ CORRECCIÓN APLICADA: 'Died' → 'died' (minúscula)
    date_of_death = models.DateField('died', null=True, blank=True)

    class Meta:
        ordering = ['last_name']

    def get_absolute_url(self):
        return reverse('author-detail', args=[str(self.id)])

    def __str__(self):
        return f'{self.last_name}, {self.first_name}'