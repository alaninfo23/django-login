class EmpresaMiddleware:
    """Injeta request.empresa e request.membro para usuários autenticados."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.empresa = None
        request.membro  = None
        if request.user.is_authenticated:
            membro = (request.user.membros
                      .select_related('empresa')
                      .filter(ativo=True, empresa__ativa=True)
                      .order_by('id')
                      .first())
            if membro:
                request.empresa = membro.empresa
                request.membro  = membro
        return self.get_response(request)
