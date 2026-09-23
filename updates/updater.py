import json
import os
import sys
import shutil
import hashlib
import zipfile
import subprocess
import ssl
import urllib.request
import urllib.error
import urllib.parse
import webbrowser

from typing import Optional, Dict, Any, Tuple, Callable


# ============================================================
# CONFIGURACIÓN
# ============================================================

APP_VERSION: str = "1.0.0"

VERSION_URL: str = (
    "https://aasnet.tech/updates/version.json"
)

# IMPORTANTE:
# Tu PyInstaller genera main.exe
APP_EXE_NAME: str = "main.exe"

# Permitir segundo intento HTTPS sin validar certificado.
# No es lo ideal desde seguridad, pero lo mantenemos
# por compatibilidad con tu configuración actual.
ALLOW_INSECURE_SSL_FALLBACK: bool = True


# ============================================================
# SSL
# ============================================================

def _crear_contexto_ssl(
    inseguro: bool = False
) -> Optional[ssl.SSLContext]:

    if inseguro:
        ctx = ssl.create_default_context()

        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        return ctx

    return None


# ============================================================
# CAMBIAR HTTP / HTTPS
# ============================================================

def _alternar_http(url: str) -> str:

    try:
        p = urllib.parse.urlparse(url)

        if p.scheme == "https":
            return p._replace(
                scheme="http"
            ).geturl()

        if p.scheme == "http":
            return p._replace(
                scheme="https"
            ).geturl()

    except Exception:
        pass

    return url


# ============================================================
# HTTP GET
# ============================================================

def _http_get_raw(
    url: str,
    timeout: int,
    extra_headers: Optional[Dict[str, str]] = None,
    salida_binaria: bool = False,
    progress_cb: Optional[
        Callable[[int, int], None]
    ] = None,
    destino_archivo: Optional[str] = None,
) -> Dict[str, Any]:

    resultados: Dict[str, Any] = {
        "ok": False,
        "data": None,
        "ruta": None,
        "bytes_descargados": 0,
        "bytes_totales": 0,
        "sha256": None,
        "url_final": None,
        "errores": [],
    }

    headers = {
        "User-Agent": (
            f"FacturasVentas-SIS/{APP_VERSION}"
        ),
        "Accept": "*/*",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    if extra_headers:
        headers.update(extra_headers)

    estrategias = []

    # --------------------------------------------------------
    # 1. HTTPS normal
    # --------------------------------------------------------

    estrategias.append(
        (url, None)
    )

    # --------------------------------------------------------
    # 2. HTTPS sin validación SSL
    # --------------------------------------------------------

    if ALLOW_INSECURE_SSL_FALLBACK:

        estrategias.append(
            (
                url,
                _crear_contexto_ssl(True)
            )
        )

    # --------------------------------------------------------
    # 3. HTTP
    # --------------------------------------------------------

    url_http = _alternar_http(url)

    if url_http != url:

        estrategias.append(
            (
                url_http,
                None
            )
        )

        # ----------------------------------------------------
        # 4. HTTP sin SSL
        # ----------------------------------------------------

        if ALLOW_INSECURE_SSL_FALLBACK:

            estrategias.append(
                (
                    url_http,
                    _crear_contexto_ssl(True)
                )
            )

    ultimo_error = None

    for idx, (u, ctx) in enumerate(
        estrategias,
        start=1
    ):

        try:

            resultados["url_final"] = u

            req = urllib.request.Request(
                u,
                headers=headers,
                method="GET"
            )

            kwargs = {
                "timeout": timeout
            }

            if ctx is not None:
                kwargs["context"] = ctx

            with urllib.request.urlopen(
                req,
                **kwargs
            ) as resp:

                total_bytes = int(
                    resp.headers.get(
                        "Content-Length"
                    ) or 0
                )

                resultados[
                    "bytes_totales"
                ] = total_bytes

                # ==================================================
                # GUARDAR EN ARCHIVO
                # ==================================================

                if destino_archivo:

                    directorio = os.path.dirname(
                        destino_archivo
                    )

                    if directorio:
                        os.makedirs(
                            directorio,
                            exist_ok=True
                        )

                    descargado = 0

                    with open(
                        destino_archivo,
                        "wb"
                    ) as out:

                        while True:

                            chunk = resp.read(
                                64 * 1024
                            )

                            if not chunk:
                                break

                            out.write(chunk)

                            descargado += len(
                                chunk
                            )

                            resultados[
                                "bytes_descargados"
                            ] = descargado

                            if (
                                progress_cb
                                and total_bytes
                            ):

                                try:

                                    progress_cb(
                                        descargado,
                                        total_bytes
                                    )

                                except Exception:
                                    pass

                    resultados["ok"] = True

                    resultados[
                        "ruta"
                    ] = destino_archivo

                    resultados[
                        "sha256"
                    ] = _sha256_archivo(
                        destino_archivo
                    )

                    return resultados

                # ==================================================
                # DEVOLVER DATA
                # ==================================================

                raw = resp.read()

                resultados["data"] = raw

                resultados[
                    "bytes_descargados"
                ] = len(raw)

                resultados["ok"] = True

                return resultados

        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            ssl.SSLError,
            OSError,
        ) as e:

            ultimo_error = (
                f"{type(e).__name__}: {e}"
            )

            resultados[
                "errores"
            ].append(
                f"[{idx}] {ultimo_error}"
            )

            continue

        except Exception as e:

            ultimo_error = (
                f"{type(e).__name__}: {e}"
            )

            resultados[
                "errores"
            ].append(
                f"[{idx}] {ultimo_error}"
            )

            continue

    resultados[
        "errores"
    ].append(
        f"URL original: {url}"
    )

    return resultados


