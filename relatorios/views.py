import io
from datetime import date, datetime

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render

from assets.models import Asset
from empresa.decorators import requer_empresa
from financeiro.models import CentroCusto, Despesa, FormaPagamento, Repasse, SubGrupo


# ── helpers ────────────────────────────────────────────────────────────────────

def _fmt_valor(v):
    """Formata Decimal/float para R$ 1.234,56"""
    return 'R$ {:,.2f}'.format(v).replace(',', 'X').replace('.', ',').replace('X', '.')


def _fmt_data(d):
    """Formata date/str para dd/mm/yyyy"""
    if not d:
        return ''
    if hasattr(d, 'strftime'):
        return d.strftime('%d/%m/%Y')
    try:
        return datetime.strptime(str(d), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return str(d)


def _parse_periodo(request):
    de_str  = request.GET.get('de', '')
    ate_str = request.GET.get('ate', '')
    try:
        de  = datetime.strptime(de_str,  '%Y-%m-%d').date()
        ate = datetime.strptime(ate_str, '%Y-%m-%d').date()
    except ValueError:
        hoje = date.today()
        de   = hoje.replace(day=1)
        ate  = hoje
    return de, ate


def _pdf_resp(filename):
    r = HttpResponse(content_type='application/pdf')
    r['Content-Disposition'] = f'attachment; filename="{filename}"'
    return r


def _excel_resp(filename):
    r = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    r['Content-Disposition'] = f'attachment; filename="{filename}"'
    return r


def _build_pdf(title, headers, rows, totais=None, col_widths=None, logo_path=None):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    data   = [headers] + rows + ([totais] if totais else [])
    page_w = landscape(A4)[0] - 3*cm
    if col_widths:
        total_parts = sum(col_widths)
        widths = [page_w * (p / total_parts) for p in col_widths]
    else:
        widths = [page_w / len(headers)] * len(headers)
    t = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e1b4b')),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1,-1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('GRID',       (0, 0), (-1,-1), 0.3, colors.HexColor('#e2e8f0')),
        ('VALIGN',     (0, 0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1,-1), 5),
        ('BOTTOMPADDING', (0, 0), (-1,-1), 5),
    ]
    if totais:
        style += [('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#e0e7ff')),
                  ('FONTNAME',   (0,-1), (-1,-1), 'Helvetica-Bold')]
    t.setStyle(TableStyle(style))

    story = []
    if logo_path:
        try:
            img = Image(logo_path, height=1.2*cm, width=3.5*cm, kind='proportional')
            story.append(img)
            story.append(Spacer(1, .2*cm))
        except Exception:
            pass
    story += [Paragraph(title, styles['Title']), Spacer(1, .4*cm), t]
    doc.build(story)
    return buf.getvalue()


def _build_excel(title, headers, rows, totais=None, min_widths=None):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = title[:31].replace('/', '-')
    ws.append([title])
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
    ws['A1'].font = Font(bold=True, size=13)
    ws.append([])
    ws.append(headers)
    hfill = PatternFill('solid', fgColor='1e1b4b')
    for cell in ws[ws.max_row]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = hfill
        cell.alignment = Alignment(horizontal='center')
    for i, row in enumerate(rows):
        ws.append(row)
        if i % 2 == 1:
            for cell in ws[ws.max_row]:
                cell.fill = PatternFill('solid', fgColor='F8FAFC')
    if totais:
        ws.append(totais)
        for cell in ws[ws.max_row]:
            cell.font = Font(bold=True)
            cell.fill = PatternFill('solid', fgColor='E0E7FF')
    for i, col in enumerate(ws.columns):
        try:
            from openpyxl.utils import get_column_letter
            letter = get_column_letter(i + 1)
            vals = []
            for c in col:
                try:
                    vals.append(len(str(c.value or '')))
                except Exception:
                    pass
            ml = max(vals) if vals else 10
            w = min(ml + 4, 60)
            if min_widths and i < len(min_widths):
                w = max(w, min_widths[i])
            ws.column_dimensions[letter].width = w
        except Exception:
            pass
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ── central view ───────────────────────────────────────────────────────────────

@login_required
@requer_empresa
def central(request):
    hoje = date.today()
    # padrão: do 1º dia do mês anterior até hoje
    if hoje.month == 1:
        de_default = hoje.replace(year=hoje.year - 1, month=12, day=1)
    else:
        de_default = hoje.replace(month=hoje.month - 1, day=1)
    de  = request.GET.get('de',  de_default.isoformat())
    ate = request.GET.get('ate', hoje.isoformat())
    modulo = request.GET.get('modulo', 'patrimonial')

    empresa = request.empresa
    centros   = CentroCusto.objects.filter(empresa=empresa).values_list('nome', flat=True)
    subgrupos = SubGrupo.objects.filter(empresa=empresa).values_list('nome', flat=True)
    formas    = FormaPagamento.objects.filter(empresa=empresa).values_list('nome', flat=True)

    return render(request, 'relatorios/central.html', {
        'de': de, 'ate': ate, 'modulo': modulo,
        'asset_types': Asset.AssetType.choices,
        'asset_statuses': Asset.Status.choices,
        'centros': centros, 'subgrupos': subgrupos, 'formas': formas,
    })


