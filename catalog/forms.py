from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import datetime


class RenewBookForm(forms.Form):
    renewal_date = forms.DateField(
        label="Fecha de renovación",
        help_text="Ingrese una fecha entre hoy y 4 semanas adelante.",
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={'type': 'date'}
        )
    )

    def clean_renewal_date(self):
        data = self.cleaned_data['renewal_date']

        if data < datetime.date.today():
            raise ValidationError(_('Fecha inválida: no puede ser una fecha pasada.'))

        if data > datetime.date.today() + datetime.timedelta(weeks=4):
            raise ValidationError(_('Fecha inválida: no puede ser mayor a 4 semanas.'))

        return data