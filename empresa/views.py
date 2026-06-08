from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from .decorators import requer_admin, requer_empresa, requer_superuser
from .models import Empresa, MembroEmpresa


# ── Painel Super-Admin ────────────────────────────────────────────────────────

@login_required
@requer_superuser
def superadmin_empresas(request):
    empresas = Empresa.objects.all().order_by('nome')
    return render(request, 'empresa/superadmin/empresas.html', {'empresas': empresas})


@login_required
@requer_superuser
def superadmin_empresa_criar(request):
    if request.method == 'POST':
        nome     = request.POST.get('nome', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        email    = request.POST.get('email', '').strip()

        if not nome or not username or not password:
            messages.error(request, 'Nome da empresa, username e senha são obrigatórios.')
            return redirect('superadmin_empresa_criar')

        if User.objects.filter(username=username).exists():
            messages.error(request, f'Usuário "{username}" já existe.')
            return redirect('superadmin_empresa_criar')

        slug = slugify(nome)[:60] or 'empresa'
        base, i = slug, 1
        while Empresa.objects.filter(slug=slug).exists():
            slug = f'{base}-{i}'; i += 1

        empresa = Empresa.objects.create(nome=nome, slug=slug)
        if request.FILES.get('logo'):
            empresa.logo = request.FILES['logo']
            empresa.save()
        user    = User.objects.create_user(username=username, password=password, email=email)
        MembroEmpresa.objects.create(empresa=empresa, user=user, perfil='admin')
        messages.success(request, f'Empresa "{nome}" criada com admin "{username}".')
        return redirect('superadmin_empresas')

    return render(request, 'empresa/superadmin/criar_empresa.html')


@login_required
@requer_superuser
def superadmin_empresa_editar(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        if nome:
            empresa.nome = nome
        if request.FILES.get('logo'):
            empresa.logo = request.FILES['logo']
        elif request.POST.get('remover_logo'):
            empresa.logo = None
        empresa.save()
        messages.success(request, 'Empresa atualizada.')
        return redirect('superadmin_empresa_detalhe', pk=pk)
    return render(request, 'empresa/superadmin/editar_empresa.html', {'empresa': empresa})


@login_required
@requer_superuser
def superadmin_empresa_detalhe(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    membros = empresa.membros.select_related('user').order_by('user__username')
    return render(request, 'empresa/superadmin/empresa_detalhe.html', {
        'empresa': empresa, 'membros': membros
    })


@login_required
@requer_superuser
def superadmin_membro_editar(request, pk):
    membro = get_object_or_404(MembroEmpresa, pk=pk)
    if request.method == 'POST':
        membro.perfil = request.POST.get('perfil', membro.perfil)
        membro.ativo  = request.POST.get('ativo') == '1'
        membro.save()
        messages.success(request, 'Membro atualizado.')
        return redirect('superadmin_empresa_detalhe', pk=membro.empresa_id)
    return render(request, 'empresa/superadmin/membro_editar.html', {
        'membro': membro, 'perfis': MembroEmpresa.Perfil
    })


@login_required
@requer_superuser
def superadmin_empresa_toggle(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    if request.method == 'POST':
        empresa.ativa = not empresa.ativa
        empresa.save()
        status = 'ativada' if empresa.ativa else 'desativada'
        messages.success(request, f'Empresa "{empresa.nome}" {status}.')
    return redirect('superadmin_empresas')


@login_required
def setup_empresa(request):
    """Tela para criar ou ingressar em uma empresa."""
    # Se já tem empresa, vai pro dashboard
    if request.empresa:
        return redirect('financeiro_dashboard')

    if request.method == 'POST':
        acao = request.POST.get('acao')

        if acao == 'criar':
            nome = request.POST.get('nome', '').strip()
            if nome:
                slug = slugify(nome)[:60] or 'empresa'
                # garante slug único
                base, i = slug, 1
                while Empresa.objects.filter(slug=slug).exists():
                    slug = f'{base}-{i}'; i += 1
                empresa = Empresa.objects.create(nome=nome, slug=slug)
                MembroEmpresa.objects.create(empresa=empresa, user=request.user, perfil='admin')
                messages.success(request, f'Empresa "{nome}" criada com sucesso!')
                return redirect('financeiro_dashboard')
            else:
                messages.error(request, 'Informe o nome da empresa.')

    return render(request, 'empresa/setup.html')


@login_required
@requer_empresa
@requer_admin
def usuarios_list(request):
    membros = MembroEmpresa.objects.filter(empresa=request.empresa).select_related('user').order_by('user__username')
    return render(request, 'empresa/usuarios.html', {'membros': membros})


@login_required
@requer_empresa
@requer_admin
def usuario_convidar(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        perfil   = request.POST.get('perfil', 'operador')
        email    = request.POST.get('email', '').strip()

        if not username or not password:
            messages.error(request, 'Username e senha são obrigatórios.')
            return redirect('usuario_convidar')

        if User.objects.filter(username=username).exists():
            messages.error(request, f'Usuário "{username}" já existe no sistema.')
            return redirect('usuario_convidar')

        user = User.objects.create_user(username=username, password=password, email=email)
        MembroEmpresa.objects.create(empresa=request.empresa, user=user, perfil=perfil)
        messages.success(request, f'Usuário "{username}" criado e adicionado como {perfil}.')
        return redirect('usuarios_list')

    return render(request, 'empresa/convidar.html', {'perfis': MembroEmpresa.Perfil})


@login_required
@requer_empresa
@requer_admin
def usuario_editar(request, pk):
    membro = get_object_or_404(MembroEmpresa, pk=pk, empresa=request.empresa)
    if request.method == 'POST':
        membro.perfil = request.POST.get('perfil', membro.perfil)
        membro.ativo  = request.POST.get('ativo') == '1'
        membro.save()
        messages.success(request, 'Membro atualizado.')
        return redirect('usuarios_list')
    return render(request, 'empresa/editar_usuario.html', {'membro': membro, 'perfis': MembroEmpresa.Perfil})