# ============================================================
# SHA256
# ============================================================

def _sha256_archivo(
    ruta: str,
    progress_cb: Optional[
        Callable[[int, int], None]
    ] = None,
) -> str:

    h = hashlib.sha256()

    if not os.path.exists(ruta):
        return ""

    total = os.path.getsize(ruta)

    leido = 0

    with open(
        ruta,
        "rb"
    ) as f:

        while True:

            buf = f.read(
                64 * 1024
            )

            if not buf:
                break

            h.update(buf)

            leido += len(buf)

            if (
                progress_cb
                and total
            ):

                try:

                    progress_cb(
                        leido,
                        total
                    )

                except Exception:
                    pass

    return h.hexdigest()


# ============================================================
# VERSION
# ============================================================

def _parse_version(
    version_str: str
) -> Tuple[int, ...]:

    try:

        return tuple(
            int(x)
            for x in version_str.strip().split(".")
        )

    except Exception:

        return (
            0,
            0,
            0
        )


def version_disponible(
    local: str,
    remota: str
) -> bool:

    return (
        _parse_version(remota)
        >
        _parse_version(local)
    )


# ============================================================
# RUTAS
# ============================================================

def obtener_ruta_ejecutable() -> str:

    if getattr(
        sys,
        "frozen",
        False
    ):

        return sys.executable

    return os.path.abspath(
        sys.argv[0]
    )


def obtener_directorio_ejecutable() -> str:

    return os.path.dirname(
        obtener_ruta_ejecutable()
    )


def obtener_ruta_app_exe() -> str:

    if getattr(
        sys,
        "frozen",
        False
    ):

        return sys.executable

    return os.path.join(
        obtener_directorio_ejecutable(),
        APP_EXE_NAME
    )


# ============================================================
# CONSULTAR VERSION REMOTA
# ============================================================

