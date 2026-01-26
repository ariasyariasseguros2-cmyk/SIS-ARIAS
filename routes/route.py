from flask import Blueprint, redirect, url_for, session, render_template, request, current_app, send_from_directory, jsonify
from werkzeug.utils import secure_filename
import os
from controllers.dashboard import get_dashboard_data, get_rows as get_dashboard_rows, get_dashboard_cards
from datetime import datetime, timedelta
from controllers.reportes.vencimientos_renovaciones import bp as vencimientos_bp

bp = Blueprint('main', __name__)

@bp.route('/cuotas/extract', methods=['POST'])
def extract_cuota():
    if 'file' not in request.files:
        return {'ok': False, 'error': 'No file part'}, 400
    file = request.files['file']
    if file.filename == '':
        return {'ok': False, 'error': 'No selected file'}, 400
    
    if file:
        try:
            filename = secure_filename(file.filename)
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)
            
            from controllers.cuotas.cuotas import extract_cuota_from_pdf
            data = extract_cuota_from_pdf(filepath)
            
            # Clean up
            if os.path.exists(filepath):
                os.remove(filepath)
                
            return {'ok': True, 'data': data}
        except Exception as e:
            return {'ok': False, 'error': str(e)}, 500
            
    return {'ok': False, 'error': 'Unknown error'}, 500

@bp.route('/cuotas/save', methods=['POST'])
def save_cuota_route():
    if 'user' not in session:
        return {'ok': False, 'error': 'Unauthorized'}, 401
    
    data = request.json
    if not data:
        return {'ok': False, 'error': 'No data'}, 400
        
    # Add user context
    data['usuario'] = session['user']
    
    from controllers.cuotas.cuotas import save_cuota
    success = save_cuota(data)
    
    if success:
        return {'ok': True}
    else:
        return {'ok': False, 'error': 'Database error'}, 500

@bp.route('/home')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    rows = get_dashboard_rows()
    chart = get_dashboard_data()
    cards = get_dashboard_cards()
    return render_template('view/dashboard.html', rows=rows, chart=chart, cards=cards)
from controllers.reportes.reporte_archivos_poliza import bp as reporte_archivos_bp
bp.register_blueprint(reporte_archivos_bp)

bp.register_blueprint(vencimientos_bp)

from controllers.reportes.reporte_archivos_cliente import bp as reporte_archivos_cliente_bp
bp.register_blueprint(reporte_archivos_cliente_bp)

@bp.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    rows = get_dashboard_rows()
    chart = get_dashboard_data()
    cards = get_dashboard_cards()
    return render_template('view/dashboard.html', rows=rows, chart=chart, cards=cards)

