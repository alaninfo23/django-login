from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import models, transaction
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from empresa.decorators import requer_empresa
from .models import Abastecimento, Manutencao, Motorista, Veiculo, Viagem


def _veiculo_da_empresa(pk, empresa):
    return get_object_or_404(Veiculo, pk=pk, empresa=empresa)


def _erro_km_menor(km_informado, veiculo):
    """Retorna mensagem de erro se km_informado < veiculo.km_atual, senão None."""
    if km_informado and int(km_informado) < veiculo.km_atual:
        return f'KM informado ({km_informado}) é menor que o KM atual do veículo ({veiculo.km_atual} km).'
    return None


# ── Dashboard ──────────────────────────────────────────────────────────────────

@login_required
@requer_empresa
def dashboard(request):
    from datetime import date, timedelta, datetime
    from django.db.models import Sum, Count

    empresa = request.empresa
    hoje = date.today()

    # Filtro de período
    de  = request.GET.get('de', '')
    ate = request.GET.get('ate', '')
    try:
        data_de  = datetime.strptime(de,  '%Y-%m-%d').date() if de  else None
        data_ate = datetime.strptime(ate, '%Y-%m-%d').date() if ate else None
    except ValueError:
        data_de = data_ate = None

    veiculos_qs = Veiculo.objects.filter(empresa=empresa)

    # Dados enriquecidos por veículo
    limite_sem_mov = hoje - timedelta(days=30)
    veiculos = []
    for v in veiculos_qs:
        ab_qs  = v.abastecimentos.all()
        man_qs = v.manutencoes.all()
        via_qs = v.viagens.all()
        if data_de:
            ab_qs  = ab_qs.filter(data__gte=data_de)
            man_qs = man_qs.filter(data__gte=data_de)
            via_qs = via_qs.filter(saida__date__gte=data_de)
        if data_ate:
            ab_qs  = ab_qs.filter(data__lte=data_ate)
            man_qs = man_qs.filter(data__lte=data_ate)
            via_qs = via_qs.filter(saida__date__lte=data_ate)

        gasto_comb = ab_qs.aggregate(t=Sum('valor_total'))['t']
        gasto_man  = man_qs.filter(valor__isnull=False).aggregate(t=Sum('valor'))['t']
        total_litros = ab_qs.aggregate(t=Sum('litros'))['t']

        km_rodado_total = sum(
            (vg.km_final - vg.km_inicial)
            for vg in via_qs.filter(km_final__isnull=False)
            if vg.km_final and vg.km_final > vg.km_inicial
        )

        consumo_medio = None
        if total_litros and km_rodado_total:
            consumo_medio = round(km_rodado_total / float(total_litros), 2)

        # Sem movimentação nos últimos 30 dias
        sem_mov = (
            not v.abastecimentos.filter(data__gte=limite_sem_mov).exists() and
            not v.viagens.filter(saida__date__gte=limite_sem_mov).exists()
        )

        v.km_rodado_total      = km_rodado_total or None
        v.total_abastecimentos = ab_qs.count()
        v.gasto_combustivel    = gasto_comb
        v.gasto_manutencao     = gasto_man
        v.total_viagens        = via_qs.count()
        v.consumo_medio        = consumo_medio
        v.sem_movimentacao     = sem_mov
        veiculos.append(v)

    # Alertas de motoristas (QuerySets para .count funcionar no template)
    motoristas_cnh_vencida  = Motorista.objects.filter(
        empresa=empresa, status=Motorista.Status.ATIVO,
        cnh_validade__isnull=False, cnh_validade__lt=hoje,
    )
    motoristas_cnh_vencendo = Motorista.objects.filter(
        empresa=empresa, status=Motorista.Status.ATIVO,
        cnh_validade__range=(hoje, hoje + timedelta(days=30)),
    )

    # Alertas de manutenções (QuerySets para .count funcionar no template)
    manutencoes_vencidas = Manutencao.objects.filter(
        veiculo__empresa=empresa, status=Manutencao.Status.AGENDADA,
        data__lt=hoje,
    ).select_related('veiculo')
    manutencoes_vencendo = Manutencao.objects.filter(
        veiculo__empresa=empresa, status=Manutencao.Status.AGENDADA,
        data__range=(hoje, hoje + timedelta(days=7)),
    ).select_related('veiculo')

    return render(request, 'frota/dashboard.html', {
        'total_veiculos':         veiculos_qs.count(),
        'em_manutencao':          veiculos_qs.filter(status=Veiculo.Status.MANUTENCAO).count(),
        'viagens_abertas':        Viagem.objects.filter(veiculo__empresa=empresa, status=Viagem.Status.EM_ANDAMENTO).count(),
        'manut_agendadas':        len(manutencoes_vencidas) + len(manutencoes_vencendo),
        'veiculos':               veiculos,
        'motoristas_cnh_vencida':  motoristas_cnh_vencida,
        'motoristas_cnh_vencendo': motoristas_cnh_vencendo,
        'manutencoes_vencidas':    manutencoes_vencidas,
        'manutencoes_vencendo':    manutencoes_vencendo,
        'de':  de,
        'ate': ate,
    })