def consultar_version_remota(
    url: Optional[str] = None,
    timeout: int = 10,
) -> Dict[str, Any]:

    destino = (
        url
        or VERSION_URL
    )

    resultado: Dict[str, Any] = {

        "ok": False,

        "hay_actualizacion": False,

        "version_remota": None,

        "version_local": APP_VERSION,

        "download_url": None,

        "patch_url": None,

        "strategy": None,

        "force_update": False,

        "checksum_sha256": None,

        "file_size_bytes": 0,

        "min_version_to_patch": None,

        "notas": None,

        "published_at": None,

        "puede_autoaplicar": False,

        "url_version_json_usada": None,

        "error": None,
    }

    try:

        http_res = _http_get_raw(
            destino,
            timeout=timeout,
            extra_headers={
                "Accept": "application/json"
            }
        )

        if not http_res["ok"]:

            err_list = (
                http_res.get(
                    "errores"
                )
                or []
            )

            if len(err_list) >= 2:
                msj = err_list[-2]

            elif err_list:
                msj = err_list[0]

            else:
                msj = "Error desconocido"

            resultado["error"] = msj

            return resultado

        resultado[
            "url_version_json_usada"
        ] = http_res.get(
            "url_final"
        )

        raw_bytes = (
            http_res.get(
                "data"
            )
            or b""
        )

        raw = raw_bytes.decode(
            "utf-8",
            errors="replace"
        )

        try:

            datos = json.loads(
                raw
            )

        except json.JSONDecodeError:

            resultado[
                "error"
            ] = (
                "El archivo de versión remoto "
                "es inválido (JSON corrupto)"
            )

            return resultado

        # ==================================================
        # LEER VERSION.JSON
        # ==================================================

        version_remota = str(
            datos.get(
                "version",
                ""
            )
        ).strip()

        download_url = str(
            datos.get(
                "download_url",
                ""
            )
        ).strip() or None

        patch_url = str(
            datos.get(
                "patch_url",
                ""
            )
        ).strip() or None

        strategy = str(
            datos.get(
                "strategy",
                ""
            )
        ).strip() or None

        force_update = bool(
            datos.get(
                "force_update",
                False
            )
        )

        checksum = str(
            datos.get(
                "checksum_sha256",
                ""
            )
        ).strip() or None

        try:

            file_size = int(
                datos.get(
                    "file_size_bytes"
                )
                or 0
            )

        except Exception:

            file_size = 0

        min_patch = str(
            datos.get(
                "min_version_to_patch",
                ""
            )
        ).strip() or None

        notas = (
            datos.get(
                "release_notes"
            )
            or datos.get(
                "notes"
            )
            or None
        )

        published_at = str(
            datos.get(
                "published_at",
                ""
            )
        ).strip() or None

        # ==================================================
        # GUARDAR RESULTADOS
        # ==================================================

        resultado["ok"] = True

        resultado[
            "version_remota"
        ] = (
            version_remota
            or None
        )

        resultado[
            "download_url"
        ] = download_url

        resultado[
            "patch_url"
        ] = patch_url

        resultado[
            "strategy"
        ] = strategy

        resultado[
            "force_update"
        ] = force_update

        resultado[
            "checksum_sha256"
        ] = checksum

        resultado[
            "file_size_bytes"
        ] = file_size

        resultado[
            "min_version_to_patch"
        ] = min_patch

        resultado[
            "notas"
        ] = notas

        resultado[
            "published_at"
        ] = published_at

        # ==================================================
        # COMPARAR VERSION
        # ==================================================

        if (
            version_remota
            and version_disponible(
                APP_VERSION,
                version_remota
            )
        ):

            resultado[
                "hay_actualizacion"
            ] = True

        # ==================================================
        # VALIDAR SI PUEDE USAR ZIP PATCH
        # ==================================================

        if (
            resultado[
                "hay_actualizacion"
            ]
            and patch_url
            and strategy == "zip_patch"
            and getattr(
                sys,
                "frozen",
                False
            )
        ):

            cumple_min = True

            if min_patch:

                cumple_min = not (
                    version_disponible(
                        APP_VERSION,
                        min_patch
                    )
                )

            resultado[
                "puede_autoaplicar"
            ] = cumple_min

    except Exception as e:

        resultado[
            "error"
        ] = (
            f"Error inesperado: {e}"
        )

    return resultado


# ============================================================
# ABRIR DESCARGA
# ============================================================

def abrir_descarga(
    url: str
) -> bool:

    try:

        webbrowser.open(
            url,
            new=2
        )

        return True

    except Exception:

        return False


# ============================================================
# DESCARGAR ARCHIVO
# ============================================================