# ── PATRIMONIAL ────────────────────────────────────────────────────────────────

@login_required
@requer_empresa
def patrimonial_pdf(request):
    de, ate = _parse_periodo(request)
    subtipo  = request.GET.get('subtipo', '')
    status   = request.GET.get('status', '')

    qs = Asset.objects.filter(empresa=request.empresa, purchase_date__range=(de, ate))
    if subtipo:
        qs = qs.filter(asset_type=subtipo)
    if status:
        qs = qs.filter(status=status)

    if not qs.exists():
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.warning(request, 'Nenhum dado encontrado para os filtros selecionados.')
        return redirect(request.META.get('HTTP_REFERER', '/relatorios/'))

    headers = ['Nome', 'Tipo', 'Valor (R$)', 'Data Compra', 'Status', 'Local']
    rows    = [[a.name, a.get_asset_type_display(), _fmt_valor(a.acquisition_value),
                _fmt_data(a.purchase_date), a.get_status_display(), a.location] for a in qs]
    total   = qs.aggregate(v=Sum('acquisition_value'))['v'] or 0
    totais  = ['TOTAL', '', _fmt_valor(total), '', '', '']

    label = f'{de.strftime("%d/%m/%Y")} a {ate.strftime("%d/%m/%Y")}'
    logo  = request.empresa.logo.path if request.empresa.logo else None
    pdf = _build_pdf(f'Relatório Patrimonial — {label}', headers, rows, totais,
                     col_widths=[3, 2, 2, 1.5, 1.5, 2], logo_path=logo)
    resp = _pdf_resp(f'patrimonial_{de}_{ate}.pdf')
    resp.write(pdf)
    return resp


@login_required
@requer_empresa
def patrimonial_excel(request):
    de, ate = _parse_periodo(request)
    subtipo  = request.GET.get('subtipo', '')
    status   = request.GET.get('status', '')

    qs = Asset.objects.filter(empresa=request.empresa, purchase_date__range=(de, ate))
    if subtipo:
        qs = qs.filter(asset_type=subtipo)
    if status:
        qs = qs.filter(status=status)

    if not qs.exists():
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.warning(request, 'Nenhum dado encontrado para os filtros selecionados.')
        return redirect(request.META.get('HTTP_REFERER', '/relatorios/'))

    headers = ['Nome', 'Tipo', 'Valor (R$)', 'Data Compra', 'Status', 'Local']
    rows    = [[a.name, a.get_asset_type_display(), _fmt_valor(a.acquisition_value),
                _fmt_data(a.purchase_date), a.get_status_display(), a.location] for a in qs]
    total   = qs.aggregate(v=Sum('acquisition_value'))['v'] or 0
    totais  = ['TOTAL', '', _fmt_valor(total), '', '', '']

    label = f'{de.strftime("%d/%m/%Y")} a {ate.strftime("%d/%m/%Y")}'
    # Nome, Tipo, Valor, Data, Status, Local
    data = _build_excel(f'Patrimonial — {label}', headers, rows, totais,
                        min_widths=[35, 22, 16, 12, 12, 20])
    resp = _excel_resp(f'patrimonial_{de}_{ate}.xlsx')
    resp.write(data)
    return resp


# ── FINANCEIRO ─────────────────────────────────────────────────────────────────