# ── Veículos ───────────────────────────────────────────────────────────────────

@login_required
@requer_empresa
def veiculo_list(request):
    veiculos = Veiculo.objects.filter(empresa=request.empresa)
    return render(request, 'frota/veiculo_list.html', {
        'veiculos': veiculos,
        'status_choices': Veiculo.Status,
    })


@login_required
@requer_empresa
def veiculo_create(request):
    if request.method == 'POST':
        Veiculo.objects.create(
            empresa=request.empresa,
            placa=request.POST.get('placa', '').upper().strip(),
            modelo=request.POST.get('modelo', '').strip(),
            marca=request.POST.get('marca', '').strip(),
            ano=request.POST.get('ano'),
            capacidade_carga=request.POST.get('capacidade_carga'),
            km_atual=request.POST.get('km_atual') or 0,
            status=request.POST.get('status', Veiculo.Status.ATIVO),
            observacoes=request.POST.get('observacoes', ''),
        )
        return redirect('frota_veiculos')
    return render(request, 'frota/veiculo_form.html', {'status_choices': Veiculo.Status})


@login_required
@requer_empresa
def veiculo_edit(request, pk):
    veiculo = _veiculo_da_empresa(pk, request.empresa)
    if request.method == 'POST':
        veiculo.placa            = request.POST.get('placa', '').upper().strip()
        veiculo.modelo           = request.POST.get('modelo', '').strip()
        veiculo.marca            = request.POST.get('marca', '').strip()
        veiculo.ano              = request.POST.get('ano')
        veiculo.capacidade_carga = request.POST.get('capacidade_carga')
        veiculo.km_atual         = request.POST.get('km_atual') or 0
        veiculo.status           = request.POST.get('status', veiculo.status)
        veiculo.observacoes      = request.POST.get('observacoes', '')
        veiculo.save()
        return redirect('frota_veiculos')
    return render(request, 'frota/veiculo_form.html', {
        'veiculo': veiculo, 'status_choices': Veiculo.Status,
    })


@login_required
@requer_empresa
def veiculo_delete(request, pk):
    veiculo = _veiculo_da_empresa(pk, request.empresa)
    if request.method == 'POST':
        try:
            veiculo.delete()
        except ProtectedError:
            msgs = []
            if veiculo.viagens.exists():
                msgs.append(f'{veiculo.viagens.count()} viagem(ns)')
            if veiculo.manutencoes.exists():
                msgs.append(f'{veiculo.manutencoes.count()} manutenção(ões)')
            if veiculo.abastecimentos.exists():
                msgs.append(f'{veiculo.abastecimentos.count()} abastecimento(s)')
            messages.error(request, f'Remova primeiro os registros vinculados: {", ".join(msgs)}.')
            return redirect('frota_veiculos')
        return redirect('frota_veiculos')
    return render(request, 'frota/confirm_delete.html', {
        'objeto': veiculo, 'cancelar_url': 'frota_veiculos',
    })


