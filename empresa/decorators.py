from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def requer_empresa(view_func):
    """Redireciona para setup se o usuário não tiver empresa ativa associada."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.empresa:
            messages.warning(request, 'Configure sua empresa antes de continuar.')
            return redirect('setup_empresa')
        return view_func(request, *args, **kwargs)
    return wrapper


def requer_admin(view_func):
    """Exige perfil admin dentro da empresa."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.membro or request.membro.perfil != 'admin':
            messages.error(request, 'Acesso restrito a administradores.')
            return redirect('financeiro_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def requer_superuser(view_func):
    """Acesso exclusivo ao superusuário do sistema."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            messages.error(request, 'Acesso restrito.')
            return redirect('financeiro_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper
