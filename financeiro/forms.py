from django import forms
from .models import Despesa, Repasse, CentroCusto, SubGrupo, FormaPagamento


class DespesaForm(forms.ModelForm):
    class Meta:
        model = Despesa
        fields = ['data', 'centro_custo', 'subgrupo', 'descricao', 'valor', 'forma_pagamento', 'situacao']

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            centros  = CentroCusto.objects.filter(empresa=empresa).values_list('nome', 'nome')
            subgrupos = SubGrupo.objects.filter(empresa=empresa).values_list('nome', 'nome')
            formas   = FormaPagamento.objects.filter(empresa=empresa).values_list('nome', 'nome')
        else:
            centros = subgrupos = formas = []
        self.fields['centro_custo']    = forms.ChoiceField(choices=[('', 'Selecione...')] + list(centros))
        self.fields['subgrupo']        = forms.ChoiceField(choices=[('', 'Selecione...')] + list(subgrupos))
        self.fields['forma_pagamento'] = forms.ChoiceField(choices=[('', 'Selecione...')] + list(formas))
        self.fields['valor'].widget.attrs.update({'min': '0.01', 'step': '0.01'})
        for f in self.fields.values():
            f.widget.attrs.setdefault('class', 'field-input')


class RepasseForm(forms.ModelForm):
    class Meta:
        model = Repasse
        fields = ['data', 'tipo', 'origem', 'destino', 'valor', 'descricao']

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            centros = CentroCusto.objects.filter(empresa=empresa).values_list('nome', 'nome')
        else:
            centros = []
        choices = [('', 'Selecione...')] + list(centros)
        self.fields['origem']  = forms.ChoiceField(choices=choices)
        self.fields['destino'] = forms.ChoiceField(choices=choices)
        self.fields['valor'].widget.attrs.update({'min': '0.01', 'step': '0.01'})
        for f in self.fields.values():
            f.widget.attrs.setdefault('class', 'field-input')

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('origem') and cleaned.get('origem') == cleaned.get('destino'):
            raise forms.ValidationError('Origem e destino não podem ser iguais.')
        return cleaned