@login_required
@requer_empresa
def financeiro_pdf(request):
    de, ate  = _parse_periodo(request)
    subtipo  = request.GET.get('subtipo', 'despesas')  # despesas | repasses | ambos
    centro   = request.GET.get('centro', '')
    subgrupo = request.GET.get('subgrupo', '')
    forma    = request.GET.get('forma', '')

    label = f'{de.strftime("%d/%m/%Y")} a {ate.strftime("%d/%m/%Y")}'

    import io as _io
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf    = _io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=landscape(A4),
                               leftMargin=1.5*cm, rightMargin=1.5*cm,
                               topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    page_w = landscape(A4)[0] - 3*cm
    story  = []
    logo_path = request.empresa.logo.path if request.empresa.logo else None
    if logo_path:
        from reportlab.platypus import Image as RLImage
        try:
            story.append(RLImage(logo_path, height=1.2*cm, width=3.5*cm, kind='proportional'))
            story.append(Spacer(1, .2*cm))
        except Exception:
            pass
    story += [Paragraph(f'Relatório Financeiro — {label}', styles['Title']), Spacer(1, .4*cm)]

    def _tbl(headers, rows, totais=None, col_widths=None):
        data = [headers] + rows + ([totais] if totais else [])
        if col_widths:
            total_parts = sum(col_widths)
            widths = [page_w * (p / total_parts) for p in col_widths]
        else:
            widths = [page_w / len(headers)] * len(headers)
        t = Table(data, colWidths=widths, repeatRows=1)
        s = [('BACKGROUND',(0,0),(-1,0),colors.HexColor('#1e1b4b')),
             ('TEXTCOLOR',(0,0),(-1,0),colors.white),
             ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
             ('FONTSIZE',(0,0),(-1,-1),8),
             ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f8fafc')]),
             ('GRID',(0,0),(-1,-1),.3,colors.HexColor('#e2e8f0')),
             ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]
        if totais:
            s += [('BACKGROUND',(0,-1),(-1,-1),colors.HexColor('#e0e7ff')),
                  ('FONTNAME',(0,-1),(-1,-1),'Helvetica-Bold')]
        t.setStyle(TableStyle(s))
        return t

    has_data = False
    if subtipo in ('despesas', 'ambos'):
        qs = Despesa.objects.filter(empresa=request.empresa, data__range=(de, ate))
        if centro:   qs = qs.filter(centro_custo=centro)
        if subgrupo: qs = qs.filter(subgrupo=subgrupo)
        if forma:    qs = qs.filter(forma_pagamento=forma)
        if qs.exists():
            has_data = True
            rows = [[_fmt_data(d.data), d.centro_custo, d.subgrupo, d.descricao,
                     d.forma_pagamento, d.get_situacao_display(), _fmt_valor(d.valor)] for d in qs]
            total = qs.aggregate(v=Sum('valor'))['v'] or 0
            # Data=1, Centro=2.5, SubGrupo=2.5, Descrição=4.5, FormaPag=1.5, Situação=1, Valor=1
            story += [Paragraph('Despesas', styles['Heading2']), Spacer(1, .2*cm),
                      _tbl(['Data','Centro','SubGrupo','Descrição','Forma Pag.','Situação','Valor'],
                           rows, ['','','','','','TOTAL', _fmt_valor(total)],
                           col_widths=[1, 2.5, 2.5, 4.5, 1.5, 1, 1]),
                      Spacer(1, .5*cm)]

    if subtipo in ('repasses', 'ambos'):
        qs = Repasse.objects.filter(empresa=request.empresa, data__range=(de, ate))
        if qs.exists():
            has_data = True
            rows = [[_fmt_data(r.data), r.get_tipo_display(), r.origem, r.destino,
                     _fmt_valor(r.valor), r.descricao] for r in qs]
            total = qs.aggregate(v=Sum('valor'))['v'] or 0
            story += [Paragraph('Repasses', styles['Heading2']), Spacer(1, .2*cm),
                      _tbl(['Data','Tipo','Origem','Destino','Valor','Descrição'],
                           rows, ['','','','TOTAL', _fmt_valor(total), ''],
                           col_widths=[1, 1.5, 2, 2, 1.5, 4]),
                      Spacer(1, .5*cm)]

    if not has_data:
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.warning(request, 'Nenhum dado encontrado para os filtros selecionados.')
        return redirect(request.META.get('HTTP_REFERER', '/relatorios/'))

    doc.build(story)
    resp = _pdf_resp(f'financeiro_{de}_{ate}.pdf')
    resp.write(buf.getvalue())
    return resp


