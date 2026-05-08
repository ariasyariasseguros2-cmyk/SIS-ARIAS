from flask import Blueprint, request, session, jsonify, current_app, send_file
import os


bp = Blueprint("reporte_diario", __name__)


@bp.route("/api/reporte-diario", methods=["POST"])
def api_reporte_diario():
    if "user" not in session:
        return {"ok": False, "error": "No autenticado"}, 401

    from controllers.reporte_diario import get_reporte_diario_data

    filters = request.get_json(silent=True) or {}
    rows = get_reporte_diario_data(filters)
    return jsonify({"ok": True, "rows": rows})


@bp.route("/api/reporte-diario/export/excel", methods=["GET"])
def api_reporte_diario_excel():
    if "user" not in session:
        return {"ok": False, "error": "No autenticado"}, 401
    try:
        from controllers.reporte_diario import export_excel

        upload_folder = current_app.config.get("UPLOAD_FOLDER", os.path.join(current_app.root_path, "uploads"))
        filepath, filename = export_excel(upload_folder)
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        current_app.logger.error(f"Error exportando reporte diario Excel: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/api/reporte-diario/export/pdf", methods=["GET"])
def api_reporte_diario_pdf():
    if "user" not in session:
        return {"ok": False, "error": "No autenticado"}, 401
    try:
        from controllers.reporte_diario import export_pdf

        upload_folder = current_app.config.get("UPLOAD_FOLDER", os.path.join(current_app.root_path, "uploads"))
        filepath, filename = export_pdf(upload_folder)
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        current_app.logger.error(f"Error exportando reporte diario PDF: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/api/reporte-gestion-diaria", methods=["POST"])
def api_reporte_gestion_diaria():
    if "user" not in session:
        return {"ok": False, "error": "No autenticado"}, 401

    from controllers.reporte_diario import get_reporte_diario_data

    filters = request.get_json(silent=True) or {}
    rows = get_reporte_diario_data(filters)
    return jsonify({"ok": True, "rows": rows})


@bp.route("/api/reporte-gestion-diaria/export/excel", methods=["GET"])
def api_reporte_gestion_diaria_excel():
    if "user" not in session:
        return {"ok": False, "error": "No autenticado"}, 401
    try:
        from controllers.reporte_diario import export_excel

        upload_folder = current_app.config.get("UPLOAD_FOLDER", os.path.join(current_app.root_path, "uploads"))
        filters = {
            "usuario": request.args.get("usuario") or "",
            "f_reg_desde": request.args.get("f_reg_desde") or "",
            "f_reg_hasta": request.args.get("f_reg_hasta") or "",
        }
        filepath, filename = export_excel(upload_folder, filters=filters)
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        current_app.logger.error(f"Error exportando reporte gestion diaria Excel: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/api/reporte-gestion-diaria/export/pdf", methods=["GET"])
def api_reporte_gestion_diaria_pdf():
    if "user" not in session:
        return {"ok": False, "error": "No autenticado"}, 401
    try:
        from controllers.reporte_diario import export_pdf

        upload_folder = current_app.config.get("UPLOAD_FOLDER", os.path.join(current_app.root_path, "uploads"))
        filters = {
            "usuario": request.args.get("usuario") or "",
            "f_reg_desde": request.args.get("f_reg_desde") or "",
            "f_reg_hasta": request.args.get("f_reg_hasta") or "",
        }
        filepath, filename = export_pdf(upload_folder, filters=filters)
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        current_app.logger.error(f"Error exportando reporte gestion diaria PDF: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