def descargar_archivo(
    url: str,
    destino: str,
    progress_cb: Optional[
        Callable[[int, int], None]
    ] = None,
    timeout: int = 300,
) -> Dict[str, Any]:

    res: Dict[str, Any] = {

        "ok": False,

        "ruta": None,

        "bytes_descargados": 0,

        "bytes_totales": 0,

        "sha256": None,

        "error": None,
    }

    try:

        http_res = _http_get_raw(
            url,
            timeout=timeout,
            progress_cb=progress_cb,
            destino_archivo=destino
        )

        if not http_res["ok"]:

            err_list = (
                http_res.get(
                    "errores"
                )
                or []
            )

            if len(err_list) >= 2:
                msj = err_list[-2]

            elif err_list:
                msj = err_list[0]

            else:
                msj = "Error desconocido"

            res[
                "error"
            ] = msj

            if os.path.exists(destino):

                try:
                    os.remove(destino)
                except Exception:
                    pass

            return res

        res[
            "ruta"
        ] = destino

        res[
            "sha256"
        ] = (
            http_res.get(
                "sha256"
            )
            or _sha256_archivo(
                destino
            )
        )

        res[
            "bytes_descargados"
        ] = http_res.get(
            "bytes_descargados",
            0
        )

        res[
            "bytes_totales"
        ] = http_res.get(
            "bytes_totales",
            0
        )

        res["ok"] = True

    except Exception as e:

        res[
            "error"
        ] = (
            f"Error de descarga: {e}"
        )

        if os.path.exists(destino):

            try:
                os.remove(destino)
            except Exception:
                pass

    return res


# ============================================================
# EXTRAER ZIP
# ============================================================

def extraer_zip(
    ruta_zip: str,
    dir_destino: str,
    progress_cb: Optional[
        Callable[[int, int], None]
    ] = None,
) -> Dict[str, Any]:

    res: Dict[str, Any] = {

        "ok": False,

        "dir_destino": dir_destino,

        "error": None
    }

    try:

        os.makedirs(
            dir_destino,
            exist_ok=True
        )

        with zipfile.ZipFile(
            ruta_zip,
            "r"
        ) as zf:

            miembros = zf.infolist()

            total = len(
                miembros
            )

            # ------------------------------------------------
            # SEGURIDAD CONTRA ZIP SLIP
            # ------------------------------------------------

            destino_real = os.path.realpath(
                dir_destino
            )

            for miembro in miembros:

                nombre = miembro.filename

                ruta_final = os.path.realpath(
                    os.path.join(
                        dir_destino,
                        nombre
                    )
                )

                if not (
                    ruta_final == destino_real
                    or ruta_final.startswith(
                        destino_real
                        + os.sep
                    )
                ):

                    raise RuntimeError(
                        "El ZIP contiene una ruta insegura: "
                        + nombre
                    )

            # ------------------------------------------------
            # EXTRAER
            # ------------------------------------------------

            for idx, miembro in enumerate(
                miembros,
                start=1
            ):

                try:

                    zf.extract(
                        miembro,
                        dir_destino
                    )

                except Exception as e:

                    raise RuntimeError(
                        f"No se pudo extraer "
                        f"{miembro.filename}: {e}"
                    )

                if (
                    progress_cb
                    and total
                ):

                    try:

                        progress_cb(
                            idx,
                            total
                        )

                    except Exception:
                        pass

        res["ok"] = True

    except zipfile.BadZipFile:

        res[
            "error"
        ] = (
            "El archivo ZIP está corrupto"
        )

    except Exception as e:

        res[
            "error"
        ] = (
            f"Error al extraer ZIP: {e}"
        )

    return res


# ============================================================
# GENERAR BAT DE ACTUALIZACIÓN
# ============================================================