@bp.route('/menu/<page>')
def menu_page(page):
    if 'user' not in session:
        return redirect(url_for('login'))

    # Clientes → renderiza su plantilla dedicada con sus datos
    if page == 'clientes':
        from controllers.clientes.cliente import get_clientes_data
        data = get_clientes_data()

        # Pagination logic
        try:
            page_num = int(request.args.get('page') or 1)
        except ValueError:
            page_num = 1
        
        per_page = 20
        all_rows = data['rows']
        total = len(all_rows)
        pages = max(1, (total + per_page - 1) // per_page)
        
        # Ensure page_num is valid
        if pages > 0:
            page_num = max(1, min(page_num, pages))
        else:
            page_num = 1

        start = (page_num - 1) * per_page
        end = start + per_page
        sliced_rows = all_rows[start:end]

        pagination = {
            'page': page_num,
            'per_page': per_page,
            'total': total,
            'pages': pages,
            'has_prev': page_num > 1,
            'has_next': page_num < pages,
            'start_index': start + 1 if total > 0 else 0,
            'end_index': min(end, total)
        }

        from controllers.subagente import get_subagentes_abreviaciones

        subagentes_data = get_subagentes_abreviaciones()

        return render_template(
            'view/cliente/cliente.html',
            page='clientes',
            title=data['title'],
            rows=sliced_rows,
            filters=data['filters'],
            pagination=pagination,
            subagentes_abbrs=subagentes_data
        )

    # Clientes Anulados -> reutiliza la vista de clientes pero con datos anulados
    if page == 'clientes-anulados':
        from controllers.clientes.cliente import get_clientes_anulados_data
        data = get_clientes_anulados_data()

        try:
            page_num = int(request.args.get('page') or 1)
        except ValueError:
            page_num = 1

        per_page = 20
        all_rows = data['rows']
        total = len(all_rows)
        pages = max(1, (total + per_page - 1) // per_page)
        if pages > 0:
            page_num = max(1, min(page_num, pages))
        else:
            page_num = 1

        start = (page_num - 1) * per_page
        end = start + per_page
        sliced_rows = all_rows[start:end]

        pagination = {
            'page': page_num,
            'per_page': per_page,
            'total': total,
            'pages': pages,
            'has_prev': page_num > 1,
            'has_next': page_num < pages,
            'start_index': start + 1 if total > 0 else 0,
            'end_index': min(end, total)
        }

        from controllers.subagente import get_subagentes_abreviaciones
        subagentes_data = get_subagentes_abreviaciones()

        return render_template(
            'view/cliente/cliente.html',
            page='clientes-anulados',
            title=data['title'],
            rows=sliced_rows,
            filters=data['filters'],
            pagination=pagination,
            subagentes_abbrs=subagentes_data
        )

    # Estado de Cuenta - con filtros y búsqueda de cliente
    if page == 'clientes-estado-cuenta':
        from controllers.clientes.estado_cuenta import get_estado_cuenta_data
        from datetime import datetime
        data = get_estado_cuenta_data()
        return render_template(
            'view/cliente/estado-cuenta.html',
            page='clientes-estado-cuenta',
            cliente=data['cliente'],
            polizas=data['polizas'],
            totales=data['totales'],
            filtros_options=data['filtros_options'],
            filtros_aplicados=data['filtros_aplicados'],
            now=datetime.now()
        )

    # Pólizas → plantilla dedicada
    if page == 'polizas':
        from controllers.polizas import get_polizas_data
        # Tomar la selección almacenada en sesión (sin exponer en la URL)
        selected = session.get('selected_cliente') or {}
        data = get_polizas_data(selected)
        return render_template(
            'view/polizas.html',
            page='polizas',
            title=data['title'],
            rows=data['rows'],
            details=data.get('details', {})
        )

    # NUEVO: Listado de pólizas con paginación (global: todas las pólizas)
    if page == 'listado-poliza':
        from controllers.polizas import get_polizas_all
        data = get_polizas_all()

        try:
            page_num = int(request.args.get('page') or 1)
        except Exception:
            page_num = 1
        try:
            per_page = int(request.args.get('per_page') or 20)
        except Exception:
            per_page = 20

        total = len(data.get('rows', []))
        pages = max(1, (total + per_page - 1) // per_page)
        page_num = max(1, min(page_num, pages))
        start = (page_num - 1) * per_page
        end = start + per_page
        page_rows = data.get('rows', [])[start:end]

        pagination = {
            'page': page_num,
            'per_page': per_page,
            'total': total,
            'pages': pages,
            'has_prev': page_num > 1,
            'has_next': page_num < pages
        }

        return render_template(
            'view/listado-poliza.html',
            page='listado-poliza',
            page_rows=page_rows,
            pagination=pagination
        )

    # REPORTE: Archivos Póliza
    if page == 'reporte-archivos-poliza':
        return render_template('view/reportes/reporte-archivos-poliza.html')

    # REPORTE: Vencimientos y Renovaciones
    if page == 'vencimientos-renovaciones':
        return render_template('view/reportes/vencimientos-renovaciones.html')

    # Primas → plantilla dedicada
    if page == 'primas':
        from controllers.primas.primas import get_primas_data
        selected = session.get('selected_cliente') or {}
        numero_poliza = request.args.get('poliza') or None
        data = get_primas_data(selected, numero_poliza)
        return render_template(
            'view/primas/primas.html',
            page='primas',
            title=data['title'],
            rows=data['rows'],
            details=data.get('details', {})
        )
    # Cuotas → plantilla dedicada
    if page == 'cuotas':
        from controllers.cuotas.cuotas import get_cuotas_data
        selected = session.get('selected_cliente') or {}
        numero_poliza = request.args.get('poliza') or None
        data = get_cuotas_data(selected, numero_poliza)
        return render_template(
            'view/cuotas/cuotas.html',
            page='cuotas',
            title=data['title'],
            encabezado=data['encabezado'],
            resumen=data['resumen'],
            rows=data['rows'],
            total_monto=data['total_monto']
        )
    # NUEVO: Editar Póliza
    if page == 'editar-poliza':
        from controllers.editar_poliza import get_poliza_data
        from controllers.ramos import get_ramos
        from controllers.compania import get_aseguradoras
        from controllers.subagente import get_subagentes_abreviaciones
        from controllers.ejecutivos import get_ejecutivos
        from controllers.clientes.cliente import get_clientes_data

        poliza_id = request.args.get('id')
        if not poliza_id:
            return redirect(url_for('main.menu_page', page='listado-poliza'))
        
        poliza = get_poliza_data(poliza_id)
        if not poliza:
            return redirect(url_for('main.menu_page', page='listado-poliza'))

        return render_template(
            'view/editar-poliza.html',
            poliza=poliza,
            ramos_abbrs=get_ramos(),
            aseguradoras_rows=get_aseguradoras(),
            subagentes_abbrs=get_subagentes_abreviaciones(),
            ejecutivos_rows=get_ejecutivos(),
            clientes_data=get_clientes_data()
        )

    # NUEVO: Editar Primas (Misma tabla que polizas pero diferente vista)
    if page == 'editar-primas':
        from controllers.editar_poliza import get_poliza_data
        from controllers.ramos import get_ramos
        from controllers.compania import get_aseguradoras
        from controllers.subagente import get_subagentes_abreviaciones
        from controllers.clientes.cliente import get_clientes_data

        prima_id = request.args.get('id')
        if not prima_id:
            return redirect(url_for('main.menu_page', page='primas'))
        
        # Reuse get_poliza_data because Primas are Polizas rows
        prima = get_poliza_data(prima_id)
        if not prima:
            return redirect(url_for('main.menu_page', page='primas'))
        
        # Inject idPrima property if missing (it's actually idPoliza)
        if prima and 'idPrima' not in prima:
            prima['idPrima'] = prima.get('idPoliza')

        return render_template(
            'view/primas/editar-primas.html',
            prima=prima,
            # We pass similar helpers
            ramos_abbrs=get_ramos(),
            aseguradoras_rows=get_aseguradoras(),
            subagentes_abbrs=get_subagentes_abreviaciones(),
            clientes_data=get_clientes_data()
        )

        # NUEVO: Avisos - Documentos
    if page == 'avisos':
        from controllers.editar_poliza import get_poliza_data
        
        prima_id = request.args.get('id')
        if not prima_id:
             return redirect(url_for('main.menu_page', page='primas'))
        
        prima = get_poliza_data(prima_id)
        if not prima:
             return redirect(url_for('main.menu_page', page='primas'))

        # Prepare documents list
        documents = []
        pdf_url = prima.get('pdf_url')
        if pdf_url:
             documents.append({
                 'name': pdf_url, 
                 'url': pdf_url
             })

        return render_template(
            'view/avisos/avisos.html',
            page='avisos',
            prima=prima,
            documents=documents
        )


    # NUEVO: página “Añadir Póliza”
    if page == 'anadir-poliza':
        from controllers.addPoliza import get_rows
        from controllers.clientes.cliente import get_clientes_data
        from controllers.ramos import get_ramos
        from controllers.compania import get_aseguradoras
        from controllers.subagente import get_subagentes_abreviaciones  # NUEVO
        from controllers.ejecutivos import get_ejecutivos               # NUEVO
        cli_data = get_clientes_data()
        selected = session.get('selected_cliente') or {}

        # Hidratar datos faltantes del cliente seleccionado
        if not selected.get('subagente'):
            match = None
            sel_doc = (selected.get('n_doc') or '').strip()
            sel_name = (selected.get('razon_social') or selected.get('nombre') or '').strip()
            for c in cli_data['rows']:
                if sel_doc and c.get('n_doc') == sel_doc:
                    match = c
                    break
                if not match and sel_name and c.get('razon_social') == sel_name:
                    match = c
            if match:
                selected['subagente'] = match.get('subagente')
                # Completar nombre si faltaba
                selected['razon_social'] = selected.get('razon_social') or match.get('razon_social')

        return render_template(
            'view/anadir.poliza.html',
            rows=get_rows(),
            clientes_rows=cli_data['rows'],
            selected=selected,
            ramos_abbrs=get_ramos(),
            aseguradoras_rows=get_aseguradoras(),
            subagentes_abbrs=get_subagentes_abreviaciones(),  # NUEVO
            ejecutivos_rows=get_ejecutivos()                  # NUEVO
        )

    # NUEVO: Reporte Diario (acepta 'reporte-diaro' por el slug del menú)
    if page in ('reporte-diario', 'reporte-diaro'):
        from controllers.reporte_diario import get_filters
        filters = get_filters()
        return render_template(
            'view/reporte-diario.dashboard.html',
            page='reporte-diario',
            filters=filters
        )

    # Fallback: otras secciones usan el dashboard con etiqueta de sección
    rows = get_dashboard_rows()
    chart = get_dashboard_data()
    return render_template('view/layout_dashboard.html', rows=rows, chart=chart, page=page)

@bp.route('/upload', methods=['POST'])
def upload():
    if 'user' not in session:
        # En llamadas XHR, devolver JSON claro en vez de redirect HTML
        return {'error': 'No autenticado'}, 401

    if 'file' not in request.files:
        return {'error': 'No se envió archivo'}, 400

    file = request.files['file']
    if file.filename == '':
        return {'error': 'Nombre de archivo vacío'}, 400

    if not allowed_file(file.filename):
        return {'error': 'Tipo de archivo no permitido'}, 400

    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    
    # NUEVO: Guardar en subcarpeta 'polizas'
    polizas_folder = os.path.join(upload_folder, 'polizas')
    os.makedirs(polizas_folder, exist_ok=True)
    
    filename = secure_filename(file.filename)
    save_path = os.path.join(polizas_folder, filename)
    file.save(save_path)
    # NUEVO: log para confirmar escritura del archivo
    try:
        exists = os.path.exists(save_path)
        print(f"[upload] saved to {save_path} exists={exists}")
    except Exception as e:
        print(f"[upload] error verifying save path: {e}")

    issuer = (request.form.get('issuer') or '').strip() or None
    # Modo debug: si llega desde el cliente
    debug_enabled = (request.form.get('debug') == '1') or (request.args.get('debug') == '1')
    debug_logs = []
    def LOG(msg):
        print(msg)
        if debug_enabled:
            debug_logs.append(str(msg))

    LOG(f'[upload] issuer={issuer} file={filename}')

    items = []
    if filename.lower().endswith('.pdf'):
        try:
            items = parse_pdf_items_provider(save_path, issuer)
            LOG(f'[upload] provider items count={len(items)}')
        except Exception as e:
            LOG(f'[upload] provider parse error: {e}')
            items = []

    # Normalización: mapear variantes de claves a las usadas por la UI
    def _add_days_ddmmyyyy(date_str: str | None, days: int) -> str | None:
        try:
            if not date_str:
                return None
            dt = datetime.strptime(date_str.strip(), "%d/%m/%Y")
            return (dt + timedelta(days=days)).strftime("%d/%m/%Y")
        except Exception:
            return None

    def _normalize_to_ui(it: dict) -> dict:
        res = {
            "numero_poliza": it.get("numero_poliza") or it.get("poliza") or it.get("folio_id") or it.get("contrato_nro"),
            "recibo": it.get("recibo") or it.get("numero_proforma") or it.get("nro_tramite"),
            "colectivo_asegurado": it.get("colectivo_asegurado") or it.get("asegurado") or it.get("contratante"),
            "inicio_vigencia": it.get("inicio_vigencia") or it.get("vigencia_desde"),
            "vencimiento": it.get("vencimiento") or it.get("vigencia_hasta") or it.get("hasta"),
            "moneda": it.get("moneda"),
            "fecha_emision": it.get("fecha_emision") or it.get("emision"),
            "forma_pago": it.get("forma_pago"),
            "ultimo_dia_pago": it.get("ultimo_dia_pago"),
            "prima_comercial": it.get("prima_comercial"),
            "prima_neta": it.get("prima_neta"),
            "prima_total": it.get("prima_total") or it.get("monto"),
            "prima_comercial_igv": it.get("prima_comercial_igv") or it.get("prima_total") or it.get("monto"),
            "ramo": it.get("ramo") or it.get("doc_tipo"),
            "fecha_vencimiento": it.get("fecha_vencimiento") or it.get("vencimiento") or it.get("vigencia_hasta") or it.get("hasta") or it.get("expiracion"),
            "fecha_vecimiento": it.get("fecha_vecimiento"),
            "numero_documento_extracted": it.get("numero_documento_extracted"),
            # Campos extra para validación de cliente
            "contratante": it.get("contratante"),
            "razon_social": it.get("razon_social"),
        }
        # Si hay Prima Comercial, derive Prima Neta; o viceversa
        try:
            if res["prima_comercial"]:
                val = float(str(res["prima_comercial"]).replace(',', '.').replace(' ', ''))
                res["prima_neta"] = f"{(val / 1.03):.2f}"
            elif res["prima_neta"]:
                val = float(str(res["prima_neta"]).replace(',', '.').replace(' ', ''))
                res["prima_comercial"] = f"{(val * 1.03):.2f}"
        except Exception:
            pass

        # Regla de negocio de fechas (UI):
        # - último día de pago = fecha_emision (+fallback inicio_vigencia) + 15
        # - fecha_vencimiento (UI) = último día de pago
        cand = res.get("fecha_emision") or res.get("inicio_vigencia")
        calc = _add_days_ddmmyyyy(cand, 15)
    
        # 1) Completar último día de pago si falta
        if not res.get("ultimo_dia_pago") and calc:
            res["ultimo_dia_pago"] = calc
    
        # 2) Completar fecha_vencimiento si falta, prefiriendo último día de pago
        if not res.get("fecha_vencimiento"):
            res["fecha_vencimiento"] = res.get("ultimo_dia_pago") or calc
    
        # 3) Completar fecha_vecimiento (campo legacy) si falta, igual a fecha de pago
        if not res.get("fecha_vecimiento"):
            res["fecha_vecimiento"] = res.get("ultimo_dia_pago") or calc
    
        return res

    if items and len(items) > 0:
        LOG('[upload] Origen de datos: provider parser (items).')
        items_ui = [_normalize_to_ui(it) for it in items]
        LOG(f"[upload] fechas normalizadas: {[(x.get('ultimo_dia_pago'), x.get('fecha_vencimiento'), x.get('vencimiento')) for x in items_ui]}")
        # Dedupe por combinación clave y descartar muy vacíos
        unique = []
        seen = set()
        for it in items_ui:
            key = f"{it.get('numero_poliza') or ''}|{it.get('recibo') or ''}|{it.get('ramo') or ''}"
            is_meaningful = any(it.get(k) for k in ['numero_poliza', 'recibo', 'colectivo_asegurado', 'moneda', 'prima_comercial_igv'])
            if not is_meaningful:
                LOG(f"[upload] descartado item vacío: {it}")
                continue
            if key in seen:
                LOG(f"[upload] item duplicado (clave={key}) descartado")
                continue
            seen.add(key)
            unique.append(it)

        return {'filename': filename, 'items': unique, 'debug': debug_logs}, 200

    # Fallback: comportamiento anterior (un solo objeto)
    extracted = {}
    if filename.lower().endswith('.pdf'):
        try:
            extracted = parse_pdf_fields_fitz(save_path)
            LOG(f'[upload] fitz fields keys={list(extracted.keys())}')
            extra2 = parse_pdf_fields(save_path)
            LOG(f'[upload] fallback fields keys={list(extra2.keys())}')
            for k, v in extra2.items():
                cur = extracted.get(k)
                if (cur is None or cur == '') and (v is not None and v != ''):
                    extracted[k] = v
            # fallback del folio en servidor
            if not extracted.get('folio_id'):
                cand = extracted.get('poliza') or extracted.get('contrato_nro')
                if cand:
                    extracted['folio_id'] = cand
                    extracted['folio_label'] = 'Contrato Nro' if extracted.get('contrato_nro') else 'Póliza N°'
        except Exception as e:
            LOG(f'[upload] parse error (fitz/pypdf2): {e}')
            extracted = parse_pdf_fields(save_path)
            # fallback del folio también en parse alterno
            if not extracted.get('folio_id'):
                cand = extracted.get('poliza') or extracted.get('contrato_nro')
                if cand:
                    extracted['folio_id'] = cand
                    extracted['folio_label'] = 'Contrato Nro' if extracted.get('contrato_nro') else 'Póliza N°'
    # Derivar Prima Neta desde Prima Comercial en el fallback (fields)
    try:
        pc = extracted.get('prima_comercial') or extracted.get('prima_total') or extracted.get('monto')
        if pc:
            val = float(str(pc).replace(',', '.').replace(' ', ''))
            extracted['prima_neta'] = f"{(val / 1.03):.2f}"
    except Exception:
        pass

    # NUEVO: si solo vino prima_neta, derive prima_comercial
    try:
        pn = extracted.get('prima_neta')
        if pn and not extracted.get('prima_comercial'):
            val = float(str(pn).replace(',', '.').replace(' ', ''))
            extracted['prima_comercial'] = f"{(val * 1.03):.2f}"
    except Exception:
        pass

    # NUEVO: derivar ultimo_dia_pago = fecha_emision + 15 si falta
    try:
        if not extracted.get('ultimo_dia_pago'):
            # NUEVO: derivación SIEMPRE desde fecha_emision (+15)
            try:
                cand = extracted.get('fecha_emision') or extracted.get('inicio_vigencia')
                calc = _add_days_ddmmyyyy(cand, 15)
                if calc:
                    extracted['ultimo_dia_pago'] = calc
                    extracted['fecha_vencimiento'] = calc
                    extracted['fecha_vecimiento'] = calc
            except Exception:
                pass
            
            # Ajuste de fechas (regla negocio):
            # - fecha_vencimiento = fecha de pago (emisión + 15)
            # - fecha_vecimiento = idem
            try:
                cand = extracted.get('fecha_emision') or extracted.get('inicio_vigencia')
                calc = _add_days_ddmmyyyy(cand, 15)
                if calc:
                    extracted['fecha_vencimiento'] = calc
                    extracted['fecha_vecimiento'] = calc
            except Exception:
                pass
    except Exception:
        pass

    # Ajuste de fechas:
    # - fecha_vencimiento = vigencia (si existe)
    # - fecha_vecimiento = fecha de pago (ultimo_dia_pago o emision+15)
    try:
        if not extracted.get('fecha_vencimiento'):
            fv = (extracted.get('vencimiento')
                  or extracted.get('vigencia_hasta')
                  or extracted.get('hasta')
                  or extracted.get('expiracion'))
            if fv:
                extracted['fecha_vencimiento'] = fv

        # Sincroniza fecha_vecimiento a la fecha de pago
        extracted['fecha_vecimiento'] = extracted.get('ultimo_dia_pago') or _add_days_ddmmyyyy(extracted.get('fecha_emision'), 15)
    except Exception:
        pass

    return {'filename': filename, 'fields': extracted, 'debug': debug_logs}, 200


@bp.route('/clientes/add', methods=['POST'])
def clientes_add():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    # Manejar upload de archivo si existe
    data = {}
    if request.files or request.form:
         # Si es multipart/form-data, los campos están en form
         data = request.form.to_dict()
    else:
         # Si es JSON puro
         data = request.get_json(silent=True) or {}

    pdf_file = request.files.get('pdf_file')
    if pdf_file and pdf_file.filename:
         from werkzeug.utils import secure_filename
         import os
         import time
         
         filename = secure_filename(pdf_file.filename)
         # Usar timestamp para evitar colisiones
         ts = int(time.time())
         filename = f"{ts}_{filename}"
         
         upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'clientes')
         os.makedirs(upload_folder, exist_ok=True)
         
         save_path = os.path.join(upload_folder, filename)
         pdf_file.save(save_path)
         
         data['pdf_path'] = f"static/uploads/clientes/{filename}"

    from controllers.clientes.addcliente import save_cliente
    res = save_cliente(data)
    status = 200 if res.get('ok') else 400
    return res, status


@bp.route('/api/subagentes', methods=['GET'])
def api_get_subagentes():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    from controllers.subagente import get_subagentes_abreviaciones
    subagentes = get_subagentes_abreviaciones()
    return {'ok': True, 'subagentes': subagentes}, 200


@bp.route('/api/clientes/buscar', methods=['GET'])
def api_buscar_clientes():
    """Busca clientes por nombre, RUC o DNI"""
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    from controllers.clientes.estado_cuenta import buscar_clientes
    search_term = request.args.get('q', '').strip()

    if not search_term or len(search_term) < 2:
        return jsonify({'ok': False, 'message': 'Mínimo 2 caracteres'}), 400

    clientes = buscar_clientes(search_term)
    return jsonify({'ok': True, 'clientes': clientes}), 200


@bp.route('/clientes/extract-pdf', methods=['POST'])
def clientes_extract_pdf():
    """Endpoint para extraer información de cliente desde un PDF."""
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    if 'pdf_file' not in request.files:
        return {'ok': False, 'errors': ['No se envió ningún archivo PDF']}, 400

    file = request.files['pdf_file']

    if file.filename == '':
        return {'ok': False, 'errors': ['Nombre de archivo vacío']}, 400

    if not file.filename.lower().endswith('.pdf'):
        return {'ok': False, 'errors': ['El archivo debe ser un PDF']}, 400

    try:
        # Guardar archivo temporalmente
        filename = secure_filename(file.filename)
        temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp_' + filename)
        file.save(temp_path)

        # Procesar PDF
        from controllers.clientes.pdf_extractor import process_pdf_file
        result = process_pdf_file(temp_path)

        # Eliminar archivo temporal
        try:
            os.remove(temp_path)
        except:
            pass

        if result.get('ok'):
            return {'ok': True, 'data': result.get('data', {}), 'debug': result.get('raw_text', '')}, 200
        else:
            return {'ok': False, 'errors': [result.get('error', 'Error procesando PDF')]}, 400

    except Exception as e:
        current_app.logger.error(f'Error en extract-pdf: {e}')
        return {'ok': False, 'errors': [str(e)]}, 500


@bp.route('/clientes/select', methods=['POST'])
def clientes_select():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    payload = request.get_json(silent=True) or request.form.to_dict()
    selected = {
        'nombre': payload.get('nombre') or payload.get('razon_social'),
        'razon_social': payload.get('razon_social'),
        'tipo_doc': payload.get('tipo_doc') or payload.get('doc') or payload.get('tipo_documento'),
        'n_doc': payload.get('n_doc') or payload.get('numero_documento'),
        'tel': payload.get('tel') or payload.get('telefono'),
        'subagente': payload.get('subagente') or payload.get('subAgente'),
        'motivo': payload.get('motivo'),
        'ramos_producto': payload.get('ramos_producto'),
        'idCliente': payload.get('idCliente')
    }
    session['selected_cliente'] = selected
    return {'ok': True}, 200

@bp.route('/polizas/save', methods=['POST'])
def polizas_save():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    payload = request.get_json(silent=True) or {}
    items = payload.get('items') or []
    selected = payload.get('selected') or session.get('selected_cliente') or {}

    # Sincroniza la sesión con el subagente seleccionado (y demás campos)
    prev = session.get('selected_cliente') or {}
    if selected:
        session['selected_cliente'] = {**prev, **selected}

    from controllers.addPoliza import save_polizas
    res = save_polizas(items, selected)
    if not res.get('ok'):
        current_app.logger.error('polizas_save error: %s', res.get('errors'))
    status = 200 if res.get('ok') else 400
    return res, status


@bp.route('/polizas/update', methods=['POST'])
def polizas_update():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    data = request.get_json(silent=True) or request.form.to_dict()
    from controllers.editar_poliza import update_poliza
    res = update_poliza(data)
    status = 200 if res.get('ok') else 400
    return res, status

# NUEVO: Endpoint para actualizar Primas (que en realidad son pólizas)
@bp.route('/primas/update', methods=['POST'])
def primas_update():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    data = request.get_json(silent=True) or request.form.to_dict()
    # Mapeo de campos de Primas a Pólizas
    # La UI envía idPrima, pero el controlador espera idPoliza
    if 'idPrima' in data:
        data['idPoliza'] = data.pop('idPrima')
    
    # Reutilizamos el controlador de pólizas ya que comparten tabla
    from controllers.editar_poliza import update_poliza
    res = update_poliza(data)
    status = 200 if res.get('ok') else 400
    return res, status

@bp.route('/api/polizas/renovar', methods=['POST'])
def polizas_renovar():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401
    
    data = request.get_json(silent=True) or {}
    
    # Construir payload para update_poliza
    # Se mantienen los datos financieros existentes (no se resetean a 0)
    update_payload = {
        'idPoliza': data.get('idPoliza'),
        'cia': data.get('compania'),
        'ramos_producto': data.get('producto'),
        'poliza': data.get('poliza'),
        'vig_hasta': data.get('vig_fin'),
        'ramo': data.get('ramo'),
        'motivo': data.get('tipo_vigencia'), # mapeado a 'motivo'
        'vig_desde': data.get('vig_inicio'),
        'fecha_emision': data.get('fecha_emision'),
        
        # Al no enviar claves de primas, el controlador usará los valores actuales de la BD
    }

    from controllers.editar_poliza import update_poliza
    res = update_poliza(update_payload)
    status = 200 if res.get('ok') else 400
    return res, status


# Util: permitir archivos
def allowed_file(filename: str) -> bool:
    ext = (filename or '').rsplit('.', 1)[-1].lower()
    return ext in {'pdf', 'jpg', 'jpeg', 'png'}

# -------- Extracción de texto (PyMuPDF y fallback) --------
def _extract_text_fitz(path: str) -> str:
    try:
        import fitz  # PyMuPDF
        text_chunks = []
        with fitz.open(path) as doc:
            for page in doc:
                text_chunks.append(page.get_text())
        return "\n".join(text_chunks)
    except Exception:
        return _extract_text_pypdf2(path)

def _extract_text_pypdf2(path: str) -> str:
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(path)
        return "\n".join([page.extract_text() or "" for page in reader.pages])
    except Exception:
        return ""

# -------- Parser por proveedor --------
import re
from typing import List, Dict, Optional

def _clean(s: Optional[str]) -> str:
    return (s or "").strip()

def _find(pattern: str, text: str, flags=re.IGNORECASE) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None

def _number(s: Optional[str]) -> Optional[str]:
    if not s: return None
    m = re.search(r"([0-9][0-9\.\-\/ ]+)", s)
    return m.group(1).strip() if m else s

def _money(s: Optional[str]) -> Optional[str]:
    if not s: return None
    m = re.search(r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+)", s)
    return m.group(1) if m else s

def _parse_mapfre(text: str) -> Dict[str, str]:
    item = {}
    item['numero_poliza'] = _find(r"POLIZA\s*:?\s*([0-9A-Z\-]+)", text) or _find(r"Poliza\s*:\s*([0-9A-Z\-]+)", text)

    # Recibo desde CONCEPTO y fallback
    recibo_concept = _find(r"(?:Ct\s*)?Cancelaci[oó]n\s+Recibo\s*([0-9]+)", text)
    # Fallback anterior: factura o recibo estándar
    recibo_top = _find(r"FACTURA\s+ELECTRONICA\s*\n([A-Z0-9\- ]+)", text) or _find(r"Recibo\s*:?[\s\n]*([0-9A-Z\- ]+)", text)
    item['recibo'] = recibo_concept or recibo_top

    item['colectivo_asegurado'] = _find(r"CONTRATANTE\s*:\s*(.+)", text) or _find(r"Asegurado\s*:\s*(.+)", text)

    # Vigencias: captura en bloque (entre DESDE … HASTA …) y fallback
    m_vig = re.search(r"DESDE\s*([0-9]{2}/[0-9]{2}/[0-9]{4}).*?HASTA\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text, re.IGNORECASE | re.DOTALL)
    if m_vig:
        item['inicio_vigencia'] = m_vig.group(1)
        item['vencimiento'] = m_vig.group(2)
    else:
        item['inicio_vigencia'] = _find(r"DESDE\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        item['vencimiento'] = _find(r"HASTA\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)

    item['moneda'] = _find(r"MONEDA\s*:\s*([A-Za-z]+)", text) or _find(r"Moneda\s*:\s*([A-Za-z]+)", text)
    item['fecha_emision'] = _find(r"FECHA\s+EMISION\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text) or _find(r"Emision\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    item['forma_pago'] = _find(r"Forma de Pago\s*:\s*(.+)", text)
    item['ultimo_dia_pago'] = _find(r"Ultimo d[ií]a de Pago\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)

    # Ramo desde la línea de CONCEPTO
    ramo_concept = _find(r"(?:Ct\s*)?Cancelaci[oó]n\s+Recibo\s*[0-9]+\.?\s*(.+?)(?:\n|$)", text)
    item['ramo'] = ramo_concept

    # Conceptos
    prima = _find(r"Prima Comercial\s*[:]*\s*S?\/?\s*([0-9\.,]+)", text)
    igv = _find(r"(?:Impuesto Gral\.? A Las Ventas|IGV)\s*[:]*\s*S?\/?\s*([0-9\.,]+)", text)
    total = _find(r"(?:Importe Total|Total)\s*[:]*\s*S?\/?\s*([0-9\.,]+)", text)
    item['prima_comercial'] = prima or _money(_find(r"Prima\s*Total\s*[:]*\s*([0-9\.,]+)", text))
    item['prima_comercial_igv'] = total or (f"{float(prima.replace(',', '.')) + float(igv.replace(',', '.')):.2f}" if prima and igv else None)

    return {k: _clean(v) for k, v in item.items() if v}

def _parse_positiva(text: str) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []

    # Partir el PDF en bloques por títulos conocidos
    markers = [r"PROFORMA DE PAGO", r"Proforma de Cobertura \(Cobro\)", r"PROFORMA DE COBERTURA \(Cobro\)"]
    positions = []
    for pat in markers:
        for m in re.finditer(pat, text, re.IGNORECASE):
            positions.append(m.start())
    positions = sorted(set(positions))
    blocks = []
    if positions:
        for i, start in enumerate(positions):
            end = positions[i + 1] if i + 1 < len(positions) else len(text)
            blocks.append(text[start:end])
    else:
        blocks = [text]

    def _sum(a: str | None, b: str | None) -> str | None:
        try:
            return f"{float((a or '0').replace(',', '.')) + float((b or '0').replace(',', '.')):.2f}"
        except Exception:
            return None

    for blk in blocks:
        numero_proforma = _find(r"N[uú]mero de Proforma\s*:\s*([0-9A-Z\-]+)", blk)
        poliza_nro = _find(r"P[oó]liza\s*Nro\s*:\s*([0-9A-Z\-]+)", blk) or _find(r"P[oó]liza\s*N°\s*:\s*([0-9A-Z\-]+)", blk) or _find(r"Poliza\s*:\s*([0-9A-Z\-]+)", blk)
        contrato_nro = _find(r"Contrato\s+Nro\s*:\s*([0-9A-Z\-]+)", blk)
        vig_desde = _find(r"Vigencia Desde\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", blk)
        vig_hasta = _find(r"Hasta\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", blk) or _find(r"Vencimiento\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", blk)
        moneda = _find(r"Moneda\s*:\s*([A-Za-z]+)", blk)
        emision = _find(r"Emisi[oó]n\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", blk)
        ramo = _find(r"Ramo\s*:\s*(.+)", blk)
        contratante = _find(r"Contratante\s*:\s*(.+)", blk)
        asegurado = _find(r"Asegurado\s*:\s*(.+)", blk)
        forma_pago = _find(r"Forma de Pago\s*:\s*(.+)", blk)
        ultimo_dia = _find(r"[ÚU]ltimo d[ií]a de Pago\s*:?[\s]*([0-9]{2}/[0-9]{2}/[0-9]{4})", blk)

        prima_total = _money(_find(r"Prima Total\s*S?\/?\s*([0-9\.,]+)", blk))
        igv_val = _money(_find(r"Impuesto General a las Ventas\s*S?\/?\s*([0-9\.,]+)", blk))
        sobrevivencia = _money(_find(r"Sobrevivencia.*?S?\/?\s*([0-9\.,]+)", blk, flags=re.IGNORECASE | re.DOTALL))
        costos_emision = _money(_find(r"Costos?\s+de\s+Emisi[oó]n.*?S?\/?\s*([0-9\.,]+)", blk, flags=re.IGNORECASE | re.DOTALL))
        igv_val = igv_val or _money(_find(r"IGV.*?S?\/?\s*([0-9\.,]+)", blk, flags=re.IGNORECASE | re.DOTALL))
        total_plus_igv_line = _money(_find(r"Prima\s+Comercial\s*\+\s*IGV.*?S?\/?\s*([0-9\.,]+)", blk, flags=re.IGNORECASE | re.DOTALL))

        prima_comercial = _money(_find(r"Prima Comercial\s*S?\/?\s*([0-9\.,]+)", blk)) or prima_total
        if not prima_comercial and (sobrevivencia or costos_emision):
            prima_comercial = _sum(sobrevivencia, costos_emision)

        total_con_igv = None
        if total_plus_igv_line:
            total_con_igv = total_plus_igv_line
        elif prima_comercial and igv_val:
            total_con_igv = _sum(prima_comercial, igv_val)
        elif prima_total and igv_val:
            total_con_igv = _sum(prima_total, igv_val)

        item = {
            'numero_poliza': poliza_nro or contrato_nro,
            'contrato_nro': contrato_nro,
            'recibo': numero_proforma,
            'colectivo_asegurado': asegurado or contratante,
            'inicio_vigencia': vig_desde,
            'vencimiento': vig_hasta,
            'moneda': moneda,
            'fecha_emision': emision,
            'forma_pago': forma_pago,
            'ultimo_dia_pago': ultimo_dia,
            'prima_comercial': prima_comercial or prima_total,
            'prima_comercial_igv': total_con_igv or prima_total,
            'ramo': ramo
        }
        items.append({k: _clean(v) for k, v in item.items() if v})

    return items

def parse_pdf_items_provider(path: str, issuer: str | None = None):
    text = _extract_text_fitz(path)
    t = text.lower()
    prov = (issuer or "").strip().lower() or None
    low = (text or "").lower()

    if not prov:
        # detección básica por contenido
        # Primero: Vida Ley de Mapfre por patrones de contenido
        if re.search(r"\bmapfre\b", t) and (
            re.search(r"\bvida\s+ley\b", t) or
            re.search(r"decreto\s+legislativo\s*n?\s*688", t) or
            "d.l.688" in t
        ):
            prov = "mapfre-vida-ley"
        elif "la positiva" in t:
            prov = "positiva"
        elif "mapfre-vida-ley" in t:
            prov = "mapfre-vida-ley"
        elif "mapfre" in t:
            prov = "mapfre"
        elif "lpv-vida-ley" in t:
            prov = "lpv-vida-ley"
        elif "lpv-pension" in t:
            prov = "lpv-pension"
        elif "lpv-salud" in t:
            prov = "lpv-salud"
        # QUITADO: no detectar 'lpv-vida-ley', 'lpv-pension', 'lpv-salud' por contenido del PDF
        # Estos slugs deben venir desde el 'issuer' del cliente (UI).
        # NUEVO: preferir Crecer si aparece, aunque también figure 'sanitasperu'
        elif "crecer seguros" in t or re.search(r"\bcrecer\b", t):
            prov = "crecer"
        # NUEVO: detectar Protecta ANTES que Sanitas (por pasarela de pago Sanitas en PDFs de Protecta)
        elif "protecta" in t or "protecta security" in t:
            prov = "protecta"
        elif "sanitas" in t:
            prov = "sanitas"
        elif "pacifico" in t or "pacífico" in t:
            prov = "pacifico"
        elif "vida-ley-crecer" in t:
            prov = "vida-ley-crecer"
        else:
            prov = ""


    # Backstop: corregir proveedor a Pacífico si el contenido lo indica claramente
    # Evita ruta equivocada cuando el UI envió 'proctecta/protecta/positiva'.
    if prov in ('proctecta', 'protecta', 'positiva', None):
        # QUITADO patrón PF-SCTR: también aparece en Sanitas
        if ('pacifico' in low or 'pacífico' in low):
            prov = 'pacifico'

    # NUEVO: si vino 'pacifico' o 'positiva' desde UI pero el contenido dice 'sanitas', fuerza Sanitas
    if prov in ('pacifico', 'positiva', 'protecta') and 'sanitas' in low:
        prov = 'sanitas'

    # Enrutamiento por proveedor (prioriza 'prov' si está presente)
    items: List[Dict[str, str]] = []
    if prov == 'pacifico':
        # Heurística por contenido para distinguir producto
        is_vida_ley = re.search(r'\bvida\s+ley\b', low) or re.search(r'\bcondicionado', low)
        is_sctr_pension = re.search(r'\bsctr\b', low) or re.search(r'\baccidentes\s+de\s+trabajo\b', low)
        is_sctr_salud = re.search(r'\bsctr\b', low) or re.search(r'\bsalud\b', low)
        
        try:
            if is_vida_ley:
                from controllers.addPacificoVidaLey import parse_pacifico_vidaley
                it = parse_pacifico_vidaley(text)
                if it: items.append(it)
            elif is_sctr_pension:
                # SCTR (Pensión/Salud) o genérico: usar el parser correcto
                from controllers.addPacifico import parse_pacifico_pension
                it = parse_pacifico_pension(text)
                if it: items.append(it)
            # Antes era "elif"; cambiamos a "if" para detectar ambos en un mismo PDF
            if is_sctr_salud:
                from controllers.addPacificoSalud import parse_pacifico_salud
                it = parse_pacifico_salud(text)
                if it: items.append(it)
        except Exception as e:
            print(f"[provider] pacifico parse error: {e}")

        return items

    print(f"[provider] detectado: {prov}")

    if prov == "mapfre":
        from controllers.addMapfre import parse_mapfre
        item = parse_mapfre(text)
        print("[provider] mapfre item:", item)
        return [item] if item else []
    if prov == "mapfre-vida-ley":
        from controllers.addMapfreVidaLey import parse_mapfre_vidaley
        item = parse_mapfre_vidaley(text)
        print("[provider] mapfre-vida-ley item:", item)
        return [item] if item else []

    # La Positiva (EPS/Vida/Seguros)
    if prov in {"positiva", ""}:
        # Detectar Vida Ley por contenido dentro de La Positiva
        hint_vidaley = (
            re.search(r"\bvida\s+ley\b", text, re.IGNORECASE) or
            re.search(r"decreto\s+legislativo\s*n?\s*688", text, re.IGNORECASE) or
            ("d.l.688" in t)
        )
        if hint_vidaley:
            from controllers.addLPVLEY import parse_positiva_vidaley
            item = parse_positiva_vidaley(text)
            print("[provider] positiva-vida-ley item:", item)
            return [item] if item else []
        # Separar SCTR Salud vs Pensión por contenido
        hint_sctr = re.search(r"\bsctr\b", text, re.IGNORECASE)
        has_salud = re.search(r"\beps\b", text, re.IGNORECASE) or re.search(r"\bsalud\b", text, re.IGNORECASE)
        has_pension = re.search(r"\bpensi[o\u00f3]n\b", text, re.IGNORECASE)

        if hint_sctr or has_salud or has_pension:
            # NUEVO: si hay ambos, parsear y devolver dos ítems
            if has_salud and has_pension:
                from controllers.addLPVSALUD import parse_positiva_Salud
                from controllers.addLPVPENSION import parse_positiva_Pension
                item_salud = parse_positiva_Salud(text)
                item_pension = parse_positiva_Pension(text)
                print("[provider] positiva-sctr ambos -> salud:", item_salud, "pension:", item_pension)
                items = []
                if item_salud: items.append(item_salud)
                if item_pension: items.append(item_pension)
                return items
            if has_salud:
                from controllers.addLPVSALUD import parse_positiva_Salud
                item = parse_positiva_Salud(text)
                print("[provider] positiva-sctr-salud item:", item)
                return [item] if item else []
            elif has_pension:
                from controllers.addLPVPENSION import parse_positiva_Pension
                item = parse_positiva_Pension(text)
                print("[provider] positiva-sctr-pension item:", item)
                return [item] if item else []
            else:
                # Ambiguo: por ahora cae en Pensión (comportamiento previo)
                from controllers.addLPVPENSION import parse_positiva_Pension
                item = parse_positiva_Pension(text)
                print("[provider] positiva-sctr item:", item)
                return [item] if item else []
        return _parse_positiva(text)
    # Sanitas (EPS Salud / SCTR)
    if prov == "sanitas":
        from controllers.addSanitasSalud import parse_sanitas_salud
        item = parse_sanitas_salud(text)
        return [item] if item else []
    # NUEVO: Protecta Pensión
    if prov in {"protecta", "proctecta"}:
        from controllers.addProctectaPension import parse_protecta_pension
        item = parse_protecta_pension(text)
        return [item] if item else []
    # NUEVO: Crecer Pensión
    if prov == "crecer":
        from controllers.addCrecerPension import parse_crecer_pension
        item = parse_crecer_pension(text)
        print("[provider] crecer pension item:", item)
        return [item] if item else []
    if prov == "pacifico":
        from controllers.addPacifico import parse_pacifico_pension
        from controllers.addPacificoVidaLey import parse_pacifico_vidaley  # NUEVO
        print("[provider] branch: pacifico; texto (head 600):", text[:600].replace("\n", "\\n"))
        # Detectar Vida Ley por contenido
        hint_vidaley = re.search(r"\bvida\s+ley\b", text, re.IGNORECASE) or re.search(r"decreto\s+legislativo\s*n?\s*688", text, re.IGNORECASE)
        item = parse_pacifico_vidaley(text) if hint_vidaley else parse_pacifico_pension(text)
        print("[provider] pacifico item:", item)
        return [item] if item else []
    # NUEVO: Pacifico Salud
    if prov == "pacifico_salud":
        from controllers.addPacificoSalud import parse_pacifico_salud
        item = parse_pacifico_salud(text)
        print("[provider] pacifico_salud item:", item)
        return [item] if item else []
    
    if prov == "vida-ley-crecer":
        from controllers.addCrecerVidaLey import parse_crecer_vidaley
        item = parse_crecer_vidaley(text)
        print("[provider] vida-ley-crecer item:", item)
        return [item] if item else []
    
    # NUEVO: LPV Vida Ley
    if prov == "lpv-vida-ley":
        from controllers.addLPVLEY import parse_positiva_vidaley
        item = parse_positiva_vidaley(text)
        print("[provider] lpv-vida-ley item:", item)
        return [item] if item else []
    # NUEVO: LPV Pension
    if prov == "lpv-pension":
        from controllers.addLPVPENSION import parse_positiva_Pension
        item = parse_positiva_Pension(text)
        print("[provider] lpv-pension item:", item)
        return [item] if item else []
    # NUEVO: LPV Salud
    if prov == "lpv-salud":
        from controllers.addLPVSALUD import parse_positiva_Salud
        item = parse_positiva_Salud(text)
        print("[provider] lpv-salud item:", item)
        return [item] if item else []
    return []

def parse_pdf_fields_fitz(path: str) -> Dict[str, str]:
    # Devuelve un único objeto (fallback)
    items = parse_pdf_items_provider(path)
    return items[0] if items else {}

def parse_pdf_fields(path: str) -> Dict[str, str]:
    # Fallback simple: intenta más patrones sobre todo el texto
    text = _extract_text_pypdf2(path)
    if not text:
        return {}
    items = parse_pdf_items_provider(path, None)
    return items[0] if items else {}

# -------- Opcional: usar PDF.co si configuras la API key --------
def parse_pdf_fields_pdfco(path: str) -> Dict[str, str]:
    import os, requests
    api_key = os.getenv("PDFCO_API_KEY")  # <- FIX: variable correcta
    if not api_key:
        return {}
    # Sube archivo en crudo con inline=true para obtener texto y luego aplicar patrones
    url = "https://api.pdf.co/v1/pdf/convert/to/text"
    files = {'file': open(path, 'rb')}
    payload = {'inline': True}
    headers = {'x-api-key': api_key}
    try:
        r = requests.post(url, data=payload, files=files, headers=headers, timeout=30)
        txt = r.text or ""
        # Reutiliza los parsers sobre el texto
        # Nota: aquí uso el parser La Positiva/Mapfre por patrones
        # (puedes expandir con reglas adicionales si aparecen más variantes)
        prov = "positiva" if "la positiva" in txt.lower() else ("mapfre" if "mapfre" in txt.lower() else "")
        if prov == "mapfre":
            return _parse_mapfre(txt)
        return (_parse_positiva(txt) or [{}])[0]
    except Exception:
        return {}


@bp.route('/dashboard/notes', methods=['GET', 'POST'])
def dashboard_notes():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    notes_path = os.path.join(current_app.root_path, 'plaintext', 'dashboard_notes.txt')
    os.makedirs(os.path.dirname(notes_path), exist_ok=True)

    if request.method == 'GET':
        try:
            with open(notes_path, 'r', encoding='utf-8') as f:
                return {'ok': True, 'notes': f.read()}, 200
        except Exception:
            return {'ok': True, 'notes': ''}, 200

    data = request.get_json(silent=True) or request.form.to_dict()
    content = data.get('notes') or ''
    try:
        with open(notes_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {'ok': True}, 200
    except Exception as e:
        return {'ok': False, 'errors': [str(e)]}, 500

# NUEVO: ruta para servir PDFs subidos desde UPLOAD_FOLDER
@bp.route('/uploads/<path:filename>', methods=['GET'])
def serve_upload(filename):
    folder = current_app.config.get('UPLOAD_FOLDER')
    
    # 1. Soporte para subcarpetas (ej: polizas/archivo.pdf)
    # Evitamos secure_filename en la ruta completa para no romper los slashes
    if '/' in filename or '\\' in filename:
        # Extraer subcarpeta y archivo
        parts = filename.replace('\\', '/').split('/')
        # Solo permitimos subcarpeta 'polizas' u 'clientes' por seguridad
        if parts[0] in ['polizas', 'clientes']:
             sub = parts[0]
             name = secure_filename(parts[-1])
             target_dir = os.path.join(folder, sub)
             if os.path.isfile(os.path.join(target_dir, name)):
                 return send_from_directory(target_dir, name, as_attachment=False)

    # 2. Comportamiento estándar (archivo en raíz de uploads)
    safe = secure_filename(filename)
    full = os.path.join(folder, safe)
    
    if os.path.isfile(full):
        return send_from_directory(folder, safe, as_attachment=False)
        
    # 3. Fallback: Buscar en 'polizas' si no se especificó ruta (para previews recién subidos)
    full_poliza = os.path.join(folder, 'polizas', safe)
    if os.path.isfile(full_poliza):
        return send_from_directory(os.path.join(folder, 'polizas'), safe, as_attachment=False)

    return {'error': 'Archivo no encontrado', 'path': full}, 404


# dentro de routes/route.py (añadir el nuevo endpoint API)
@bp.route('/api/aseguradoras', methods=['GET'])
def api_aseguradoras():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401
    from controllers.compania import get_aseguradoras
    rows = get_aseguradoras() or []
    return {'ok': True, 'rows': rows}, 200

#Metodos para editar y ver detalle de clienes.
@bp.route('/clientes/edit', methods=['POST'])
def clientes_edit():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    from controllers.clientes.editcliente import editar_cliente_route
    return editar_cliente_route()


@bp.route('/clientes/detalle/<int:idCliente>', methods=['GET'])
def clientes_detalle(idCliente):
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    from controllers.clientes.editcliente import get_cliente_detalle_route
    return get_cliente_detalle_route(idCliente)

@bp.route('/clientes/delete', methods=['POST'])
def clientes_delete():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    from controllers.clientes.deletecliente import eliminar_cliente_route
    return eliminar_cliente_route()

@bp.route('/clientes/restore', methods=['POST'])
def clientes_restore():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    from controllers.clientes.restorecliente import restaurar_cliente_route
    return restaurar_cliente_route()