@login_required
@requer_empresa
def veiculo_detalhe(request, pk):
    from datetime import date
    from django.db.models import Sum

    veiculo = _veiculo_da_empresa(pk, request.empresa)

    abastecimentos = veiculo.abastecimentos.order_by('-data', '-criado_em')[:10]
    manutencoes    = veiculo.manutencoes.order_by('-data', '-criado_em')[:10]
    viagens        = veiculo.viagens.select_related('motorista').order_by('-saida')[:10]

    totais = veiculo.abastecimentos.aggregate(
        gasto_combustivel=Sum('valor_total'),
        total_abastecimentos=models.Count('id'),
    )
    totais['gasto_manutencao'] = veiculo.manutencoes.filter(
        valor__isnull=False
    ).aggregate(v=Sum('valor'))['v']
    totais['total_viagens'] = veiculo.viagens.count()

    km_rodado_total = sum(
        (v.km_final - v.km_inicial)
        for v in veiculo.viagens.filter(km_final__isnull=False)
        if v.km_final and v.km_final > v.km_inicial
    )

    total_litros = veiculo.abastecimentos.aggregate(t=Sum('litros'))['t']
    consumo_medio = (
        round(km_rodado_total / float(total_litros), 2)
        if total_litros and km_rodado_total else None
    )

    ultima_man = veiculo.manutencoes.filter(
        proxima_revisao__isnull=False
    ).order_by('-data').first()
    proxima_revisao = ultima_man.proxima_revisao if ultima_man else None
    revisao_vencida = proxima_revisao and proxima_revisao < date.today()

    return render(request, 'frota/veiculo_detalhe.html', {
        'veiculo':         veiculo,
        'abastecimentos':  abastecimentos,
        'manutencoes':     manutencoes,
        'viagens':         viagens,
        'totais':          totais,
        'km_rodado_total': km_rodado_total or None,
        'consumo_medio':   consumo_medio,
        'proxima_revisao': proxima_revisao,
        'revisao_vencida': revisao_vencida,
    })


# ── Abastecimentos ─────────────────────────────────────────────────────────────

@login_required
@requer_empresa
def abastecimento_list(request):
    from datetime import date, timedelta, datetime
    qs = Abastecimento.objects.filter(veiculo__empresa=request.empresa).select_related('veiculo')
    hoje = date.today()
    de         = request.GET.get('de', (hoje - timedelta(days=60)).isoformat())
    ate        = request.GET.get('ate', hoje.isoformat())
    veiculo_pk = request.GET.get('veiculo') or None
    if veiculo_pk:
        qs = qs.filter(veiculo_id=veiculo_pk)
    try:
        qs = qs.filter(data__range=(datetime.strptime(de, '%Y-%m-%d').date(),
                                    datetime.strptime(ate, '%Y-%m-%d').date()))
    except ValueError:
        pass
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'frota/abastecimento_list.html', {
        'page_obj': page,
        'veiculos': Veiculo.objects.filter(empresa=request.empresa),
        'veiculo_selecionado': veiculo_pk,
        'de': de, 'ate': ate,
    })


@login_required
@requer_empresa
def abastecimento_create(request):
    if request.method == 'POST':
        veiculo = _veiculo_da_empresa(request.POST.get('veiculo'), request.empresa)
        erro = _erro_km_menor(request.POST.get('km_atual'), veiculo)
        if erro:
            return render(request, 'frota/abastecimento_form.html', {
                'ab': None,
                'veiculos': Veiculo.objects.filter(empresa=request.empresa),
                'erro_km': erro, 'post': request.POST,
            })
        ab = Abastecimento.objects.create(
            veiculo=veiculo,
            data=request.POST.get('data'),
            km_atual=request.POST.get('km_atual'),
            litros=request.POST.get('litros'),
            valor_total=request.POST.get('valor_total'),
            posto=request.POST.get('posto', ''),
            observacoes=request.POST.get('observacoes', ''),
        )
        veiculo.atualizar_km(ab.km_atual)
        return redirect('frota_abastecimentos')
    return render(request, 'frota/abastecimento_form.html', {
        'veiculos': Veiculo.objects.filter(empresa=request.empresa),
    })