def _generar_script_actualizacion(
    ruta_app_vieja: str,
    dir_extraccion: str,
    ruta_app_nueva: str,
) -> str:

    dir_app = os.path.dirname(
        ruta_app_vieja
    )

    nombre_bat = (
        "_update_helper.bat"
    )

    ruta_bat = os.path.join(
        dir_app,
        nombre_bat
    )

    nombre_exe = os.path.basename(
        ruta_app_vieja
    )

    contenido = f"""@echo off
setlocal EnableExtensions DisableDelayedExpansion

chcp 65001 >nul

title FacturasVentas - Actualizando

echo.
echo ============================================
echo       FacturasVentas - ACTUALIZACION
echo ============================================
echo.

set "DIR_APP={dir_app}"
set "DIR_PATCH={dir_extraccion}"
set "EXE_OLD={ruta_app_vieja}"
set "EXE_NEW={ruta_app_nueva}"
set "RELAUNCH={os.path.join(dir_app, nombre_exe)}"
set "SELF={ruta_bat}"

echo [1/6] Esperando cierre de la aplicacion...
echo.

ping -n 3 127.0.0.1 >nul

if not exist "%DIR_PATCH%" (
    echo [ERROR] Carpeta del parche no encontrada:
    echo %DIR_PATCH%
    goto error
)

if not exist "%EXE_NEW%" (
    echo [ERROR] No se encontro el nuevo ejecutable:
    echo %EXE_NEW%
    goto error
)

echo [2/6] Cerrando aplicacion anterior...

taskkill /F /IM "{nombre_exe}" >nul 2>&1

ping -n 3 127.0.0.1 >nul

echo [3/6] Preparando archivos...

if exist "%DIR_APP%\\_old_version" (
    rmdir /S /Q "%DIR_APP%\\_old_version" >nul 2>&1
)

mkdir "%DIR_APP%\\_old_version" >nul 2>&1

echo [4/6] Copiando archivos nuevos...

xcopy "%DIR_PATCH%\\*.*" "%DIR_APP%\\" /E /H /C /I /Y

if errorlevel 1 (
    echo.
    echo [ERROR] Error copiando archivos.
    goto error
)

echo.
echo [5/6] Verificando ejecutable...

if not exist "%RELAUNCH%" (
    echo [ERROR] El nuevo ejecutable no existe:
    echo %RELAUNCH%
    goto error
)

echo.
echo [6/6] Actualizacion completada correctamente.

echo.
echo ============================================
echo          ACTUALIZACION EXITOSA
echo ============================================
echo.

ping -n 2 127.0.0.1 >nul

echo Iniciando nueva version...

start "" "%RELAUNCH%" --post-update

ping -n 3 127.0.0.1 >nul

echo Limpiando archivos temporales...

if exist "%DIR_PATCH%" (
    rmdir /S /Q "%DIR_PATCH%" >nul 2>&1
)

del /F /Q "%SELF%" >nul 2>&1

exit /b 0


:error

echo.
echo ============================================
echo   ERROR: No se pudo completar la actualizacion
echo ============================================
echo.
echo Carpeta:
echo %DIR_PATCH%
echo.
echo Ejecutable:
echo %RELAUNCH%
echo.
echo El programa NO ha sido actualizado.
echo.
pause

exit /b 1
"""

    try:

        with open(
            ruta_bat,
            "w",
            encoding="utf-8",
            errors="replace"
        ) as f:

            f.write(
                contenido
            )

    except Exception:

        with open(
            ruta_bat,
            "w",
            encoding="cp1252",
            errors="replace"
        ) as f:

            f.write(
                contenido
            )

    return ruta_bat


# ============================================================
# APLICAR PARCHE
# ============================================================

