"""
Script de seed: insere 40 Despesas e 40 Repasses para teste de paginação.
Uso: python manage.py shell < financeiro/seed_financeiro.py
"""
import random
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from empresa.models import Empresa
from financeiro.models import Despesa, Repasse

User = get_user_model()
user = User.objects.first()
empresa = Empresa.objects.first()

centros    = ['Administrativo', 'Comercial', 'Operacional', 'TI', 'RH']
subgrupos  = ['Combustível', 'Manutenção', 'Material de Escritório', 'Viagem', 'Serviços']
formas_pag = ['Dinheiro', 'Cartão Crédito', 'Cartão Débito', 'PIX', 'Boleto']
situacoes  = [Despesa.Situacao.PAGO, Despesa.Situacao.PENDENTE]
origens    = ['Matriz', 'Filial SP', 'Filial RJ', 'Caixa Geral']
destinos   = ['Filial MG', 'Fornecedor A', 'Fornecedor B', 'Caixa Reserva']
tipos_rep  = [Repasse.Tipo.APORTE, Repasse.Tipo.REPASSE]

base_date = date.today() - timedelta(days=60)

despesas = [
    Despesa(
        empresa=empresa,
        user=user,
        data=base_date + timedelta(days=i),
        centro_custo=centros[i % len(centros)],
        subgrupo=subgrupos[i % len(subgrupos)],
        descricao=f'Despesa de teste #{i+1}',
        valor=round(100 + i * 37.50, 2),
        forma_pagamento=formas_pag[i % len(formas_pag)],
        situacao=situacoes[i % 2],
    )
    for i in range(40)
]
Despesa.objects.bulk_create(despesas)
print(f'{len(despesas)} despesas criadas.')

repasses = [
    Repasse(
        empresa=empresa,
        user=user,
        data=base_date + timedelta(days=i),
        origem=origens[i % len(origens)],
        destino=destinos[i % len(destinos)],
        valor=round(500 + i * 125.00, 2),
        tipo=tipos_rep[i % 2],
        descricao=f'Repasse de teste #{i+1}',
    )
    for i in range(40)
]
Repasse.objects.bulk_create(repasses)
print(f'{len(repasses)} repasses criados.')