@login_required
@requer_empresa
def abastecimento_edit(request, pk):
    ab = get_object_or_404(Abastecimento, pk=pk, veiculo__empresa=request.empresa)
    if request.method == 'POST':
        veiculo = _veiculo_da_empresa(request.POST.get('veiculo'), request.empresa)
        erro = _erro_km_menor(request.POST.get('km_atual'), veiculo)
        if erro:
            return render(request, 'frota/abastecimento_form.html', {
                'ab': ab,
                'veiculos': Veiculo.objects.filter(empresa=request.empresa),
                'erro_km': erro, 'post': request.POST,
            })
        ab.veiculo      = veiculo
        ab.data         = request.POST.get('data')
        ab.km_atual     = request.POST.get('km_atual')
        ab.litros       = request.POST.get('litros')
        ab.valor_total  = request.POST.get('valor_total')
        ab.posto        = request.POST.get('posto', '')
        ab.observacoes  = request.POST.get('observacoes', '')
        ab.save()
        veiculo.atualizar_km(ab.km_atual)
        return redirect('frota_abastecimentos')
    return render(request, 'frota/abastecimento_form.html', {
        'ab': ab,
        'veiculos': Veiculo.objects.filter(empresa=request.empresa),
    })


@login_required
@requer_empresa
def abastecimento_delete(request, pk):
    ab = get_object_or_404(Abastecimento, pk=pk, veiculo__empresa=request.empresa)
    if request.method == 'POST':
        ab.delete()
        return redirect('frota_abastecimentos')
    return render(request, 'frota/confirm_delete.html', {
        'objeto': ab, 'cancelar_url': 'frota_abastecimentos',
    })


@require_POST
@login_required
@requer_empresa
def abastecimentos_bulk_delete(request):
    ids = request.POST.getlist('ids')
    selecionados = len(ids)
    if not selecionados:
        messages.info(request, 'Nenhum abastecimento selecionado.')
        return redirect('frota_abastecimentos')

    qs = Abastecimento.objects.filter(pk__in=ids, veiculo__empresa=request.empresa)
    deletaveis = qs.count()
    with transaction.atomic():
        qs.delete()

    if deletaveis:
        messages.success(request, f'{deletaveis} abastecimento(s) excluído(s).')
    if deletaveis < selecionados:
        messages.warning(request, f'{selecionados - deletaveis} item(ns) ignorado(s) (sem permissão ou inexistentes).')
    return redirect('frota_abastecimentos')


# ── Manutenções ────────────────────────────────────────────────────────────────

@login_required
@requer_empresa
def manutencao_list(request):
    qs = Manutencao.objects.filter(veiculo__empresa=request.empresa).select_related('veiculo')
    veiculo_pk = request.GET.get('veiculo')
    status     = request.GET.get('status')
    if veiculo_pk:
        qs = qs.filter(veiculo_id=veiculo_pk)
    if status:
        qs = qs.filter(status=status)
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'frota/manutencao_list.html', {
        'page_obj': page,
        'veiculos': Veiculo.objects.filter(empresa=request.empresa),
        'tipo_choices': Manutencao.Tipo,
        'status_choices': Manutencao.Status,
        'veiculo_selecionado': veiculo_pk,
        'status_selecionado': status,
    })


@login_required
@requer_empresa
def manutencao_create(request):
    if request.method == 'POST':
        veiculo = _veiculo_da_empresa(request.POST.get('veiculo'), request.empresa)
        km = request.POST.get('km_manutencao') or None
        erro = _erro_km_menor(km, veiculo)
        if erro:
            return render(request, 'frota/manutencao_form.html', {
                'veiculos': Veiculo.objects.filter(empresa=request.empresa),
                'tipo_choices': Manutencao.Tipo,
                'status_choices': Manutencao.Status,
                'erro_km': erro, 'post': request.POST,
            })
        Manutencao.objects.create(
            veiculo=veiculo,
            tipo=request.POST.get('tipo'),
            descricao=request.POST.get('descricao', ''),
            status=request.POST.get('status', Manutencao.Status.REALIZADA),
            oficina=request.POST.get('oficina', ''),
            valor=request.POST.get('valor') or None,
            km_manutencao=km,
            data=request.POST.get('data'),
            proxima_revisao=request.POST.get('proxima_revisao') or None,
        )
        if km:
            veiculo.atualizar_km(km)
        return redirect('frota_manutencoes')
    return render(request, 'frota/manutencao_form.html', {
        'veiculos': Veiculo.objects.filter(empresa=request.empresa),
        'tipo_choices': Manutencao.Tipo,
        'status_choices': Manutencao.Status,
    })


@login_required
@requer_empresa
def manutencao_edit(request, pk):
    man = get_object_or_404(Manutencao, pk=pk, veiculo__empresa=request.empresa)
    if request.method == 'POST':
        km = request.POST.get('km_manutencao') or None
        veiculo = _veiculo_da_empresa(request.POST.get('veiculo'), request.empresa)
        erro = _erro_km_menor(km, veiculo)
        if erro:
            return render(request, 'frota/manutencao_form.html', {
                'man': man,
                'veiculos': Veiculo.objects.filter(empresa=request.empresa),
                'tipo_choices': Manutencao.Tipo,
                'status_choices': Manutencao.Status,
                'erro_km': erro, 'post': request.POST,
            })
        man.veiculo         = veiculo
        man.tipo            = request.POST.get('tipo')
        man.descricao       = request.POST.get('descricao', '')
        man.status          = request.POST.get('status', man.status)
        man.oficina         = request.POST.get('oficina', '')
        man.valor           = request.POST.get('valor') or None
        man.km_manutencao   = km
        man.data            = request.POST.get('data')
        man.proxima_revisao = request.POST.get('proxima_revisao') or None
        man.save()
        if km:
            man.veiculo.atualizar_km(km)
        return redirect('frota_manutencoes')
    return render(request, 'frota/manutencao_form.html', {
        'man': man,
        'veiculos': Veiculo.objects.filter(empresa=request.empresa),
        'tipo_choices': Manutencao.Tipo,
        'status_choices': Manutencao.Status,
    })


@login_required
@requer_empresa
def manutencao_delete(request, pk):
    man = get_object_or_404(Manutencao, pk=pk, veiculo__empresa=request.empresa)
    if request.method == 'POST':
        man.delete()
        return redirect('frota_manutencoes')
    return render(request, 'frota/confirm_delete.html', {
        'objeto': man, 'cancelar_url': 'frota_manutencoes',
    })


@require_POST
@login_required
@requer_empresa
def manutencoes_bulk_delete(request):
    ids = request.POST.getlist('ids')
    selecionados = len(ids)
    if not selecionados:
        messages.info(request, 'Nenhuma manutenção selecionada.')
        return redirect('frota_manutencoes')

    qs = Manutencao.objects.filter(pk__in=ids, veiculo__empresa=request.empresa)
    deletaveis = qs.count()
    with transaction.atomic():
        qs.delete()

    if deletaveis:
        messages.success(request, f'{deletaveis} manutenção(ões) excluída(s).')
    if deletaveis < selecionados:
        messages.warning(request, f'{selecionados - deletaveis} item(ns) ignorado(s) (sem permissão ou inexistentes).')
    return redirect('frota_manutencoes')


# ── Viagens ────────────────────────────────────────────────────────────────────

@login_required
@requer_empresa
def viagem_list(request):
    from datetime import date, timedelta, datetime
    qs = Viagem.objects.filter(veiculo__empresa=request.empresa).select_related('veiculo', 'motorista')
    hoje = date.today()
    de         = request.GET.get('de', (hoje - timedelta(days=60)).isoformat())
    ate        = request.GET.get('ate', hoje.isoformat())
    veiculo_pk = request.GET.get('veiculo') or None
    status     = request.GET.get('status')
    if veiculo_pk:
        qs = qs.filter(veiculo_id=veiculo_pk)
    if status:
        qs = qs.filter(status=status)
    try:
        qs = qs.filter(saida__date__range=(datetime.strptime(de, '%Y-%m-%d').date(),
                                           datetime.strptime(ate, '%Y-%m-%d').date()))
    except ValueError:
        pass
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'frota/viagem_list.html', {
        'page_obj': page,
        'veiculos': Veiculo.objects.filter(empresa=request.empresa),
        'status_choices': Viagem.Status,
        'veiculo_selecionado': veiculo_pk,
        'status_selecionado': status,
        'de': de, 'ate': ate,
    })


