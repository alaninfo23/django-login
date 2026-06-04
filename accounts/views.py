from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 300  # 5 minutos


def _check_lockout(request):
    attempts = request.session.get('login_attempts', 0)
    lockout_until = request.session.get('lockout_until')
    if lockout_until:
        if timezone.now().timestamp() < lockout_until:
            remaining = int(lockout_until - timezone.now().timestamp())
            return True, f'Muitas tentativas. Tente novamente em {remaining}s.'
        else:
            request.session.pop('lockout_until', None)
            request.session['login_attempts'] = 0
    return False, None


def login_view(request):
    error = request.session.pop('login_error', None)
    if request.method == 'POST':
        locked, msg = _check_lockout(request)
        if locked:
            request.session['login_error'] = msg
            return redirect('login')

        user = authenticate(request,
                            username=request.POST.get('username', ''),
                            password=request.POST.get('password', ''))
        if user:
            request.session['login_attempts'] = 0
            login(request, user)
            return redirect(settings.LOGIN_REDIRECT_URL)

        attempts = request.session.get('login_attempts', 0) + 1
        request.session['login_attempts'] = attempts
        if attempts >= MAX_ATTEMPTS:
            request.session['lockout_until'] = timezone.now().timestamp() + LOCKOUT_SECONDS
            request.session['login_error'] = f'Conta bloqueada por {LOCKOUT_SECONDS // 60} minutos após {MAX_ATTEMPTS} tentativas.'
        else:
            request.session['login_error'] = f'Usuário ou senha inválidos. ({attempts}/{MAX_ATTEMPTS} tentativas)'
        return redirect('login')

    return render(request, 'accounts/login.html', {'error': error})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
    return redirect('login')


@login_required
def home_view(request):
    return render(request, 'accounts/home.html')