def aplicar_parche_y_cerrar(
    ruta_zip: str,
    checksum_esperado: Optional[str] = None,
    descargar_progress_cb: Optional[
        Callable[[int, int], None]
    ] = None,
    extraer_progress_cb: Optional[
        Callable[[int, int], None]
    ] = None,
) -> Dict[str, Any]:

    res: Dict[str, Any] = {

        "ok": False,

        "bat_path": None,

        "error": None
    }

    # --------------------------------------------------------
    # SOLO EXE
    # --------------------------------------------------------

    if not getattr(
        sys,
        "frozen",
        False
    ):

        res[
            "error"
        ] = (
            "El auto-parche solo funciona "
            "cuando la app está compilada a .exe"
        )

        return res

    # --------------------------------------------------------
    # EXISTENCIA ZIP
    # --------------------------------------------------------

    if not os.path.exists(
        ruta_zip
    ):

        res[
            "error"
        ] = (
            "No existe el archivo ZIP descargado: "
            + ruta_zip
        )

        return res

    # --------------------------------------------------------
    # CHECKSUM
    # --------------------------------------------------------

    if checksum_esperado:

        checksum_actual = (
            _sha256_archivo(
                ruta_zip
            )
        )

        if (
            checksum_actual.lower()
            != checksum_esperado.lower()
        ):

            res[
                "error"
            ] = (
                "Verificación de integridad fallida. "
                "El checksum SHA256 no coincide."
            )

            return res

    # --------------------------------------------------------
    # RUTAS
    # --------------------------------------------------------

    dir_app = (
        obtener_directorio_ejecutable()
    )

    ruta_app_exe = (
        obtener_ruta_app_exe()
    )

    tmp_patch = os.path.join(
        dir_app,
        "_pending_patch"
    )

    # --------------------------------------------------------
    # ELIMINAR PARCHE ANTERIOR
    # --------------------------------------------------------

    if os.path.exists(
        tmp_patch
    ):

        try:

            shutil.rmtree(
                tmp_patch,
                ignore_errors=True
            )

        except Exception:
            pass

    # --------------------------------------------------------
    # EXTRAER
    # --------------------------------------------------------

    ext_res = extraer_zip(
        ruta_zip,
        tmp_patch,
        progress_cb=extraer_progress_cb
    )

    if not ext_res["ok"]:

        res[
            "error"
        ] = ext_res[
            "error"
        ]

        try:

            shutil.rmtree(
                tmp_patch,
                ignore_errors=True
            )

        except Exception:
            pass

        return res

    # --------------------------------------------------------
    # BUSCAR MAIN.EXE
    # --------------------------------------------------------

    posibles_exes = [

        os.path.join(
            tmp_patch,
            os.path.basename(
                ruta_app_exe
            )
        ),

        os.path.join(
            tmp_patch,
            APP_EXE_NAME
        ),
    ]

    exe_en_zip = next(
        (
            p
            for p in posibles_exes
            if os.path.exists(p)
        ),
        None
    )

    # --------------------------------------------------------
    # SI NO ESTA DIRECTAMENTE, BUSCAR RECURSIVAMENTE
    # --------------------------------------------------------

    if not exe_en_zip:

        for root, dirs, files in os.walk(
            tmp_patch
        ):

            if APP_EXE_NAME in files:

                exe_en_zip = os.path.join(
                    root,
                    APP_EXE_NAME
                )

                break

    if not exe_en_zip:

        res[
            "error"
        ] = (
            f"No se encontró {APP_EXE_NAME} "
            "dentro del ZIP."
        )

        try:

            shutil.rmtree(
                tmp_patch,
                ignore_errors=True
            )

        except Exception:
            pass

        return res

    # --------------------------------------------------------
    # GENERAR BAT
    # --------------------------------------------------------

    try:

        ruta_bat = (
            _generar_script_actualizacion(
                ruta_app_exe,
                tmp_patch,
                exe_en_zip
            )
        )

    except Exception as e:

        res[
            "error"
        ] = (
            "No se pudo crear el script "
            f"de actualización: {e}"
        )

        return res

    res["ok"] = True

    res[
        "bat_path"
    ] = ruta_bat

    return res


# ============================================================
# EJECUTAR ACTUALIZADOR
# ============================================================

def ejecutar_actualizador_y_salir(
    ruta_bat: str
) -> bool:

    try:

        ruta_bat_abs = os.path.abspath(
            ruta_bat
        )

        if not os.path.exists(
            ruta_bat_abs
        ):

            return False

        if os.name == "nt":

            creation_flags = (
                0x08000000
            )

            subprocess.Popen(
                [
                    "cmd.exe",
                    "/C",
                    ruta_bat_abs
                ],
                shell=False,
                close_fds=True,
                creationflags=creation_flags,
                cwd=os.path.dirname(
                    ruta_bat_abs
                )
            )

        else:

            subprocess.Popen(
                [
                    "bash",
                    ruta_bat_abs
                ]
            )

        return True

    except Exception:

        return False