def _ctx_viagem(empresa):
    return {
        'veiculos':       Veiculo.objects.filter(empresa=empresa),
        'motoristas':     Motorista.objects.filter(empresa=empresa, status=Motorista.Status.ATIVO),
        'status_choices': Viagem.Status,
    }


def _validar_km_viagem(km_inicial, km_final):
    if km_final and int(km_final) < int(km_inicial):
        return None, 'KM final não pode ser menor que KM inicial.'
    return None, None


@login_required
@requer_empresa
def viagem_create(request):
    if request.method == 'POST':
        km_inicial = request.POST.get('km_inicial')
        km_final   = request.POST.get('km_final') or None
        _, erro_km_final = _validar_km_viagem(km_inicial, km_final)
        if erro_km_final:
            ctx = _ctx_viagem(request.empresa)
            ctx.update({'erro_km_final': erro_km_final, 'post': request.POST})
            return render(request, 'frota/viagem_form.html', ctx)
        veiculo = _veiculo_da_empresa(request.POST.get('veiculo'), request.empresa)
        erro_km_inicial = _erro_km_menor(km_inicial, veiculo)
        if erro_km_inicial:
            ctx = _ctx_viagem(request.empresa)
            ctx.update({'erro_km_inicial': erro_km_inicial, 'post': request.POST})
            return render(request, 'frota/viagem_form.html', ctx)
        if veiculo.status != Veiculo.Status.ATIVO:
            ctx = _ctx_viagem(request.empresa)
            ctx['erro_veiculo'] = f'Veículo {veiculo.placa} está "{veiculo.get_status_display()}" e não pode ser usado em viagens.'
            ctx['post'] = request.POST
            return render(request, 'frota/viagem_form.html', ctx)
        motorista_pk = request.POST.get('motorista') or None
        motorista = get_object_or_404(Motorista, pk=motorista_pk, empresa=request.empresa) if motorista_pk else None
        if motorista and motorista.cnh_vencida:
            messages.warning(request, f'Atenção: CNH de {motorista.nome} está vencida desde {motorista.cnh_validade:%d/%m/%Y}.')
        elif motorista and motorista.cnh_vencendo:
            messages.warning(request, f'Atenção: CNH de {motorista.nome} vence em {motorista.cnh_validade:%d/%m/%Y}.')
        v = Viagem.objects.create(
            veiculo=veiculo, motorista=motorista,
            origem=request.POST.get('origem', ''),
            destino=request.POST.get('destino', ''),
            saida=request.POST.get('saida'),
            retorno=request.POST.get('retorno') or None,
            km_inicial=km_inicial, km_final=km_final,
            status=request.POST.get('status', Viagem.Status.EM_ANDAMENTO),
            observacoes=request.POST.get('observacoes', ''),
            ajudante1_nome=request.POST.get('ajudante1_nome', ''),
            ajudante1_telefone=request.POST.get('ajudante1_telefone', ''),
            ajudante2_nome=request.POST.get('ajudante2_nome', ''),
            ajudante2_telefone=request.POST.get('ajudante2_telefone', ''),
            ajudante3_nome=request.POST.get('ajudante3_nome', ''),
            ajudante3_telefone=request.POST.get('ajudante3_telefone', ''),
        )
        if v.status == Viagem.Status.CONCLUIDA and km_final:
            veiculo.atualizar_km(km_final)
        return redirect('frota_viagens')
    return render(request, 'frota/viagem_form.html', _ctx_viagem(request.empresa))


