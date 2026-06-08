from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render

from empresa.decorators import requer_admin
from .models import Asset

FIELDS = ['name', 'asset_type', 'acquisition_value', 'purchase_date', 'status', 'location', 'notes']
NULLABLE_FIELDS = {'purchase_date'}

def _parse_post(post):
    return {f: (post.get(f) or None) if f in NULLABLE_FIELDS else (post.get(f) or '') for f in FIELDS}


def _owned_or_404(pk, user):
    return get_object_or_404(Asset, pk=pk, user=user)


@login_required
def home(request):
    return render(request, 'assets/home.html')


@login_required
def asset_list(request):
    qs = Asset.objects.filter(user=request.user)

    q           = request.GET.get('q', '').strip()
    asset_type  = request.GET.get('asset_type', '')
    status      = request.GET.get('status', '')
    order       = request.GET.get('order', '-created_at')

    if q:
        qs = qs.filter(name__icontains=q)
    if asset_type:
        qs = qs.filter(asset_type=asset_type)
    if status:
        qs = qs.filter(status=status)

    VALID_ORDERS = {'acquisition_value', '-acquisition_value', 'purchase_date', '-purchase_date', 'created_at', '-created_at'}
    if order not in VALID_ORDERS:
        order = '-created_at'
    qs = qs.order_by(order)

    return render(request, 'assets/list.html', {
        'assets':      qs,
        'asset_types': Asset.AssetType,
        'statuses':    Asset.Status,
        'filters':     {'q': q, 'asset_type': asset_type, 'status': status, 'order': order},
    })


@login_required
def asset_create(request):
    if request.method == 'POST':
        Asset.objects.create(user=request.user, **_parse_post(request.POST))
        return redirect('asset_list')
    return render(request, 'assets/form.html', {'asset': None, 'asset_types': Asset.AssetType, 'statuses': Asset.Status})


@login_required
@requer_admin
def asset_edit(request, pk):
    asset = _owned_or_404(pk, request.user)
    if request.method == 'POST':
        for f, v in _parse_post(request.POST).items():
            setattr(asset, f, v)
        asset.save()
        return redirect('asset_list')
    return render(request, 'assets/form.html', {'asset': asset, 'asset_types': Asset.AssetType, 'statuses': Asset.Status})


@login_required
@requer_admin
def asset_delete(request, pk):
    asset = _owned_or_404(pk, request.user)
    if request.method == 'POST':
        asset.delete()
        return redirect('asset_list')
    return render(request, 'assets/confirm_delete.html', {'asset': asset})


@login_required
def dashboard(request):
    qs = Asset.objects.filter(user=request.user)

    totals = qs.aggregate(total=Count('id'), patrimonio=Sum('acquisition_value'))

    by_type   = qs.values('asset_type').annotate(count=Count('id')).order_by('-count')
    by_status = qs.values('status').annotate(count=Count('id')).order_by('-count')

    # resolve display labels
    type_labels   = dict(Asset.AssetType.choices)
    status_labels = dict(Asset.Status.choices)
    for row in by_type:
        row['label'] = type_labels.get(row['asset_type'], row['asset_type'])
    for row in by_status:
        row['label'] = status_labels.get(row['status'], row['status'])

    return render(request, 'assets/dashboard.html', {
        'total':      totals['total'] or 0,
        'patrimonio': totals['patrimonio'] or 0,
        'by_type':    by_type,
        'by_status':  by_status,
    })