# ============================================================
# FUNCIÓN COMPLETA PARA ACTUALIZAR
# ============================================================

def actualizar_desde_servidor(
    progress_descarga_cb: Optional[
        Callable[[int, int], None]
    ] = None,
    progress_extraccion_cb: Optional[
        Callable[[int, int], None]
    ] = None,
) -> Dict[str, Any]:

    resultado: Dict[str, Any] = {

        "ok": False,

        "actualizacion_disponible": False,

        "actualizacion_aplicada": False,

        "version_actual": APP_VERSION,

        "version_nueva": None,

        "error": None,

        "bat_path": None,
    }

    # --------------------------------------------------------
    # CONSULTAR VERSION
    # --------------------------------------------------------

    info = consultar_version_remota()

    if not info["ok"]:

        resultado[
            "error"
        ] = (
            info.get(
                "error"
            )
            or "No se pudo consultar la versión."
        )

        return resultado

    if not info[
        "hay_actualizacion"
    ]:

        resultado["ok"] = True

        return resultado

    resultado[
        "actualizacion_disponible"
    ] = True

    resultado[
        "version_nueva"
    ] = info.get(
        "version_remota"
    )

    # --------------------------------------------------------
    # VERIFICAR PATCH
    # --------------------------------------------------------

    if not info[
        "puede_autoaplicar"
    ]:

        resultado[
            "error"
        ] = (
            "La actualización está disponible, "
            "pero no puede aplicarse automáticamente."
        )

        return resultado

    patch_url = info.get(
        "patch_url"
    )

    if not patch_url:

        resultado[
            "error"
        ] = (
            "version.json no contiene patch_url."
        )

        return resultado

    # --------------------------------------------------------
    # CARPETA TEMPORAL
    # --------------------------------------------------------

    dir_app = (
        obtener_directorio_ejecutable()
    )

    ruta_zip = os.path.join(
        dir_app,
        "_update_package.zip"
    )

    # --------------------------------------------------------
    # ELIMINAR ZIP ANTERIOR
    # --------------------------------------------------------

    if os.path.exists(
        ruta_zip
    ):

        try:
            os.remove(
                ruta_zip
            )
        except Exception:
            pass

    # --------------------------------------------------------
    # DESCARGAR
    # --------------------------------------------------------

    descarga = descargar_archivo(
        patch_url,
        ruta_zip,
        progress_cb=progress_descarga_cb,
        timeout=300
    )

    if not descarga["ok"]:

        resultado[
            "error"
        ] = (
            descarga.get(
                "error"
            )
            or "No se pudo descargar el parche."
        )

        return resultado

    # --------------------------------------------------------
    # VALIDAR TAMAÑO
    # --------------------------------------------------------

    file_size = int(
        info.get(
            "file_size_bytes"
        )
        or 0
    )

    if file_size > 0:

        tamano_real = os.path.getsize(
            ruta_zip
        )

        if tamano_real != file_size:

            resultado[
                "error"
            ] = (
                "El tamaño del ZIP descargado "
                "no coincide con file_size_bytes."
            )

            try:
                os.remove(ruta_zip)
            except Exception:
                pass

            return resultado

    # --------------------------------------------------------
    # APLICAR PARCHE
    # --------------------------------------------------------

    parche = aplicar_parche_y_cerrar(
        ruta_zip,
        checksum_esperado=info.get(
            "checksum_sha256"
        ),
        descargar_progress_cb=progress_descarga_cb,
        extraer_progress_cb=progress_extraccion_cb
    )

    if not parche["ok"]:

        resultado[
            "error"
        ] = (
            parche.get(
                "error"
            )
            or "No se pudo preparar la actualización."
        )

        return resultado

    resultado[
        "ok"
    ] = True

    resultado[
        "actualizacion_aplicada"
    ] = True

    resultado[
        "bat_path"
    ] = parche.get(
        "bat_path"
    )

    return resultado