@login_required
@requer_empresa
def viagem_edit(request, pk):
    viagem = get_object_or_404(Viagem, pk=pk, veiculo__empresa=request.empresa)
    if request.method == 'POST':
        km_inicial = request.POST.get('km_inicial')
        km_final   = request.POST.get('km_final') or None
        _, erro_km_final = _validar_km_viagem(km_inicial, km_final)
        if erro_km_final:
            ctx = _ctx_viagem(request.empresa)
            ctx.update({'viagem': viagem, 'erro_km_final': erro_km_final, 'post': request.POST})
            return render(request, 'frota/viagem_form.html', ctx)
        motorista_pk = request.POST.get('motorista') or None
        viagem.veiculo    = _veiculo_da_empresa(request.POST.get('veiculo'), request.empresa)
        erro_km_inicial = _erro_km_menor(km_inicial, viagem.veiculo)
        if erro_km_inicial:
            ctx = _ctx_viagem(request.empresa)
            ctx.update({'viagem': viagem, 'erro_km_inicial': erro_km_inicial, 'post': request.POST})
            return render(request, 'frota/viagem_form.html', ctx)
        if viagem.veiculo.status != Veiculo.Status.ATIVO:
            ctx = _ctx_viagem(request.empresa)
            ctx['viagem'] = viagem
            ctx['erro_veiculo'] = f'Veículo {viagem.veiculo.placa} está "{viagem.veiculo.get_status_display()}" e não pode ser usado em viagens.'
            ctx['post'] = request.POST
            return render(request, 'frota/viagem_form.html', ctx)
        viagem.motorista  = get_object_or_404(Motorista, pk=motorista_pk, empresa=request.empresa) if motorista_pk else None
        if viagem.motorista and viagem.motorista.cnh_vencida:
            messages.warning(request, f'Atenção: CNH de {viagem.motorista.nome} está vencida desde {viagem.motorista.cnh_validade:%d/%m/%Y}.')
        elif viagem.motorista and viagem.motorista.cnh_vencendo:
            messages.warning(request, f'Atenção: CNH de {viagem.motorista.nome} vence em {viagem.motorista.cnh_validade:%d/%m/%Y}.')
        viagem.origem     = request.POST.get('origem', '')
        viagem.destino    = request.POST.get('destino', '')
        viagem.saida      = request.POST.get('saida')
        viagem.retorno    = request.POST.get('retorno') or None
        viagem.km_inicial = km_inicial
        viagem.km_final   = km_final
        viagem.status     = request.POST.get('status', viagem.status)
        viagem.observacoes = request.POST.get('observacoes', '')
        viagem.ajudante1_nome      = request.POST.get('ajudante1_nome', '')
        viagem.ajudante1_telefone  = request.POST.get('ajudante1_telefone', '')
        viagem.ajudante2_nome      = request.POST.get('ajudante2_nome', '')
        viagem.ajudante2_telefone  = request.POST.get('ajudante2_telefone', '')
        viagem.ajudante3_nome      = request.POST.get('ajudante3_nome', '')
        viagem.ajudante3_telefone  = request.POST.get('ajudante3_telefone', '')
        viagem.save()
        if viagem.status == Viagem.Status.CONCLUIDA and km_final:
            viagem.veiculo.atualizar_km(km_final)
        return redirect('frota_viagens')
    return render(request, 'frota/viagem_form.html', {
        **_ctx_viagem(request.empresa), 'viagem': viagem,
    })


@login_required
@requer_empresa
def viagem_encerrar(request, pk):
    viagem = get_object_or_404(Viagem, pk=pk, veiculo__empresa=request.empresa,
                               status=Viagem.Status.EM_ANDAMENTO)
    if request.method == 'POST':
        from datetime import datetime
        km_final = request.POST.get('km_final') or None
        if km_final and int(km_final) < viagem.km_inicial:
            messages.error(request, 'KM final não pode ser menor que KM inicial.')
            return render(request, 'frota/viagem_encerrar.html', {'viagem': viagem})
        viagem.km_final = km_final
        viagem.retorno  = request.POST.get('retorno') or None
        viagem.status   = Viagem.Status.CONCLUIDA
        viagem.save()
        if km_final:
            viagem.veiculo.atualizar_km(km_final)
        messages.success(request, f'Viagem encerrada com sucesso.')
        return redirect('frota_viagens')
    return render(request, 'frota/viagem_encerrar.html', {'viagem': viagem})


