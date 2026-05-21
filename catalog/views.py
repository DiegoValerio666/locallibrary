import datetime

from django.shortcuts import render, get_object_or_404
from django.views import generic
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy

from .models import Book, Author, BookInstance, Genre
from .forms import RenewBookForm


def index(request):
    """
    Vista para la página de inicio del sitio.
    """
    num_books = Book.objects.all().count()
    num_instances = BookInstance.objects.all().count()
    num_instances_available = BookInstance.objects.filter(status__exact='a').count()
    num_authors = Author.objects.count()

    num_visits = request.session.get('num_visits', 0)
    num_visits += 1
    request.session['num_visits'] = num_visits

    context = {
        'num_books': num_books,
        'num_instances': num_instances,
        'num_instances_available': num_instances_available,
        'num_authors': num_authors,
        'num_visits': num_visits,
    }

    return render(request, 'index.html', context=context)


class BookListView(generic.ListView):
    model = Book
    paginate_by = 10


class BookDetailView(generic.DetailView):
    model = Book


class AuthorListView(generic.ListView):
    model = Author
    paginate_by = 10


class AuthorDetailView(generic.DetailView):
    model = Author


class LoanedBooksByUserListView(LoginRequiredMixin, generic.ListView):
    """
    Muestra los libros prestados al usuario actual.
    """
    model = BookInstance
    template_name = 'catalog/bookinstance_list_borrowed_user.html'
    paginate_by = 10

    def get_queryset(self):
        return BookInstance.objects.filter(
            borrower=self.request.user
        ).filter(
            status__exact='o'
        ).order_by('due_back')


class LoanedBooksAllListView(PermissionRequiredMixin, generic.ListView):
    """
    Muestra todos los libros prestados.
    Solo usuarios con permiso can_mark_returned pueden entrar.
    """
    permission_required = 'catalog.can_mark_returned'
    model = BookInstance
    template_name = 'catalog/bookinstance_list_borrowed_all.html'
    paginate_by = 10

    def get_queryset(self):
        return BookInstance.objects.filter(
            status__exact='o'
        ).order_by('due_back')


@permission_required('catalog.can_mark_returned', raise_exception=True)
def renew_book_librarian(request, pk):
    """
    Renueva una copia específica de un libro.
    """
    book_inst = get_object_or_404(BookInstance, pk=pk)

    if request.method == 'POST':
        form = RenewBookForm(request.POST)

        if form.is_valid():
            book_inst.due_back = form.cleaned_data['renewal_date']
            book_inst.save()

            return HttpResponseRedirect(reverse('all-borrowed'))

    else:
        proposed_renewal_date = datetime.date.today() + datetime.timedelta(weeks=3)

        form = RenewBookForm(
            initial={
                'renewal_date': proposed_renewal_date,
            }
        )

    context = {
        'form': form,
        'bookinst': book_inst,
    }

    return render(request, 'catalog/book_renew_librarian.html', context)


class AuthorCreate(PermissionRequiredMixin, CreateView):
    model = Author
    fields = '__all__'
    initial = {'date_of_death': '12/10/2016'}
    permission_required = 'catalog.can_mark_returned'


class AuthorUpdate(PermissionRequiredMixin, UpdateView):
    permission_required = 'catalog.can_mark_returned'
    model = Author
    fields = ['first_name', 'last_name', 'date_of_birth', 'date_of_death']


class AuthorDelete(PermissionRequiredMixin, DeleteView):
    permission_required = 'catalog.can_mark_returned'
    model = Author
    success_url = reverse_lazy('authors')


class BookCreate(PermissionRequiredMixin, CreateView):
    permission_required = 'catalog.can_mark_returned'
    model = Book
    fields = ['title', 'author', 'summary', 'isbn', 'genre']


class BookUpdate(PermissionRequiredMixin, UpdateView):
    permission_required = 'catalog.can_mark_returned'
    model = Book
    fields = ['title', 'author', 'summary', 'isbn', 'genre']


class BookDelete(PermissionRequiredMixin, DeleteView):
    permission_required = 'catalog.can_mark_returned'
    model = Book
    success_url = reverse_lazy('books')