@login_required
@requer_empresa
def financeiro_excel(request):
    de, ate  = _parse_periodo(request)
    subtipo  = request.GET.get('subtipo', 'despesas')
    centro   = request.GET.get('centro', '')
    subgrupo = request.GET.get('subgrupo', '')
    forma    = request.GET.get('forma', '')

    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    label = f'{de.strftime("%d/%m/%Y")} a {ate.strftime("%d/%m/%Y")}'
    wb = Workbook()
    wb.remove(wb.active)

    def _sheet(ws, headers, rows, totais=None, min_widths=None):
        ws.append([ws.title])
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
        ws['A1'].font = Font(bold=True, size=13)
        ws.append([])
        ws.append(headers)
        hfill = PatternFill('solid', fgColor='1e1b4b')
        for c in ws[ws.max_row]:
            c.font = Font(bold=True, color='FFFFFF')
            c.fill = hfill
            c.alignment = Alignment(horizontal='center')
        for i, row in enumerate(rows):
            ws.append(row)
            if i % 2 == 1:
                for c in ws[ws.max_row]:
                    c.fill = PatternFill('solid', fgColor='F8FAFC')
        if totais:
            ws.append(totais)
            for c in ws[ws.max_row]:
                c.font = Font(bold=True)
                c.fill = PatternFill('solid', fgColor='E0E7FF')
        for i, col in enumerate(ws.columns):
            try:
                from openpyxl.utils import get_column_letter
                letter = get_column_letter(i + 1)
                ml = max((len(str(c.value or '')) for c in col if hasattr(c, 'value') and not hasattr(c, 'parent') or True), default=10)
                # ignora MergedCell (sem atributo 'value' acessível) usando valor da célula diretamente
                vals = []
                for c in col:
                    try:
                        vals.append(len(str(c.value or '')))
                    except Exception:
                        pass
                ml = max(vals) if vals else 10
                w = min(ml + 4, 60)
                if min_widths and i < len(min_widths):
                    w = max(w, min_widths[i])
                ws.column_dimensions[letter].width = w
            except Exception:
                pass

    if subtipo in ('despesas', 'ambos'):
        qs = Despesa.objects.filter(empresa=request.empresa, data__range=(de, ate))
        if centro:   qs = qs.filter(centro_custo=centro)
        if subgrupo: qs = qs.filter(subgrupo=subgrupo)
        if forma:    qs = qs.filter(forma_pagamento=forma)
    has_data = False
    if subtipo in ('despesas', 'ambos'):
        qs = Despesa.objects.filter(empresa=request.empresa, data__range=(de, ate))
        if centro:   qs = qs.filter(centro_custo=centro)
        if subgrupo: qs = qs.filter(subgrupo=subgrupo)
        if forma:    qs = qs.filter(forma_pagamento=forma)
        if qs.exists():
            has_data = True
            rows  = [[_fmt_data(d.data), d.centro_custo, d.subgrupo, d.descricao,
                      d.forma_pagamento, d.get_situacao_display(), _fmt_valor(d.valor)] for d in qs]
            total = qs.aggregate(v=Sum('valor'))['v'] or 0
            ws = wb.create_sheet(f'Despesas')
            # Data, Centro, SubGrupo, Descrição, FormaPag, Situação, Valor
            _sheet(ws, ['Data','Centro','SubGrupo','Descrição','Forma Pag.','Situação','Valor (R$)'],
                   rows, ['','','','','','TOTAL', _fmt_valor(total)],
                   min_widths=[12, 25, 25, 45, 22, 12, 16])

    if subtipo in ('repasses', 'ambos'):
        qs = Repasse.objects.filter(empresa=request.empresa, data__range=(de, ate))
        if qs.exists():
            has_data = True
            rows  = [[_fmt_data(r.data), r.get_tipo_display(), r.origem, r.destino,
                      _fmt_valor(r.valor), r.descricao] for r in qs]
            total = qs.aggregate(v=Sum('valor'))['v'] or 0
            ws = wb.create_sheet('Repasses')
            # Data, Tipo, Origem, Destino, Valor, Descrição
            _sheet(ws, ['Data','Tipo','Origem','Destino','Valor (R$)','Descrição'],
                   rows, ['','','','TOTAL', _fmt_valor(total), ''],
                   min_widths=[12, 14, 25, 25, 16, 45])

    if not has_data:
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.warning(request, 'Nenhum dado encontrado para os filtros selecionados.')
        return redirect(request.META.get('HTTP_REFERER', '/relatorios/'))

    buf = io.BytesIO()
    wb.save(buf)
    resp = _excel_resp(f'financeiro_{de}_{ate}.xlsx')
    resp.write(buf.getvalue())
    return resp


# ── FROTAS (placeholder data — sem model ainda) ────────────────────────────────

@login_required
@requer_empresa
def frotas_pdf(request):
    de, ate = _parse_periodo(request)
    label   = f'{de.strftime("%d/%m/%Y")} a {ate.strftime("%d/%m/%Y")}'
    pdf = _build_pdf(f'Relatório de Frotas — {label}',
                     ['Módulo', 'Status'],
                     [['Frotas', 'Em desenvolvimento']],
                     None)
    resp = _pdf_resp(f'frotas_{de}_{ate}.pdf')
    resp.write(pdf)
    return resp


@login_required
@requer_empresa
def frotas_excel(request):
    de, ate = _parse_periodo(request)
    label   = f'{de.strftime("%d/%m/%Y")} a {ate.strftime("%d/%m/%Y")}'
    data = _build_excel(f'Frotas — {label}',
                        ['Módulo', 'Status'],
                        [['Frotas', 'Em desenvolvimento']],
                        None)
    resp = _excel_resp(f'frotas_{de}_{ate}.xlsx')
    resp.write(data)
    return resp