@login_required
@requer_empresa
def viagem_delete(request, pk):
    viagem = get_object_or_404(Viagem, pk=pk, veiculo__empresa=request.empresa)
    if request.method == 'POST':
        viagem.delete()
        return redirect('frota_viagens')
    return render(request, 'frota/confirm_delete.html', {
        'objeto': viagem, 'cancelar_url': 'frota_viagens',
    })


@require_POST
@login_required
@requer_empresa
def viagens_bulk_delete(request):
    ids = request.POST.getlist('ids')
    selecionados = len(ids)
    if not selecionados:
        messages.info(request, 'Nenhuma viagem selecionada.')
        return redirect('frota_viagens')

    qs = Viagem.objects.filter(pk__in=ids, veiculo__empresa=request.empresa)
    deletaveis = qs.count()
    with transaction.atomic():
        qs.delete()

    if deletaveis:
        messages.success(request, f'{deletaveis} viagem(ns) excluída(s).')
    if deletaveis < selecionados:
        messages.warning(request, f'{selecionados - deletaveis} item(ns) ignorado(s) (sem permissão ou inexistentes).')
    return redirect('frota_viagens')


# ── Motoristas ─────────────────────────────────────────────────────────────────

@login_required
@requer_empresa
def motorista_list(request):
    motoristas = Motorista.objects.filter(empresa=request.empresa)
    return render(request, 'frota/motorista_list.html', {
        'motoristas': motoristas,
        'status_choices': Motorista.Status,
    })


@login_required
@requer_empresa
def motorista_create(request):
    if request.method == 'POST':
        cpf = request.POST.get('cpf', '').strip()
        # Dois motoristas sem CPF violariam o unique_together — usa None
        cpf = cpf if cpf else None
        from django.db import IntegrityError
        try:
            Motorista.objects.create(
                empresa=request.empresa,
                nome=request.POST.get('nome', '').strip(),
                cpf=cpf,
                telefone=request.POST.get('telefone', '').strip(),
                cnh_numero=request.POST.get('cnh_numero', '').strip(),
                cnh_categoria=request.POST.get('cnh_categoria', ''),
                cnh_validade=request.POST.get('cnh_validade') or None,
                status=request.POST.get('status', Motorista.Status.ATIVO),
                observacoes=request.POST.get('observacoes', ''),
            )
            return redirect('frota_motoristas')
        except IntegrityError:
            messages.error(request, 'Já existe um motorista cadastrado com este CPF.')
            return render(request, 'frota/motorista_form.html', {
                'status_choices': Motorista.Status,
                'categoria_choices': Motorista.CategoriaCNH,
                'motorista': None,
                'erros': {},
                'post': request.POST,
            })
    return render(request, 'frota/motorista_form.html', {
        'status_choices': Motorista.Status,
        'categoria_choices': Motorista.CategoriaCNH,
        'motorista': None,
        'erros': {},
    })


@login_required
@requer_empresa
def motorista_edit(request, pk):
    motorista = get_object_or_404(Motorista, pk=pk, empresa=request.empresa)
    if request.method == 'POST':
        motorista.nome          = request.POST.get('nome', '').strip()
        motorista.cpf           = request.POST.get('cpf', '').strip()
        motorista.telefone      = request.POST.get('telefone', '').strip()
        motorista.cnh_numero    = request.POST.get('cnh_numero', '').strip()
        motorista.cnh_categoria = request.POST.get('cnh_categoria', '')
        motorista.cnh_validade  = request.POST.get('cnh_validade') or None
        motorista.status        = request.POST.get('status', motorista.status)
        motorista.observacoes   = request.POST.get('observacoes', '')
        motorista.save()
        return redirect('frota_motoristas')
    return render(request, 'frota/motorista_form.html', {
        'motorista': motorista,
        'status_choices': Motorista.Status,
        'categoria_choices': Motorista.CategoriaCNH,
        'erros': {},
    })


@login_required
@requer_empresa
def motorista_delete(request, pk):
    motorista = get_object_or_404(Motorista, pk=pk, empresa=request.empresa)
    if request.method == 'POST':
        motorista.delete()
        return redirect('frota_motoristas')
    return render(request, 'frota/confirm_delete.html', {
        'objeto': motorista, 'cancelar_url': 'frota_motoristas',
    })
