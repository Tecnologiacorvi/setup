#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
CORVI CONTROL DE ASISTENCIA — SISTEMA DE REGISTRO DE JORNADA Y TELEMETRÍA OPERATIVA
=============================================================================
Firma: CORVI CONSULTORES S.A.S.
Propósito: Monitoreo objetivo de jornada laboral remota, telemetría granular
           de aplicaciones y páginas web (desglose exacto de pestañas de Chrome y
           archivos de trabajo), reconocimiento de Oficina Virtual CORVI
           (WorkAdventure) y Copiloto AI (Antigravity), registro de inactividad (AFK),
           verificación continua de internet, capturas de pantalla cada 5 min
           y consolidación ejecutiva diaria.
Plataformas compatibles: Linux (X11 / Linux Mint / Ubuntu) y Windows 10/11.
=============================================================================
"""

import os
import base64
import sys
import time
import json
import socket
import datetime
import threading
import subprocess
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Importación de PIL para capturas de pantalla de alta fidelidad y ultra-compresión
try:
    from PIL import ImageGrab
except ImportError:
    print("[ERROR] Se requiere la librería 'Pillow' (PIL). Instálela con: pip install Pillow")
    sys.exit(1)

# =============================================================================
# CONFIGURACIÓN Y RUTAS BASE
# =============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Almacenamiento universal y persistente por usuario (siempre en el perfil del colaborador)
USER_DATA_DIR = os.path.expanduser("~/.corvi_asistencia")
_OLD_DIR = os.path.expanduser("~/.corvi_auditor")
if os.path.exists(_OLD_DIR) and not os.path.exists(USER_DATA_DIR):
    try:
        shutil.move(_OLD_DIR, USER_DATA_DIR)
    except Exception:
        pass
os.makedirs(USER_DATA_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(USER_DATA_DIR, "config.json")
REGISTROS_DIR = os.path.join(USER_DATA_DIR, "REGISTROS_JORNADA")
os.makedirs(REGISTROS_DIR, exist_ok=True)

DEFAULT_CONFIG = {
    "registrado": False,
    "colaborador_nombre": "__COLABORADOR_NOMBRE__",
    "colaborador_cargo": "Auxiliar Contable y Tributario",
    "colaborador_cedula": "",
    "colaborador_correo": "",
    "empresa": "CORVI CONSULTORES S.A.S.",
    "intervalo_telemetria_seg": 10,
    "intervalo_captura_min": 5,          # Cada 5 minutos (12 capturas/hora)
    "umbral_inactividad_afk_seg": 300,   # 5 minutos sin tocar mouse/teclado
    "puerto_web": 8765,
    "notificaciones_activas": True,
    "oficina_virtual_url": "https://play.workadventu.re/@/corvi-consultores-1780437475/corvi-consultores-2/corvi-star-up",
    "oficina_virtual_keywords": [
        "WORKADVENTURE", "CORVI-CONSULTORES", "CORVI-STAR-UP", "PLAY.WORKADVENTU.RE"
    ],
    "clientes_autorizados": [
        "CIDERAL", "KDT", "BOCANOS", "FUMIPARTES", "CORVI", "SIIGO", "ODOO",
        "DIAN", "SECRETARIA DE HACIENDA", "SDH", "BOGOTA", "BANCOLOMBIA",
        "BANCO", "CAMARA DE COMERCIO", "CCB", "RUES", "SUPERINTENDENCIA"
    ],
    "sitios_ocio": [
        "facebook.com", "instagram.com", "tiktok.com", "twitter.com", "x.com",
        "netflix.com", "twitch.tv", "primevideo.com", "disneyplus.com"
    ],
    "cerrar_al_finalizar": True
}

def cargar_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                cfg = DEFAULT_CONFIG.copy()
                cfg.update(data)
                return cfg
        except Exception:
            return DEFAULT_CONFIG.copy()
    else:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
        return DEFAULT_CONFIG.copy()

def guardar_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

def notificar_registro_colaborador(nombre, cedula, cargo, correo, empresa="CORVI CONSULTORES S.A.S."):
    def _enviar():
        try:
            import smtplib
            from email.mime.text import MIMEText
            asunto = f"🔔 [CONTROL DE ASISTENCIA] Nuevo Puesto Remoto Vinculado: {nombre} ({cargo})"
            cuerpo = f"""Se ha vinculado con éxito un nuevo equipo al sistema de control de asistencia y telemetría laboral de CORVI CONSULTORES S.A.S.

• Empresa / Organización: {empresa}
• Colaborador: {nombre}
• Cédula: {cedula}
• Cargo: {cargo}
• Correo de contacto: {correo}
• Fecha y Hora: {datetime.datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}
• Nombre del Equipo (Host): {socket.gethostname()}
• Sistema Operativo: {'Windows' if IS_WINDOWS else 'Linux'}

A partir de este momento, cada jornada laboral que {nombre} inicie y finalice generará automáticamente su reporte diario con capturas de pantalla, tiempo efectivo y métricas de internet directamente a los registros de la firma.
"""
            msg = MIMEText(cuerpo, "plain", "utf-8")
            msg["From"] = "CORVI Control de Asistencia <linda.gutierrez@corviconsultores.com>"
            destinatarios_admin = ["tecnologia@corviconsultores.com", "r.davidmauriciop@gmail.com"]
            msg["To"] = ", ".join(destinatarios_admin)
            msg["Subject"] = asunto

            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as s:
                s.login("linda.gutierrez@corviconsultores.com", "saleehtsxyekoehc")
                s.sendmail("linda.gutierrez@corviconsultores.com", destinatarios_admin, msg.as_string())
            print(f"[CONTROL DE ASISTENCIA] 📧 Notificación de registro despachada a: {destinatarios_admin}")
        except Exception as e:
            print(f"[CONTROL DE ASISTENCIA] Aviso: No se pudo enviar notificación por email (sin conexión o error): {e}")

    threading.Thread(target=_enviar, daemon=True).start()

CONFIG = cargar_config()

# =============================================================================
# ADAPTADORES DEL SISTEMA OPERATIVO (LINUX / WINDOWS)
# =============================================================================
IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")

_xlib = None
_xss = None
_display = None

if IS_LINUX:
    try:
        import ctypes
        import ctypes.util
        _xlib = ctypes.cdll.LoadLibrary("libX11.so.6")
        _xss = ctypes.cdll.LoadLibrary("libXss.so.1")
        _display = _xlib.XOpenDisplay(None)
        
        class XScreenSaverInfo(ctypes.Structure):
            _fields_ = [
                ('window', ctypes.c_ulong),
                ('state', ctypes.c_int),
                ('kind', ctypes.c_int),
                ('til_or_since', ctypes.c_ulong),
                ('idle', ctypes.c_ulong),
                ('event_mask', ctypes.c_ulong)
            ]
        _XScreenSaverInfo = XScreenSaverInfo
    except Exception as e:
        print(f"[WARN] No se pudo inicializar libXss de X11: {e}")

def get_idle_seconds():
    """Retorna los segundos transcurridos desde la última acción de teclado o ratón."""
    if IS_WINDOWS:
        try:
            import ctypes
            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
            if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
                millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
                return millis / 1000.0
        except Exception:
            return 0.0
    elif IS_LINUX:
        try:
            import ctypes
            if _display and _xlib and _xss:
                root = _xlib.XDefaultRootWindow(_display)
                info = _XScreenSaverInfo()
                _xss.XScreenSaverQueryInfo(_display, root, ctypes.byref(info))
                return info.idle / 1000.0
        except Exception:
            pass
        try:
            out = subprocess.check_output(["xprintidle"], stderr=subprocess.DEVNULL).decode().strip()
            return float(out) / 1000.0
        except Exception:
            return 0.0
    return 0.0

def get_active_window_info():
    """
    Retorna (app_name, window_title).
    En Linux usa xprop; en Windows usa user32.
    """
    if IS_WINDOWS:
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value.strip() or "Escritorio / Vacío"
            
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            app_name = "Aplicación Windows"
            try:
                import psutil
                proc = psutil.Process(pid.value)
                app_name = proc.name()
            except Exception:
                pass
            
            # Respaldo nativo con Win32 API si psutil no está disponible o falla
            if app_name == "Aplicación Windows":
                try:
                    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                    h_proc = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
                    if h_proc:
                        buf = ctypes.create_unicode_buffer(1024)
                        size = ctypes.c_ulong(1024)
                        if ctypes.windll.kernel32.QueryFullProcessImageNameW(h_proc, 0, buf, ctypes.byref(size)):
                            app_name = os.path.basename(buf.value)
                        ctypes.windll.kernel32.CloseHandle(h_proc)
                except Exception:
                    pass

            return app_name, title
        except Exception:
            return "Desconocido", "Ventana Desconocida"

    elif IS_LINUX:
        try:
            root_out = subprocess.check_output(
                ["xprop", "-root", "_NET_ACTIVE_WINDOW"],
                stderr=subprocess.DEVNULL
            ).decode()
            win_id = root_out.strip().split()[-1]
            if win_id == "0x0" or not win_id.startswith("0x"):
                return "Escritorio", "Escritorio / Sin Ventana Activa"

            title_out = subprocess.check_output(
                ["xprop", "-id", win_id, "_NET_WM_NAME", "WM_NAME"],
                stderr=subprocess.DEVNULL
            ).decode()
            title = "Ventana Sin Título"
            for line in title_out.splitlines():
                if "=" in line:
                    parts = line.split("=", 1)
                    val = parts[1].strip()
                    if val.startswith('"') and val.endswith('"'):
                        title = val[1:-1]
                        break

            class_out = subprocess.check_output(
                ["xprop", "-id", win_id, "WM_CLASS"],
                stderr=subprocess.DEVNULL
            ).decode()
            app_name = "Desconocida"
            if "=" in class_out:
                parts = class_out.split("=", 1)[1].strip().split(",")
                if parts:
                    app_name = parts[-1].strip().replace('"', '')

            return app_name, title
        except Exception:
            return "Escritorio", "Escritorio / Reposo"

    return "Sistema", "Ventana de Sistema"

def check_internet_status(hosts=[("8.8.8.8", 53), ("1.1.1.1", 53)], timeout=1.0):
    """Verifica conectividad real a internet mediante sockets TCP ultralivianos."""
    t0 = time.time()
    for host, port in hosts:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((host, port))
            s.close()
            latency = round((time.time() - t0) * 1000, 1)
            return True, latency
        except Exception:
            continue
    return False, 0.0

# =============================================================================
# DESGLOSE GRANULAR DE APLICACIONES, NAVEGADOR Y DOCUMENTOS
# =============================================================================
def desglosar_actividad_web(app_name, title):
    """
    Identifica con precisión quirúrgica la plataforma, página y contexto exacto.
    Retorna (plataforma_label, titulo_limpio, tipo_categoria, es_alerta, detalle_alerta).
    """
    app_lower = app_name.lower()
    es_navegador = any(b in app_lower for b in ["chrome", "chromium", "firefox", "edge", "brave", "opera"])
    
    # Limpiar sufijos típicos de títulos de navegadores (soporta guion ASCII, guion medio en-dash, guion largo em-dash y barra)
    titulo_limpio = title
    for b_suf in [
        "Google Chrome", "Chromium", "Mozilla Firefox", "Microsoft Edge", "Brave", "Opera"
    ]:
        for sep in [" - ", " – ", " — ", " | ", " -", " –", " —"]:
            pat = f"{sep}{b_suf}"
            if titulo_limpio.endswith(pat):
                titulo_limpio = titulo_limpio[:-len(pat)].strip()
                break

    titulo_upper = titulo_limpio.upper()

    # 1. OFICINA VIRTUAL CORVI EN WORKADVENTURE
    oficina_kw = CONFIG.get("oficina_virtual_keywords", ["WORKADVENTURE", "CORVI-CONSULTORES", "CORVI-STAR-UP"])
    if any(k in titulo_upper for k in oficina_kw):
        return (
            "🏢 Oficina Virtual CORVI (WorkAdventure)",
            "WorkAdventure — Sede Virtual (Interacción Activa)",
            "Oficina Virtual (Activo)",
            False,
            "Presencia activa en la oficina virtual de CORVI"
        )

    # 2. PLATAFORMAS DE VIDEOLLAMADAS & REUNIONES (Google Meet / Teams / Zoom / Skype)
    if any(k in titulo_upper for k in ["MEET.GOOGLE.COM", "GOOGLE MEET"]) or titulo_upper.startswith("MEET - "):
        return (
            "📞 Google Meet",
            titulo_limpio,
            "Reunión & Videollamada Oficial",
            False,
            "Sesión activa en Google Meet"
        )
    if any(k in titulo_upper for k in ["MICROSOFT TEAMS", "TEAMS.MICROSOFT.COM"]):
        return (
            "📞 Microsoft Teams",
            titulo_limpio,
            "Reunión & Videollamada Oficial",
            False,
            "Sesión activa en Microsoft Teams"
        )
    if any(k in titulo_upper for k in ["ZOOM MEETING", "ZOOM WORKPLACE"]) or "ZOOM" in app_lower:
        return (
            "📞 Zoom",
            titulo_limpio,
            "Reunión & Videollamada Oficial",
            False,
            "Sesión activa en Zoom"
        )
    if "SKYPE" in titulo_upper or "skype" in app_lower:
        return (
            "📞 Skype",
            titulo_limpio,
            "Reunión & Videollamada Oficial",
            False,
            "Llamada o reunión en Skype"
        )

    # 3. INTELIGENCIA ARTIFICIAL & COPILOTO (Antigravity AI / Gemini / Claude / ChatGPT)
    if any(k in titulo_upper for k in ["ANTIGRAVITY", "GEMINI", "CHATGPT", "CLAUDE"]):
        return (
            "🤖 Copiloto Antigravity AI",
            titulo_limpio,
            "Asistencia Tecnológica AI",
            False,
            f"Trabajo con IA: {titulo_limpio[:50]}"
        )

    # 3. WHATSAPP WEB
    if "WHATSAPP" in titulo_upper:
        return (
            "💬 WhatsApp Web",
            titulo_limpio,
            "Comunicación con Clientes / Equipo",
            False,
            "Canal de mensajería operativa"
        )

    # 4. SISTEMAS CONTABLES Y ERP (Siigo, Odoo, DIAN, Clockify)
    if "SIIGO" in titulo_upper:
        return ("📊 Siigo Nube", titulo_limpio, "Sistemas Contables", False, "Operación contable oficial")
    if "ODOO" in titulo_upper:
        return ("📦 Odoo ERP", titulo_limpio, "Sistemas Contables & WMS", False, "Operación ERP")
    if "DIAN" in titulo_upper:
        return ("🏛️ Portal DIAN", titulo_limpio, "Impuestos & DIAN", False, "Gestión tributaria")
    if "CLOCKIFY" in titulo_upper:
        return ("⏱️ Clockify", titulo_limpio, "Control de Tiempo", False, "Módulo de horas")

    # 5. GOOGLE DRIVE / GOOGLE WORKSPACE
    if any(k in titulo_upper for k in ["GOOGLE DRIVE", "DRIVE", "HOJAS DE CÁLCULO", "DOCUMENTOS DE GOOGLE", "SHEETS", "DOCS"]):
        return ("📁 Google Drive & Documentos", titulo_limpio, "Gestión Documental", False, "Archivos de trabajo")
    if "GMAIL" in titulo_upper or "CORREO" in titulo_upper:
        return ("✉️ Correo Institucional (Gmail)", titulo_limpio, "Correo Institucional", False, "Revisión de correos")

    # 6. REDES SOCIALES Y OCIO EN NAVEGADOR
    if es_navegador:
        redes_map = {
            "INSTAGRAM": "🚨 Instagram",
            "FACEBOOK": "🚨 Facebook",
            "TIKTOK": "🚨 TikTok",
            "TWITTER": "🚨 X / Twitter",
            "X.COM": "🚨 X / Twitter",
            "NETFLIX": "🚨 Netflix",
            "TWITCH": "🚨 Twitch",
            "DISNEYPLUS": "🚨 Disney+",
            "PRIMEVIDEO": "🚨 Prime Video"
        }
        for kw, label_red in redes_map.items():
            if kw in titulo_upper:
                return (label_red, titulo_limpio, "Red Social / Ocio No Autorizado", True, f"Navegación en {label_red}")

    # 7. YOUTUBE (Música / Video)
    if "YOUTUBE" in titulo_upper:
        clean_yt = titulo_limpio.replace(" - YouTube", "").strip()
        return ("🎵 YouTube", clean_yt, "Multimedia en Foco", False, f"Reproducción activa: {clean_yt[:60]}")

    # 8. BÚSQUEDAS EN GOOGLE
    if "BUSCAR CON GOOGLE" in titulo_upper or "GOOGLE SEARCH" in titulo_upper:
        termino = titulo_limpio.replace(" - Buscar con Google", "").replace(" - Google Search", "").strip()
        return (f"🔍 Búsqueda: {termino[:35]}", titulo_limpio, "Investigación Web", False, f"Búsqueda: {termino}")

    # 9. Clientes autorizados en títulos
    for cliente in CONFIG.get("clientes_autorizados", []):
        if cliente in titulo_upper:
            return (f"💼 Cliente CORVI ({cliente})", titulo_limpio, "Operación Clientes", False, f"Trabajo en cuenta {cliente}")

    if es_navegador:
        nombre_web = titulo_limpio[:40] if len(titulo_limpio) > 40 else titulo_limpio
        return (f"🌐 {nombre_web}", titulo_limpio, "Navegación Web", False, "Consulta web")

    # No es navegador: Aplicaciones de escritorio (Excel, Calc, Terminal con Antigravity, Nemo, etc.)
    app_label = app_name
    cat = "Aplicación de Escritorio"
    if any(k in app_lower for k in ["excel", "calc", "soffice"]):
        app_label = "📗 Excel / Hoja de Cálculo"
        cat = "Contabilidad & Hojas de Trabajo"
    elif any(k in app_lower for k in ["word", "writer"]):
        app_label = "📘 Word / Editor de Texto"
        cat = "Documentación"
    elif any(k in app_lower for k in ["terminal", "bash", "gnome-terminal"]):
        if any(k in title.lower() for k in ["antigravity", "davidrp@"]):
            app_label = "🤖 Copiloto Antigravity AI (Terminal)"
            cat = "Asistencia & Consultoría AI"
        else:
            app_label = "💻 Terminal / Consola"
            cat = "Sistemas & Scripts"
    elif any(k in app_lower for k in ["nemo", "explorer", "files"]):
        app_label = "📁 Explorador de Archivos"
        cat = "Archivos Locales"

    return (app_label, title, cat, False, "Actividad de escritorio")

def check_audio_active():
    """
    Verifica si en el sistema operativo hay reproducción o captura de audio activa
    (ej. voz de compañeros en llamada WebRTC de WorkAdventure, Google Meet o micrófono abierto).
    """
    if IS_LINUX:
        try:
            # 1. Verificar streams de reproducción en PulseAudio/PipeWire
            out_sinks = subprocess.check_output(["pactl", "list", "sink-inputs"], stderr=subprocess.DEVNULL).decode("utf-8", "ignore").lower()
            if "corked: no" in out_sinks or "state: running" in out_sinks or "google-chrome" in out_sinks:
                return True
        except Exception:
            pass
        
        try:
            # 2. Verificar captura de micrófono en PulseAudio/PipeWire
            out_sources = subprocess.check_output(["pactl", "list", "source-outputs"], stderr=subprocess.DEVNULL).decode("utf-8", "ignore").lower()
            if "corked: no" in out_sources or "state: running" in out_sources:
                return True
        except Exception:
            pass

        try:
            # 3. Verificación directa de hardware ALSA
            import glob
            for f in glob.glob("/proc/asound/**/status", recursive=True):
                if "RUNNING" in open(f).read():
                    return True
        except Exception:
            pass

    return False


def inspeccionar_actividad_segundo_plano():
    """
    Inspecciona la actividad concurrente en el sistema operativo:
    1. Música / Audio en segundo plano (YouTube, Spotify, etc.) vía PulseAudio / PipeWire o sesiones de Chrome.
    2. Pestañas abiertas en segundo plano en todos los perfiles de Chrome (Default, Profile 1, Profile 2, etc.).
    3. Ventanas abiertas en el escritorio (X11).
    """
    resultado = {
        "audio_segundo_plano": None,
        "audio_app": None,
        "pestanas_abiertas": [],
        "ventanas_escritorio": []
    }

    # --- 1. DETECCIÓN DE AUDIO / MÚSICA EN SEGUNDO PLANO VÍA PACTL ---
    if IS_LINUX:
        try:
            pactl_out = subprocess.check_output(["pactl", "list", "sink-inputs"], stderr=subprocess.DEVNULL).decode("utf-8", "ignore")
            bloques = pactl_out.split("Sink Input #")
            for b in bloques[1:]:
                b_lower = b.lower()
                if "corked: no" in b_lower or "state: running" in b_lower:
                    media_name = ""
                    app_bin = ""
                    for line in b.splitlines():
                        line_str = line.strip()
                        if "media.name =" in line_str or "media.title =" in line_str:
                            parts = line_str.split("=", 1)
                            if len(parts) > 1:
                                media_name = parts[1].strip().replace('"', "")
                        elif "application.name =" in line_str or "application.process.binary =" in line_str:
                            parts = line_str.split("=", 1)
                            if len(parts) > 1:
                                app_bin = parts[1].strip().replace('"', "")
                    
                    if media_name and media_name != "Playback":
                        if "youtube" in media_name.lower() or "youtube" in app_bin.lower() or "chrome" in app_bin.lower():
                            resultado["audio_segundo_plano"] = media_name
                            resultado["audio_app"] = "🎥 YouTube"
                            break
                        elif "spotify" in app_bin.lower() or "spotify" in media_name.lower():
                            resultado["audio_segundo_plano"] = media_name
                            resultado["audio_app"] = "🎵 Spotify"
                            break
        except Exception:
            pass

    # --- 2. DETECCIÓN DE PESTAÑAS ABIERTAS EN TODOS LOS PERFILES DE CHROME ---
    try:
        import glob
        import re
        chrome_base = os.path.expanduser("~/.config/google-chrome")
        ahora_ts = time.time()
        patron = os.path.join(chrome_base, "**/Sessions/Session_*")
        archivos = glob.glob(patron, recursive=True)
        recientes = [f for f in archivos if (ahora_ts - os.path.getmtime(f)) < 14400]

        pestanas_dict = {}
        candidatos_audio = []

        for f in recientes:
            try:
                content = open(f, "rb").read()
                perfil = f.split("/")[-3]  # Default, Profile 1, Profile 2, etc.

                matches = re.findall(rb"(?:[\x20-\x7e]\x00){4,}", content)
                for m in matches:
                    try:
                        txt = m.decode("utf-16le", "ignore").strip()
                        if len(txt) < 3 or txt.startswith("http") or txt.startswith("data:"):
                            continue
                        lower = txt.lower()
                        cat = None
                        icono = "🌐"

                        if "youtube" in lower:
                            cat = "Música / Video"
                            icono = "🎥"
                        elif "spotify" in lower:
                            cat = "Música"
                            icono = "🎵"
                        elif "instagram" in lower:
                            cat = "Red Social"
                            icono = "📸"
                        elif "whatsapp" in lower:
                            cat = "Mensajería"
                            icono = "💬"
                        elif "clockify" in lower:
                            cat = "Gestión Tiempo"
                            icono = "⏱️"
                        elif "workadventure" in lower:
                            cat = "Oficina Virtual"
                            icono = "🏢"
                        elif "dian" in lower:
                            cat = "Operación Tributaria"
                            icono = "🏛️"
                        elif "corvi" in lower:
                            cat = "Gestión CORVI"
                            icono = "📊"
                        elif "asana" in lower or "trello" in lower:
                            cat = "Gestión Proyectos"
                            icono = "📋"

                        if cat:
                            clave = f"{icono} {txt}"
                            if clave not in pestanas_dict:
                                item_info = {
                                    "titulo": txt,
                                    "categoria": cat,
                                    "icono": icono,
                                    "perfil": perfil
                                }
                                pestanas_dict[clave] = item_info
                                if cat in ["Música / Video", "Música"]:
                                    candidatos_audio.append(item_info)
                    except Exception:
                        pass
            except Exception:
                pass

        resultado["pestanas_abiertas"] = list(pestanas_dict.values())

        # Si pactl no identificó el nombre específico del audio, buscar en las pestañas de música
        if not resultado["audio_segundo_plano"] and candidatos_audio:
            for ca in candidatos_audio:
                t = ca["titulo"]
                if not re.match(r"^(\(\d+\)\s*)?(YouTube|Spotify)$", t, re.I):
                    resultado["audio_segundo_plano"] = t
                    resultado["audio_app"] = "🎥 YouTube" if "youtube" in t.lower() else "🎵 Spotify"
                    break
            if not resultado["audio_segundo_plano"]:
                resultado["audio_segundo_plano"] = candidatos_audio[0]["titulo"]
                resultado["audio_app"] = "🎥 YouTube" if "youtube" in candidatos_audio[0]["titulo"].lower() else "🎵 Spotify"
    except Exception:
        pass

    # --- 3. DETECCIÓN DE VENTANAS DEL SISTEMA ABIERTAS (X11) ---
    if IS_LINUX:
        try:
            wmctrl_out = subprocess.check_output(["wmctrl", "-l"], stderr=subprocess.DEVNULL).decode("utf-8", "ignore")
            for line in wmctrl_out.splitlines():
                partes = line.split(None, 3)
                if len(partes) >= 4:
                    t = partes[3].strip()
                    if t and t not in resultado["ventanas_escritorio"]:
                        resultado["ventanas_escritorio"].append(t)
        except Exception:
            pass

    return resultado


def detectar_reunion_workadventure(im=None):
    """
    Detecta si en la pantalla actual existe el contenedor flotante de reunión activa
    (video/audio de participantes: 'Tú', 'Linda', etc.) de WorkAdventure.
    Devuelve (True/False, cantidad_coincidencias).
    """
    try:
        if im is None:
            im = ImageGrab.grab()
        
        w, h = im.size
        scale_x = w / 1920.0
        scale_y = h / 1080.0
        x_ini, x_fin = int(550 * scale_x), int(1450 * scale_x)
        y_ini, y_fin = int(160 * scale_y), int(400 * scale_y)

        count = 0
        step = 4
        for y in range(y_ini, y_fin, step):
            for x in range(x_ini, x_fin, step):
                r, g, b = im.getpixel((x, y))[:3]
                # Color del contenedor de participantes en WorkAdventure: (27, 44, 65)
                if abs(r - 27) <= 12 and abs(g - 44) <= 12 and abs(b - 65) <= 12:
                    count += 1
        
        # Umbral calibrado: en reunión supera 2500 con step=4; estando solo da < 50
        return (count >= 300, count)
    except Exception:
        return (False, 0)


def clasificar_actividad(app_name, title, is_idle, screen_img=None):
    plataforma, titulo_limpio, tipo, es_alerta, detalle = desglosar_actividad_web(app_name, title)
    plat_upper = plataforma.upper()

    # 1. Identificar plataformas dedicadas de llamada / videollamada
    es_plataforma_reunion = any(k in plat_upper for k in ["MEET", "TEAMS", "ZOOM", "SKYPE", "WEBEX"])
    es_workadventure = any(k in plat_upper for k in ["WORKADVENTURE", "OFICINA VIRTUAL"])

    # 2. Para WorkAdventure: verificar visualmente si está en reunión (burbuja / sala con compañeros)
    reunion_wa = False
    if es_workadventure:
        reunion_wa, _ = detectar_reunion_workadventure(screen_img)

    # 3. Audio activo como respaldo de voz/llamada en el sistema
    audio_activo = check_audio_active()

    # Determinar si el colaborador está en reunión activa
    esta_en_reunion = es_plataforma_reunion or reunion_wa or (es_workadventure and audio_activo)

    if esta_en_reunion:
        if es_workadventure:
            cat = "🏢 En Reunión en Oficina Virtual (WorkAdventure)"
            detalle = "Participando activamente en reunión de equipo en WorkAdventure (sala o burbuja de conversación con compañeros)."
        else:
            cat = f"📞 En Reunión / Videollamada ({plataforma})"
            detalle = f"Participación activa en llamada o reunión en {plataforma}."
        # REGLA DE ORO: En reunión NUNCA es ausencia ni alerta, aunque el equipo esté quieto sin mover ratón
        return (cat, plataforma, titulo_limpio, False, detalle, True)

    # Si NO está en reunión y el teclado/ratón está quieto (> 5 min):
    if is_idle:
        if es_workadventure:
            # Avatar solo en pasillo o escritorio sin compañeros ni audio
            return (
                "🚨 Standby en Oficina Virtual (Avatar Solo sin Reunión)",
                plataforma,
                titulo_limpio,
                True,
                "Inactividad prolongada > 5 min en WorkAdventure con avatar solo (sin interacción ni reunión activa).",
                False
            )
        else:
            # Inactividad en cualquier otra aplicación sin llamada
            return (
                "Ausencia del Equipo (AFK)",
                plataforma,
                titulo_limpio,
                True,
                f"Inactividad prolongada > 5 min sin digitación ni interacción — [{plataforma}] {titulo_limpio[:50]}",
                False
            )

    # Trabajo activo normal
    return (tipo, plataforma, titulo_limpio, es_alerta, detalle, False)

def enviar_notificacion(titulo, mensaje):
    if IS_LINUX:
        try:
            subprocess.Popen(["notify-send", "-a", "Control de Asistencia", "-i", "x-office-calendar", titulo, mensaje])
        except Exception:
            pass
    elif IS_WINDOWS:
        try:
            # En Windows usamos PowerShell 100% invisible con CREATE_NO_WINDOW y -WindowStyle Hidden
            # para garantizar 0% ventanas azules en pantalla
            ps_script = f'''
            [void] [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms");
            $obj = New-Object System.Windows.Forms.NotifyIcon;
            $obj.Icon = [System.Drawing.SystemIcons]::Information;
            $obj.BalloonTipTitle = "{titulo}";
            $obj.BalloonTipText = "{mensaje}";
            $obj.Visible = $True;
            $obj.ShowBalloonTip(3000);
            Start-Sleep -Seconds 3;
            $obj.Dispose();
            '''
            kwargs = {
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "stdin": subprocess.DEVNULL
            }
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            else:
                kwargs["creationflags"] = 0x08000000

            subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", ps_script],
                **kwargs
            )
        except Exception:
            pass

# =============================================================================
# MOTOR CENTRAL DE TELEMETRÍA Y CONTROL
# =============================================================================
HILO_ENVIO_CORREO = None

def enviar_reporte_diario_email(resumen, json_path, html_path):
    global HILO_ENVIO_CORREO

    def _enviar():
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            from email.mime.base import MIMEBase
            from email import encoders

            nombre = resumen.get("colaborador", CONFIG.get("colaborador_nombre", "Colaborador"))
            cargo = resumen.get("cargo", CONFIG.get("colaborador_cargo", "Cargo"))
            fecha = resumen.get("fecha", datetime.date.today().isoformat())
            inicio = resumen.get("hora_inicio", "--:--:--")
            fin = resumen.get("hora_fin", "--:--:--")

            tot_seg = resumen.get("segundos_totales", 0)
            efec_seg = resumen.get("segundos_efectivos", 0)
            afk_seg = resumen.get("segundos_inactivos", 0)
            reunion_seg = resumen.get("segundos_en_reunion", 0)

            def s_to_hms(s):
                h = s // 3600
                m = (s % 3600) // 60
                sec = s % 60
                return f"{h:02d}h {m:02d}m {sec:02d}s"

            pct_efec = round(efec_seg / tot_seg * 100, 1) if tot_seg else 0
            pct_afk = round(afk_seg / tot_seg * 100, 1) if tot_seg else 0

            # Cargar datos detallados del JSON de jornada si existe
            data_json = {}
            if json_path and os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f_j:
                        data_json = json.load(f_j)
                except Exception:
                    pass

            alertas = data_json.get("alertas", [])
            cortes = data_json.get("historial_cortes_internet", [])
            plataformas = data_json.get("distribucion_plataformas", data_json.get("distribucion_apps", {}))

            # -----------------------------------------------------------------
            # 1. CORREO FORENSE TÉCNICO (tecnologia@corviconsultores.com)
            # Asunto con horario único para que Gmail NUNCA los agrupe en un mismo hilo
            # -----------------------------------------------------------------
            import unicodedata
            h_ini = inicio.replace(":", "")[:4]
            h_fin = fin.replace(":", "")[:4]
            nombre_ascii = unicodedata.normalize('NFKD', nombre).encode('ASCII', 'ignore').decode('utf-8').replace(' ', '_')
            nombre_archivo_html = f"REPORTE_JORNADA_{fecha}_{nombre_ascii}_{h_ini}-{h_fin}.html"

            asunto_tec = f"📊 [TURNO {inicio[:5]} - {fin[:5]}] Auditoría: {nombre} ({cargo}) — {fecha}"
            cuerpo_tec = f"""REPORTE OFICIAL DE TELEMETRÍA Y JORNADA LABORAL
Firma: CORVI CONSULTORES S.A.S.
Fecha: {fecha}

• Colaborador: {nombre}
• Cargo: {cargo}
• Empresa: {CONFIG.get('colaborador_empresa', 'CORVI CONSULTORES S.A.S.')}
• Horario registrado: {inicio} a {fin}

RESUMEN DE EFICIENCIA:
--------------------------------------------------
• Tiempo Total de Turno:    {s_to_hms(tot_seg)}
• Tiempo Efectivo Laborado: {s_to_hms(efec_seg)} ({pct_efec}%)
• Tiempo en Reunión:        {s_to_hms(reunion_seg)}
• Inactividad / AFK:        {s_to_hms(afk_seg)} ({pct_afk}%)
• Disponibilidad Internet:  {resumen.get('disponibilidad_internet_pct', 100)}% ({len(cortes)} cortes)
• Total Capturas Pantalla:  {resumen.get('total_capturas', 0)} registros

Se adjunta el archivo interactivo oficial '{nombre_archivo_html}' con la galería de capturas de pantalla, desglose por software y métricas de red.
"""
            msg_tec = MIMEMultipart()
            msg_tec["From"] = "CORVI Control de Asistencia <linda.gutierrez@corviconsultores.com>"
            msg_tec["To"] = "tecnologia@corviconsultores.com"
            msg_tec["Subject"] = asunto_tec
            msg_tec["Content-Language"] = "es"
            msg_tec.attach(MIMEText(cuerpo_tec, "plain", "utf-8"))

            if html_path and os.path.exists(html_path):
                with open(html_path, "rb") as f_attach:
                    part = MIMEBase("text", "html", charset="utf-8")
                    part.set_payload(f_attach.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", "attachment", filename=nombre_archivo_html)
                msg_tec.attach(part)

            # -----------------------------------------------------------------
            # 2. RESUMEN EJECUTIVO DE DIRECCIÓN (r.davidmauriciop@gmail.com)
            # Cero archivos pesados. Resumen directo de errores, alertas y uso.
            # -----------------------------------------------------------------
            top_apps = sorted(plataformas.items(), key=lambda x: x[1], reverse=True)[:4]
            lineas_apps = []
            for app, seg in top_apps:
                lineas_apps.append(f"  • {app}: {s_to_hms(seg)}")
            top_apps_txt = "\n".join(lineas_apps) if lineas_apps else "  • Actividad estándar de oficina"

            lineas_novedades = []
            for a in alertas[-5:]:
                lineas_novedades.append(f"  • [{a.get('hora', '--')}] {a.get('tipo', 'Alerta')}: {a.get('detalle', '')}")
            if cortes:
                for c in cortes[-3:]:
                    lineas_novedades.append(f"  • Caída de Internet: {c.get('inicio')} a {c.get('fin')} (Duración: {c.get('duracion_str', 'N/A')})")

            hay_novedades = bool(lineas_novedades)
            if hay_novedades:
                novedades_txt = "\n".join(lineas_novedades)
                asunto_david = f"⚠️ [TURNO {inicio[:5]} - {fin[:5]}] {nombre} — {fecha} | {pct_efec}% Eficiencia ({len(lineas_novedades)} novedades)"
            else:
                novedades_txt = "  ✅ Jornada 100% impecable. Cero alertas de ocio, cero cortes de red y alta productividad."
                asunto_david = f"✅ [TURNO {inicio[:5]} - {fin[:5]}] {nombre} — {fecha} | {pct_efec}% Eficiencia (Sin novedades)"

            cuerpo_david = f"""RESUMEN EJECUTIVO DE JORNADA LABORAL — CORVI CONSULTORES
Colaborador: {nombre} ({cargo})
Fecha: {fecha} | Horario: {inicio} a {fin}

📊 BALANCE DE RENDIMIENTO:
--------------------------------------------------
• Tiempo Total de Turno:    {s_to_hms(tot_seg)}
• Tiempo Efectivo Laborado: {s_to_hms(efec_seg)} ({pct_efec}%)
• Tiempo en Reunión:        {s_to_hms(reunion_seg)}
• Pausas / Inactividad:     {s_to_hms(afk_seg)} ({pct_afk}%)
• Estabilidad de Internet:  {resumen.get('disponibilidad_internet_pct', 100)}% ({len(cortes)} cortes)

💻 PRINCIPALES HERRAMIENTAS Y APLICACIONES:
{top_apps_txt}

🚨 AUDITORÍA DE NOVEDADES, ERRORES Y ALERTAS:
{novedades_txt}

--------------------------------------------------
ℹ️ Nota: El archivo forense interactivo completo con galería de capturas de pantalla reposa en tecnologia@corviconsultores.com.
"""
            msg_david = MIMEText(cuerpo_david, "plain", "utf-8")
            msg_david["From"] = "CORVI Control de Asistencia <linda.gutierrez@corviconsultores.com>"
            msg_david["To"] = "r.davidmauriciop@gmail.com"
            msg_david["Subject"] = asunto_david

            # -----------------------------------------------------------------
            # 3. CONEXIÓN SMTP Y DESPACHO EXCLUSIVO (CERO CORREO AL COLABORADOR)
            # -----------------------------------------------------------------
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=25) as s:
                s.login("linda.gutierrez@corviconsultores.com", "saleehtsxyekoehc")
                # Despacho técnico forense a tecnología
                s.sendmail("linda.gutierrez@corviconsultores.com", ["tecnologia@corviconsultores.com"], msg_tec.as_string())
                print("[CONTROL DE ASISTENCIA] 📧 Auditoría forense completa despachada a tecnologia@corviconsultores.com")
                # Despacho resumen ejecutivo a David
                s.sendmail("linda.gutierrez@corviconsultores.com", ["r.davidmauriciop@gmail.com"], msg_david.as_string())
                print("[CONTROL DE ASISTENCIA] 📧 Resumen ejecutivo despachado a David (r.davidmauriciop@gmail.com)")

        except Exception as e:
            print(f"[CONTROL DE ASISTENCIA] ⚠️ Error despachando reportes por email: {e}")

    t = threading.Thread(target=_enviar, daemon=False)
    t.start()
    HILO_ENVIO_CORREO = t
    return t

class CorviAsistenciaEngine:
    def __init__(self):
        self.lock = threading.Lock()
        self.estado = "DETENIDO"
        self.fecha_hoy = datetime.date.today().isoformat()
        self.hora_inicio = None
        self.hora_pausa = None
        self.hora_fin = None
        
        self.segundos_totales = 0
        self.segundos_efectivos = 0
        self.segundos_inactivos_afk = 0
        self.segundos_en_reunion = 0
        self.segundos_musica_fondo = 0
        self.segundos_pausa = 0

        # Actividad concurrente en segundo plano (Música, Pestañas de otros perfiles, etc.)
        self.historial_musica_fondo = {}             # {titulo_cancion: segundos}
        self.pestanas_segundo_plano_vistas = {}      # {clave: info_dict}
        self.estado_segundo_plano_actual = {"audio": None, "app_audio": None, "total_pestanas": 0}

        # Conectividad a Internet
        self.segundos_con_internet = 0
        self.segundos_sin_internet = 0
        self.estado_internet = {"online": True, "latencia_ms": 0.0}
        self.corte_internet_inicio = None
        self.historial_cortes_internet = []

        # Distribuciones detalladas
        self.distribucion_apps = {}          # {app_name: segundos}
        self.distribucion_plataformas = {}     # {plataforma_label: segundos}
        self.distribucion_detallada = {}       # {"plataforma || titulo_exacto || cat": segundos}
        self.distribucion_categorias = {}     # {categoria: segundos}
        self.registro_ventanas = []
        self.alertas = []
        
        # Banderas de recordatorios automáticos (Almuerzo 12 PM, Fin 5 PM, Notificación cada hora)
        self.ultima_notif_hora_ts = time.time()
        self.notificado_almuerzo_hoy = False
        self.notificado_fin_jornada_hoy = False
        self.lista_capturas = []
        self.alertas = []

        self.ultima_captura_tiempo = 0
        self.ultimo_chequeo_tiempo = time.time()
        self.ventana_actual = {
            "app": "N/A",
            "plataforma": "Reposo",
            "title": "Inicie su jornada",
            "idle": False,
            "cat": "Reposo"
        }

        self._running = True
        self.worker_thread = threading.Thread(target=self._bucle_telemetria, daemon=True)
        self.worker_thread.start()

    def get_carpeta_dia(self):
        hoy = datetime.date.today().isoformat()
        carpeta = os.path.join(REGISTROS_DIR, hoy)
        os.makedirs(carpeta, exist_ok=True)
        os.makedirs(os.path.join(carpeta, "capturas"), exist_ok=True)
        return carpeta

    def iniciar(self):
        with self.lock:
            if self.estado == "ACTIVO":
                return {"status": "ok", "message": "Ya se encuentra en jornada activa."}
            
            ahora = datetime.datetime.now()
            if self.estado == "DETENIDO":
                self.hora_inicio = ahora.strftime("%H:%M:%S")
                self.fecha_hoy = datetime.date.today().isoformat()
                self.segundos_totales = 0
                self.segundos_efectivos = 0
                self.segundos_inactivos_afk = 0
                self.segundos_en_reunion = 0
                self.segundos_musica_fondo = 0
                self.segundos_pausa = 0
                self.historial_musica_fondo = {}
                self.pestanas_segundo_plano_vistas = {}
                self.estado_segundo_plano_actual = {"audio": None, "app_audio": None, "total_pestanas": 0}
                self.segundos_con_internet = 0
                self.segundos_sin_internet = 0
                self.corte_internet_inicio = None
                self.historial_cortes_internet = []
                self.distribucion_apps = {}
                self.distribucion_plataformas = {}
                self.distribucion_detallada = {}
                self.distribucion_categorias = {}
                self.registro_ventanas = []
                self.alertas = []
            elif self.estado == "PAUSADO":
                if self.hora_pausa:
                    duracion_pausa = (ahora - datetime.datetime.strptime(f"{self.fecha_hoy} {self.hora_pausa}", "%Y-%m-%d %H:%M:%S")).total_seconds()
                    self.segundos_pausa += int(duracion_pausa)
                self.hora_pausa = None

            self.estado = "ACTIVO"
            self.ultimo_chequeo_tiempo = time.time()
            self.ultima_captura_tiempo = time.time()

        enviar_notificacion("Control de Asistencia", "Control de asistencia activado.")
        threading.Thread(target=self.tomar_captura, args=("Inicio de Jornada",), daemon=True).start()
        return {"status": "ok", "message": "Jornada iniciada con éxito."}

    def pausar(self):
        with self.lock:
            if self.estado != "ACTIVO":
                return {"status": "error", "message": "No puede pausar si no está en jornada activa."}
            self.estado = "PAUSADO"
            self.hora_pausa = datetime.datetime.now().strftime("%H:%M:%S")
        enviar_notificacion("Control de Asistencia", "Jornada en pausa.")
        return {"status": "ok", "message": "Jornada pausada (almuerzo o tiempo personal)."}

    def finalizar(self):
        with self.lock:
            if self.estado == "DETENIDO":
                return {"status": "error", "message": "La jornada ya está finalizada."}
            self.estado = "DETENIDO"
            self.hora_fin = datetime.datetime.now().strftime("%H:%M:%S")
            if self.corte_internet_inicio:
                fin_dt = datetime.datetime.now()
                dur_seg = int((fin_dt - self.corte_internet_inicio).total_seconds())
                dur_str = f"{dur_seg // 60}m {dur_seg % 60}s" if dur_seg >= 60 else f"{dur_seg}s"
                self.historial_cortes_internet.append({
                    "inicio": self.corte_internet_inicio.strftime("%H:%M:%S"),
                    "fin": fin_dt.strftime("%H:%M:%S"),
                    "duracion_seg": dur_seg,
                    "duracion_str": dur_str
                })
                self.corte_internet_inicio = None

        ruta_reporte = self.generar_reporte_diario()
        json_reporte = os.path.join(self.get_carpeta_dia(), "REPORTE_JORNADA.json")
        enviar_reporte_diario_email(self.get_resumen_en_vivo(), json_reporte, ruta_reporte)
        enviar_notificacion("Control de Asistencia", "Jornada finalizada.")
        return {"status": "ok", "message": "Jornada finalizada.", "reporte_url": f"/reporte?dia={self.fecha_hoy}"}

    def tomar_captura(self, motivo="Periódica (5 min)"):
        carpeta_dia = self.get_carpeta_dia()
        timestamp_str = datetime.datetime.now().strftime("%H-%M-%S")
        filename = f"{timestamp_str}_{CONFIG['colaborador_nombre'].replace(' ', '_')}.webp"
        filepath = os.path.join(carpeta_dia, "capturas", filename)

        try:
            im = ImageGrab.grab()
            # Guardar en WebP comprimido (nitidez total en 1080p, ~45-75 KB)
            im.save(filepath, "WEBP", quality=75)
            file_size_kb = os.path.getsize(filepath) / 1024.0

            item = {
                "hora": datetime.datetime.now().strftime("%H:%M:%S"),
                "filename": filename,
                "motivo": motivo,
                "size_kb": round(file_size_kb, 1),
                "url": f"/captura_img?dia={self.fecha_hoy}&img={filename}"
            }
            with self.lock:
                self.lista_capturas.append(item)
            return item
        except Exception as e:
            print(f"[ERROR Captura]: {e}")
            return None

    def _bucle_telemetria(self):
        while self._running:
            intervalo = CONFIG.get("intervalo_telemetria_seg", 10)
            time.sleep(intervalo)

            if self.estado != "ACTIVO":
                self.ultimo_chequeo_tiempo = time.time()
                continue

            ahora_ts = time.time()

            # Recordatorios automáticos al colaborador (solo si están habilitadas)
            ahora_dt = datetime.datetime.now()
            notif_habilitadas = CONFIG.get("notificaciones_activas", True)
            
            # 1. Recordatorio de Almuerzo (12:00 PM a 1:00 PM)
            if notif_habilitadas and ahora_dt.hour == 12 and not self.notificado_almuerzo_hoy:
                enviar_notificacion(
                    "Control de Asistencia",
                    "Hora de almuerzo. Recuerde activar 'Pausa / Almuerzo' para su tiempo de descanso."
                )
                self.notificado_almuerzo_hoy = True
            
            # 2. Recordatorio de Fin de Jornada (5:00 PM a 6:00 PM)
            if notif_habilitadas and ahora_dt.hour == 17 and not self.notificado_fin_jornada_hoy:
                enviar_notificacion(
                    "Control de Asistencia",
                    "Fin de jornada. Si ya completó su horario laboral de hoy, recuerde pulsar 'Finalizar Turno'."
                )
                self.notificado_fin_jornada_hoy = True
            
            # 3. Notificación periódica cada 60 minutos de jornada activa
            if notif_habilitadas and (ahora_ts - self.ultima_notif_hora_ts >= 3600):
                enviar_notificacion(
                    "Control de Asistencia",
                    "Jornada laboral en curso."
                )
                self.ultima_notif_hora_ts = ahora_ts

            delta = max(0, int(ahora_ts - self.ultimo_chequeo_tiempo))
            self.ultimo_chequeo_tiempo = ahora_ts

            # Monitoreo de Red
            net_online, net_latency = check_internet_status()

            # Ventana y Periférico
            app_name, title = get_active_window_info()
            idle_sec = get_idle_seconds()
            umbral_afk = CONFIG.get("umbral_inactividad_afk_seg", 300)
            is_idle = idle_sec >= umbral_afk

            # Clasificación Granular con Detección de Reunión Activa (Meet / WorkAdventure con compañeros)
            cat, plataforma, titulo_limpio, es_alerta, detalle, es_reunion_efectiva = clasificar_actividad(app_name, title, is_idle)

            # Inspección Holística de Segundo Plano (Audio/Música, Pestañas Múltiples de todos los perfiles)
            bg_info = inspeccionar_actividad_segundo_plano()
            if bg_info.get("audio_segundo_plano"):
                audio_track = bg_info["audio_segundo_plano"]
                with self.lock:
                    self.segundos_musica_fondo += int(delta)
                    self.historial_musica_fondo[audio_track] = self.historial_musica_fondo.get(audio_track, 0) + int(delta)

            for p in bg_info.get("pestanas_abiertas", []):
                k_p = f"{p['icono']} {p['titulo']}"
                if k_p not in self.pestanas_segundo_plano_vistas:
                    self.pestanas_segundo_plano_vistas[k_p] = p

            self.estado_segundo_plano_actual = {
                "audio": bg_info.get("audio_segundo_plano"),
                "app_audio": bg_info.get("audio_app"),
                "total_pestanas": len(bg_info.get("pestanas_abiertas", [])),
                "pestanas_resumen": [p["titulo"] for p in bg_info.get("pestanas_abiertas", [])[:6]]
            }

            with self.lock:
                self.segundos_totales += int(delta)
                if es_reunion_efectiva:
                    # En reunión activa: es tiempo 100% productivo y efectivo (NO se computa como AFK)
                    self.segundos_efectivos += int(delta)
                    self.segundos_en_reunion += int(delta)
                elif is_idle:
                    # Únicamente se computa AFK cuando el colaborador está SOLO y el equipo quieto
                    self.segundos_inactivos_afk += int(delta)
                else:
                    self.segundos_efectivos += int(delta)

                # Internet
                self.estado_internet = {"online": net_online, "latencia_ms": net_latency}
                if net_online:
                    self.segundos_con_internet += int(delta)
                    if self.corte_internet_inicio:
                        fin_dt = datetime.datetime.now()
                        dur_seg = int((fin_dt - self.corte_internet_inicio).total_seconds())
                        dur_str = f"{dur_seg // 60}m {dur_seg % 60}s" if dur_seg >= 60 else f"{dur_seg}s"
                        self.historial_cortes_internet.append({
                            "inicio": self.corte_internet_inicio.strftime("%H:%M:%S"),
                            "fin": fin_dt.strftime("%H:%M:%S"),
                            "duracion_seg": dur_seg,
                            "duracion_str": dur_str
                        })
                        self.alertas.append({
                            "hora": fin_dt.strftime("%H:%M:%S"),
                            "tipo": "Restablecimiento de Red",
                            "detalle": f"Internet restablecido tras {dur_str} de corte."
                        })
                        self.corte_internet_inicio = None
                else:
                    self.segundos_sin_internet += int(delta)
                    if not self.corte_internet_inicio:
                        self.corte_internet_inicio = datetime.datetime.now()
                        self.alertas.append({
                            "hora": self.corte_internet_inicio.strftime("%H:%M:%S"),
                            "tipo": "Caída de Internet",
                            "detalle": "Desconexión de red detectada por el monitor."
                        })

                # Distribuciones
                self.distribucion_apps[app_name] = self.distribucion_apps.get(app_name, 0) + int(delta)
                self.distribucion_plataformas[plataforma] = self.distribucion_plataformas.get(plataforma, 0) + int(delta)
                self.distribucion_categorias[cat] = self.distribucion_categorias.get(cat, 0) + int(delta)

                # Distribución detallada por contexto exacto
                # Si el título vino truncado con "..." por el navegador/sistema, intentar resolver con inventario abierto
                if titulo_limpio.endswith("...") or titulo_limpio.endswith("…"):
                    prefijo = titulo_limpio.rstrip(".… ").strip()
                    if len(prefijo) >= 8:
                        for p in bg_info.get("pestanas_abiertas", []):
                            p_t = p.get("titulo", "")
                            if p_t.startswith(prefijo) and len(p_t) > len(titulo_limpio):
                                titulo_limpio = p_t
                                break

                clave_detalle = f"{plataforma} || {titulo_limpio} || {cat}"
                self.distribucion_detallada[clave_detalle] = self.distribucion_detallada.get(clave_detalle, 0) + int(delta)

                # Ventana en vivo
                self.ventana_actual = {
                    "app": app_name,
                    "plataforma": plataforma,
                    "title": titulo_limpio,
                    "idle": is_idle,
                    "idle_sec": int(idle_sec),
                    "cat": cat,
                    "es_reunion": es_reunion_efectiva,
                    "audio_fondo": bg_info.get("audio_segundo_plano"),
                    "app_audio": bg_info.get("audio_app"),
                    "total_pestanas_abiertas": len(bg_info.get("pestanas_abiertas", [])),
                    "internet": net_online,
                    "latencia": net_latency
                }

                evento = {
                    "hora": datetime.datetime.now().strftime("%H:%M:%S"),
                    "app": app_name,
                    "plataforma": plataforma,
                    "title": titulo_limpio[:120],
                    "cat": cat,
                    "idle": is_idle,
                    "net": net_online
                }
                self.registro_ventanas.append(evento)
                if len(self.registro_ventanas) > 500:
                    self.registro_ventanas.pop(0)

                if es_alerta:
                    alerta_item = {
                        "hora": evento["hora"],
                        "tipo": cat,
                        "detalle": detalle
                    }
                    if not self.alertas or self.alertas[-1]["detalle"] != alerta_item["detalle"]:
                        self.alertas.append(alerta_item)

            carpeta_dia = self.get_carpeta_dia()
            log_path = os.path.join(carpeta_dia, "telemetria.jsonl")
            try:
                with open(log_path, "a", encoding="utf-8") as f_log:
                    f_log.write(json.dumps(evento, ensure_ascii=False) + "\n")
            except Exception:
                pass

            # Chequeo de captura periódica (cada 5 minutos)
            intervalo_captura_seg = CONFIG.get("intervalo_captura_min", 5) * 60
            if (ahora_ts - self.ultima_captura_tiempo) >= intervalo_captura_seg:
                self.ultima_captura_tiempo = ahora_ts
                self.tomar_captura(f"Periódica ({CONFIG.get('intervalo_captura_min', 5)} min)")

    def get_resumen_en_vivo(self):
        with self.lock:
            tot_net = self.segundos_con_internet + self.segundos_sin_internet
            disponibilidad_net = round((self.segundos_con_internet / max(tot_net, 1)) * 100, 1) if tot_net > 0 else 100.0

            # Tiempo transcurrido en el tramo activo actual para cronómetro fluido segundo a segundo
            seg_efectivos_vivo = self.segundos_efectivos
            seg_totales_vivo = self.segundos_totales
            if self.estado == "ACTIVO" and hasattr(self, "ultimo_chequeo_tiempo") and self.ultimo_chequeo_tiempo:
                tramo_vivo = max(0, int(time.time() - self.ultimo_chequeo_tiempo))
                seg_efectivos_vivo += tramo_vivo
                seg_totales_vivo += tramo_vivo

            return {
                "estado": self.estado,
                "colaborador": CONFIG["colaborador_nombre"],
                "cargo": CONFIG["colaborador_cargo"],
                "fecha": self.fecha_hoy,
                "hora_inicio": self.hora_inicio or "--:--:--",
                "hora_fin": self.hora_fin or "--:--:--",
                "segundos_totales": seg_totales_vivo,
                "segundos_efectivos": seg_efectivos_vivo,
                "segundos_en_reunion": self.segundos_en_reunion,
                "segundos_musica_fondo": self.segundos_musica_fondo,
                "audio_fondo_actual": self.estado_segundo_plano_actual,
                "historial_musica": self.historial_musica_fondo,
                "total_pestanas_detectadas": len(self.pestanas_segundo_plano_vistas),
                "pestanas_segundo_plano": list(self.pestanas_segundo_plano_vistas.values()),
                "segundos_inactivos": self.segundos_inactivos_afk,
                "segundos_pausa": self.segundos_pausa,
                "segundos_con_internet": self.segundos_con_internet,
                "segundos_sin_internet": self.segundos_sin_internet,
                "disponibilidad_internet_pct": disponibilidad_net,
                "estado_internet": self.estado_internet,
                "total_cortes_internet": len(self.historial_cortes_internet),
                "historial_cortes_internet": self.historial_cortes_internet,
                "ventana_actual": self.ventana_actual,
                "total_capturas": len(self.lista_capturas),
                "total_alertas": len(self.alertas),
            "notificaciones_activas": CONFIG.get("notificaciones_activas", True),
                "ultimas_capturas": self.lista_capturas[-6:] if self.lista_capturas else []
            }

    def generar_reporte_diario(self):
        carpeta_dia = self.get_carpeta_dia()
        resumen = self.get_resumen_en_vivo()
        
        json_path = os.path.join(carpeta_dia, "REPORTE_JORNADA.json")
        with open(json_path, "w", encoding="utf-8") as f:
            data = {
                "resumen": resumen,
                "distribucion_apps": self.distribucion_apps,
                "distribucion_plataformas": self.distribucion_plataformas,
                "distribucion_detallada": self.distribucion_detallada,
                "distribucion_categorias": self.distribucion_categorias,
                "historial_cortes_internet": self.historial_cortes_internet,
                "alertas": self.alertas,
                "capturas": self.lista_capturas
            }
            json.dump(data, f, indent=4, ensure_ascii=False)

        def seg_to_str(s):
            h = s // 3600
            m = (s % 3600) // 60
            sec = s % 60
            return f"{h:02d}h {m:02d}m {sec:02d}s"

        tiempo_total_str = seg_to_str(resumen["segundos_totales"])
        tiempo_efectivo_str = seg_to_str(resumen["segundos_efectivos"])
        tiempo_reunion_str = seg_to_str(resumen.get("segundos_en_reunion", 0))
        tiempo_musica_str = seg_to_str(resumen.get("segundos_musica_fondo", 0))
        tiempo_afk_str = seg_to_str(resumen["segundos_inactivos"])
        tiempo_con_net_str = seg_to_str(resumen["segundos_con_internet"])
        tiempo_sin_net_str = seg_to_str(resumen["segundos_sin_internet"])

        eficiencia_pct = 0
        if resumen["segundos_totales"] > 0:
            eficiencia_pct = round((resumen["segundos_efectivos"] / resumen["segundos_totales"]) * 100, 1)

        disp_net_pct = resumen["disponibilidad_internet_pct"]
        net_color_card = "green" if disp_net_pct >= 95.0 else ("yellow" if disp_net_pct >= 80.0 else "red")

        # TABLA ULTRA-DETALLADA: EXACTAMENTE EN QUÉ ARCHIVO, PESTAÑA O CONTEXTO TRABAJÓ
        filas_detalladas = ""
        total_s = max(resumen["segundos_totales"], 1)
        sorted_det = sorted(self.distribucion_detallada.items(), key=lambda x: x[1], reverse=True)
        for clave, segs in sorted_det[:25]:
            partes = clave.split(" || ")
            plat = partes[0] if len(partes) > 0 else "General"
            contexto = partes[1] if len(partes) > 1 else plat
            categoria = partes[2] if len(partes) > 2 else "Operativa"

            # Resolución de nombres completos si vinieron con "..." del sistema o navegador
            if contexto.endswith("...") or contexto.endswith("…"):
                prefijo = contexto.rstrip(".… ").strip()
                if len(prefijo) >= 8:
                    for p in self.pestanas_segundo_plano_vistas.values():
                        p_t = p.get("titulo", "")
                        if p_t.startswith(prefijo) and len(p_t) > len(contexto):
                            contexto = p_t
                            break
                    if contexto.endswith("...") or contexto.endswith("…"):
                        for m_t in self.historial_musica_fondo.keys():
                            if m_t.startswith(prefijo) and len(m_t) > len(contexto):
                                contexto = m_t
                                break

            pct = round((segs / total_s) * 100, 1)
            es_oficina = "WORKADVENTURE" in plat.upper() or "OFICINA VIRTUAL" in plat.upper()
            es_ai = "ANTIGRAVITY" in plat.upper() or "COPILOTO" in plat.upper()

            tag_badge = ""
            if es_oficina:
                tag_badge = '<span style="background: #059669; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; margin-left: 6px;">OFICINA CORVI</span>'
            elif es_ai:
                tag_badge = '<span style="background: #4f46e5; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; margin-left: 6px;">COPILOTO AI</span>'
            elif "🚨" in plat:
                tag_badge = '<span style="background: #dc2626; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; margin-left: 6px;">NO AUTORIZADO</span>'

            # Escapar comillas dobles para tooltip HTML seguro
            contexto_safe = contexto.replace('"', '&quot;')

            filas_detalladas += f"""
            <tr style="{'background: #f0fdf4;' if es_oficina else ('background: #f5f3ff;' if es_ai else '')}">
                <td style="font-weight: 700; color: #160826; white-space: normal; word-break: break-word;">
                    {plat} {tag_badge}
                </td>
                <td style="color: #2d3748; word-break: break-word; overflow-wrap: break-word; white-space: normal; line-height: 1.45; font-size: 13.5px;" title="{contexto_safe}">
                    <strong>{contexto}</strong>
                </td>
                <td style="font-size: 12px; color: #718096; white-space: nowrap;">{categoria}</td>
                <td style="font-weight: 600; white-space: nowrap;">{seg_to_str(segs)}</td>
                <td style="width: 14%;">
                    <div style="background: #e9ecef; border-radius: 4px; overflow: hidden; height: 14px; width: 100%;">
                        <div style="background: {'#059669' if es_oficina else ('#4f46e5' if es_ai else ('#dc2626' if '🚨' in plat else '#9e0e47'))}; height: 100%; width: {min(pct, 100)}%;"></div>
                    </div>
                </td>
                <td style="text-align: right; font-weight: 700; color: #160826; white-space: nowrap;">{pct}%</td>
            </tr>
            """

        if not filas_detalladas:
            filas_detalladas = "<tr><td colspan='6' style='text-align: center; color: #718096; padding: 15px;'>Esperando actividad registrada en la jornada...</td></tr>"

        # TABLA DE APLICACIONES GLOBALES
        filas_apps = ""
        sorted_apps = sorted(self.distribucion_apps.items(), key=lambda x: x[1], reverse=True)
        for app, segs in sorted_apps[:8]:
            pct = round((segs / total_s) * 100, 1)
            filas_apps += f"""
            <tr>
                <td style="font-weight: 600; color: #160826;">{app}</td>
                <td>{seg_to_str(segs)}</td>
                <td>
                    <div style="background: #e9ecef; border-radius: 4px; overflow: hidden; height: 14px; width: 100%;">
                        <div style="background: #64748b; height: 100%; width: {min(pct, 100)}%;"></div>
                    </div>
                </td>
                <td style="text-align: right; font-weight: 600;">{pct}%</td>
            </tr>
            """

        # FILAS DE MÚSICA / AUDIO EN SEGUNDO PLANO
        filas_musica_html = ""
        if self.historial_musica_fondo:
            filas_musica_html = """<table>
            <thead><tr>
                <th style="width: 25%;">Servicio / App</th>
                <th style="width: 45%;">Pista / Video / Emisión Reproducida</th>
                <th style="width: 15%;">Tiempo Estimado</th>
                <th style="width: 15%;">Estado Operativo</th>
            </tr></thead><tbody>"""
            for track, segs in sorted(self.historial_musica_fondo.items(), key=lambda x: x[1], reverse=True):
                app_icon = "🎥 YouTube" if "youtube" in track.lower() else ("🎵 Spotify" if "spotify" in track.lower() else "🎵 Audio")
                filas_musica_html += f"""<tr>
                <td style="font-weight: 700; color: #160826;">{app_icon}</td>
                <td style="color: #2d3748;"><strong>{track}</strong></td>
                <td style="font-weight: 600;">{seg_to_str(segs)}</td>
                <td><span style="background: #e0f2fe; color: #0369a1; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600;">Música en Segundo Plano</span></td>
            </tr>"""
            filas_musica_html += "</tbody></table>"
        else:
            filas_musica_html = '<p style="font-size: 13px; color: #64748b; font-style: italic; padding: 8px 0;">No se registró reproducción de audio ni música en segundo plano.</p>'

        # FILAS DE PESTAÑAS Y SERVICIOS CONCURRENTES (TODOS LOS PERFILES)
        filas_pestanas_html = ""
        if self.pestanas_segundo_plano_vistas:
            filas_pestanas_html = """<table>
            <thead><tr>
                <th style="width: 25%;">Categoría</th>
                <th style="width: 50%;">Pestaña / Documento Detectado</th>
                <th style="width: 15%;">Perfil de Usuario</th>
                <th style="width: 10%;">Estado</th>
            </tr></thead><tbody>"""
            for k_p, p in self.pestanas_segundo_plano_vistas.items():
                cat = p.get('categoria', 'General')
                badge_color = "#059669" if cat in ["Oficina Virtual", "Gestión CORVI"] else ("#4f46e5" if cat in ["Gestión Tiempo", "Gestión Proyectos"] else ("#0284c7" if cat in ["Música / Video", "Música"] else "#dc2626"))
                filas_pestanas_html += f"""<tr>
                <td style="font-weight: 700; color: #160826;">{p.get('icono', '🌐')} {cat}</td>
                <td style="color: #2d3748;"><strong>{p.get('titulo', 'N/A')}</strong></td>
                <td style="color: #64748b; font-size: 12px;">{p.get('perfil', 'Default')}</td>
                <td><span style="background: {badge_color}15; color: {badge_color}; border: 1px solid {badge_color}30; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600;">Abierta</span></td>
            </tr>"""
            filas_pestanas_html += "</tbody></table>"
        else:
            filas_pestanas_html = '<p style="font-size: 13px; color: #64748b; font-style: italic; padding: 8px 0;">No se detectaron pestañas concurrentes adicionales.</p>'

        # CORTES DE INTERNET
        filas_cortes = ""
        if self.historial_cortes_internet:
            for corte in self.historial_cortes_internet:
                filas_cortes += f"""
                <tr style="background: #fff5f5;">
                    <td style="color: #c53030; font-weight: bold;">{corte['inicio']}</td>
                    <td style="color: #2b6cb0; font-weight: bold;">{corte['fin']}</td>
                    <td style="font-weight: 600; color: #742a2a;">{corte['duracion_str']}</td>
                    <td style="color: #4a5568;">Desconexión total de red registrada por telemetría TCP</td>
                </tr>
                """
        else:
            filas_cortes = """
            <tr>
                <td colspan="4" style="text-align: center; color: #15803d; background: #f0fdf4; padding: 16px; font-weight: 600;">
                    ✅ Conexión 100% ininterrumpida y estable. Cero caídas de Internet registradas durante el turno laboral.
                </td>
            </tr>
            """

        # ALERTAS
        filas_alertas = ""
        if self.alertas:
            for al in reversed(self.alertas[-20:]):
                filas_alertas += f"""
                <tr style="background: #fff5f5;">
                    <td style="color: #c53030; font-weight: bold; white-space: nowrap;">{al['hora']}</td>
                    <td style="color: #9b2c2c; font-weight: 600;">{al['tipo']}</td>
                    <td style="color: #4a5568;">{al['detalle']}</td>
                </tr>
                """
        else:
            filas_alertas = "<tr><td colspan='3' style='text-align: center; color: #2e7d32; padding: 15px;'>✅ Jornada limpia. No se registraron alertas operativas.</td></tr>"

        # GALERÍA CON IMÁGENES EMBEBIDAS EN BASE64 (100% PORTABLE Y OFFLINE)
        items_galeria = ""
        capturas_dir = os.path.join(REGISTROS_DIR, self.fecha_hoy, "capturas")
        for cap in reversed(self.lista_capturas):
            img_path = os.path.join(capturas_dir, cap["filename"])
            img_src = f"capturas/{cap['filename']}"
            if os.path.exists(img_path):
                try:
                    with open(img_path, "rb") as f_img:
                        b64_data = base64.b64encode(f_img.read()).decode("utf-8")
                        img_src = f"data:image/webp;base64,{b64_data}"
                except Exception:
                    pass

            items_galeria += f"""
            <div class="thumb-card" onclick="openModal('{img_src}', '{cap['hora']} — {cap['motivo']}')">
                <img src="{img_src}" alt="Captura {cap['hora']}" loading="lazy" />
                <div class="thumb-meta">
                    <span class="thumb-time">{cap['hora']}</span>
                    <span class="thumb-badge">{cap['motivo']}</span>
                </div>
            </div>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>CORVI Control de Asistencia — Reporte de Jornada {self.fecha_hoy}</title>
    <style>
        :root {{
            --burgundy-deep: #160826;
            --burgundy-vivid: #9e0e47;
            --burgundy-soft: #fbf5f7;
            --emerald: #059669;
            --indigo: #4f46e5;
            --gold: #d4af37;
            --text-dark: #2d3748;
            --card-bg: #ffffff;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f4f6f9;
            color: var(--text-dark);
            margin: 0;
            padding: 24px;
        }}
        .header-card {{
            background: linear-gradient(135deg, var(--burgundy-deep) 0%, var(--burgundy-vivid) 100%);
            color: #ffffff;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 25px rgba(22, 8, 38, 0.25);
            margin-bottom: 24px;
        }}
        .header-card h1 {{ margin: 0 0 6px 0; font-size: 26px; letter-spacing: -0.5px; }}
        .header-card p {{ margin: 0; opacity: 0.9; font-size: 15px; }}
        .grid-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .stat-card {{
            background: var(--card-bg);
            border-radius: 10px;
            padding: 18px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            border-top: 4px solid var(--burgundy-vivid);
        }}
        .stat-card.green {{ border-top-color: #2e7d32; }}
        .stat-card.purple {{ border-top-color: #7c3aed; }}
        .stat-card.cyan {{ border-top-color: #06b6d4; }}
        .stat-card.yellow {{ border-top-color: #f59e0b; }}
        .stat-card.blue {{ border-top-color: #2563eb; }}
        .stat-card.red {{ border-top-color: #dc2626; }}
        .stat-label {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: #718096; font-weight: 600; }}
        .stat-val {{ font-size: 22px; font-weight: 700; margin-top: 8px; color: var(--burgundy-deep); }}
        .stat-sub {{ font-size: 12px; color: #a0aec0; margin-top: 4px; }}
        
        .section-box {{
            background: var(--card-bg);
            border-radius: 10px;
            padding: 24px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            margin-bottom: 24px;
        }}
        .section-title {{
            font-size: 18px;
            font-weight: 700;
            color: var(--burgundy-deep);
            margin-top: 0;
            margin-bottom: 16px;
            border-bottom: 2px solid var(--burgundy-soft);
            padding-bottom: 8px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13.5px;
            table-layout: auto;
        }}
        th, td {{
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid #edf2f7;
            vertical-align: middle;
        }}
        th {{
            background: #f8fafc;
            color: #4a5568;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.5px;
        }}
        
        .gallery-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
            gap: 14px;
        }}
        .thumb-card {{
            background: #fff;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid #e2e8f0;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .thumb-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 8px 16px rgba(0,0,0,0.12);
            border-color: var(--burgundy-vivid);
        }}
        .thumb-card img {{
            width: 100%;
            height: 115px;
            object-fit: cover;
            display: block;
            background: #2d3748;
        }}
        .thumb-meta {{
            padding: 6px 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 11px;
        }}
        .thumb-time {{ font-weight: 700; color: var(--burgundy-deep); }}
        .thumb-badge {{ background: #edf2f7; color: #4a5568; padding: 2px 5px; border-radius: 4px; font-size: 10px; }}
        
        .modal {{
            display: none;
            position: fixed;
            z-index: 9999;
            left: 0; top: 0;
            width: 100%; height: 100%;
            background: rgba(10, 5, 20, 0.92);
            align-items: center;
            justify-content: center;
            flex-direction: column;
        }}
        .modal img {{
            max-width: 92%;
            max-height: 85%;
            border-radius: 8px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5);
            border: 1px solid rgba(255,255,255,0.2);
        }}
        .modal-caption {{
            color: #ffffff;
            margin-top: 14px;
            font-size: 16px;
            font-weight: 600;
        }}
        .modal-close {{
            position: absolute;
            top: 20px; right: 30px;
            color: #fff;
            font-size: 32px;
            cursor: pointer;
        }}
    </style>
</head>
<body>

    <div class="header-card">
        <h1>📊 CORVI CONSULTORES — Reporte de Jornada y Eficiencia Laboral</h1>
        <p><strong>Colaborador:</strong> {CONFIG['colaborador_nombre']} ({CONFIG['colaborador_cargo']}) &nbsp;|&nbsp; <strong>Fecha:</strong> {self.fecha_hoy} &nbsp;|&nbsp; <strong>Horario:</strong> {resumen['hora_inicio']} a {resumen['hora_fin']}</p>
    </div>

    <!-- TARJETAS PRINCIPALES DE EFICIENCIA -->
    <div class="grid-stats">
        <div class="stat-card blue">
            <div class="stat-label">Tiempo Total en Turno</div>
            <div class="stat-val">{tiempo_total_str}</div>
            <div class="stat-sub">Jornada registrada en sistema</div>
        </div>
        <div class="stat-card green">
            <div class="stat-label">Tiempo Productivo Efectivo</div>
            <div class="stat-val">{tiempo_efectivo_str}</div>
            <div class="stat-sub">Actividad en teclado/ratón y reuniones</div>
        </div>
        <div class="stat-card purple">
            <div class="stat-label">Reuniones de Equipo</div>
            <div class="stat-val">{tiempo_reunion_str}</div>
            <div class="stat-sub">WorkAdventure / Meet / Teams</div>
        </div>
        <div class="stat-card cyan">
            <div class="stat-label">Música en Segundo Plano</div>
            <div class="stat-val">{tiempo_musica_str}</div>
            <div class="stat-sub">YouTube / Spotify</div>
        </div>
        <div class="stat-card yellow">
            <div class="stat-label">Ausencia de Equipo (AFK)</div>
            <div class="stat-val">{tiempo_afk_str}</div>
            <div class="stat-sub">Inactividad &gt; 5 minutos</div>
        </div>
        <div class="stat-card {net_color_card}">
            <div class="stat-label">Disponibilidad de Internet</div>
            <div class="stat-val">{disp_net_pct}%</div>
            <div class="stat-sub">{tiempo_con_net_str} conectado | {resumen['total_cortes_internet']} caídas</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Índice de Eficiencia</div>
            <div class="stat-val">{eficiencia_pct}%</div>
            <div class="stat-sub">Productivo / Tiempo Total</div>
        </div>
    </div>

    <!-- SECCIÓN CLAVE: EXACTAMENTE EN QUÉ ARCHIVO O PESTAÑA TRABAJÓ -->
    <div class="section-box">
        <h2 class="section-title">
            <span>📋 Desglose Exacto de Trabajo — Documentos, Pestañas y Sistemas</span>
            <span style="font-size: 13px; font-weight: normal; color: #059669;">
                ✔ Reconocimiento de Archivos, WorkAdventure y Copiloto AI
            </span>
        </h2>
        <p style="font-size: 13px; color: #718096; margin-top: -8px; margin-bottom: 14px;">
            Muestra el nombre exacto de la pestaña de navegador, libro de Excel o archivo en el que estuvo interactuando el colaborador.
        </p>
        <table>
            <thead>
                <tr>
                    <th style="width: 22%;">Plataforma / Módulo</th>
                    <th style="width: 40%;">Documento / Pestaña / Contexto Exacto</th>
                    <th style="width: 14%;">Categoría</th>
                    <th style="width: 10%;">Tiempo</th>
                    <th style="width: 14%; text-align: right;" colspan="2">Proporción</th>
                </tr>
            </thead>
            <tbody>
                {filas_detalladas}
            </tbody>
        </table>
    </div>

    <!-- SECCIÓN CLAVE: ACTIVIDAD CONCURRENTE, MÚSICA Y PESTAÑAS MÚLTIPLES EN SEGUNDO PLANO -->
    <div class="section-box">
        <h2 class="section-title">
            <span>🎧 Actividad Concurrente — Pestañas Múltiples y Música en Segundo Plano</span>
            <span style="font-size: 13px; font-weight: normal; color: #4f46e5;">
                ✔ Visibilidad de Todo el Entorno (YouTube, Spotify, Redes y Pestañas Abiertas)
            </span>
        </h2>
        <p style="font-size: 13px; color: #718096; margin-top: -8px; margin-bottom: 14px;">
            Registro de aplicaciones activas y reproducción de audio/música en segundo plano mientras el colaborador opera. Permite saber si tiene música de fondo (acompañamiento sonoro) y qué otras plataformas mantiene activas simultáneamente en su navegador en todos los perfiles de usuario.
        </p>

        <!-- SUB-BLOQUE: MÚSICA / AUDIO DETECTADO -->
        <h3 style="font-size: 15px; color: #160826; margin: 18px 0 8px 0;">🎵 Reproducción de Música / Audio en Segundo Plano:</h3>
        {filas_musica_html}

        <!-- SUB-BLOQUE: INVENTARIO DE PESTAÑAS MÚLTIPLES ABIERTAS -->
        <h3 style="font-size: 15px; color: #160826; margin: 24px 0 8px 0;">🌐 Inventario de Pestañas y Servicios Abiertos Concurrentemente (Todos los Perfiles):</h3>
        {filas_pestanas_html}
    </div>

    <!-- REGISTRO DE CONECTIVIDAD A INTERNET -->
    <div class="section-box">
        <h2 class="section-title">
            <span>📡 Registro de Conectividad a Internet (Control Técnico de Cortes)</span>
            <span style="font-size: 13px; font-weight: normal; color: #718096;">
                Tiempo Sin Internet: <strong>{tiempo_sin_net_str}</strong>
            </span>
        </h2>
        <table>
            <thead>
                <tr>
                    <th style="width: 20%;">Inicio de Caída</th>
                    <th style="width: 20%;">Restablecimiento</th>
                    <th style="width: 20%;">Duración Exacta</th>
                    <th style="width: 40%;">Diagnóstico del Sistema</th>
                </tr>
            </thead>
            <tbody>
                {filas_cortes}
            </tbody>
        </table>
    </div>

    <!-- ALERTAS OPERATIVAS -->
    <div class="section-box">
        <h2 class="section-title">🚨 Registro de Alertas y Eventos Operativos</h2>
        <table>
            <thead>
                <tr>
                    <th style="width: 15%;">Hora</th>
                    <th style="width: 25%;">Clasificación</th>
                    <th style="width: 60%;">Detalle del Evento</th>
                </tr>
            </thead>
            <tbody>
                {filas_alertas}
            </tbody>
        </table>
    </div>

    <!-- GALERÍA DE CAPTURAS CADA 5 MINUTOS -->
    <div class="section-box">
        <h2 class="section-title">
            <span>📸 Registro Visual de Jornada — Muestreo Periódico (Cada 5 minutos)</span>
            <span style="font-size: 13px; font-weight: normal; color: #718096;">
                Total capturas del día: <strong>{len(self.lista_capturas)}</strong>
            </span>
        </h2>
        <p style="font-size: 13px; color: #718096; margin-top: -8px; margin-bottom: 16px;">
            Haga clic en cualquier imagen para abrirla en alta resolución y auditar visualmente los documentos abiertos.
        </p>
        <div class="gallery-grid">
            {items_galeria if items_galeria else "<p style='color: #718096;'>No se han tomado capturas aún en esta jornada.</p>"}
        </div>
    </div>

    <!-- Modal Lightbox -->
    <div id="modalBox" class="modal" onclick="closeModal()">
        <span class="modal-close">&times;</span>
        <img id="modalImg" src="" alt="Captura ampliada" />
        <div id="modalCaption" class="modal-caption"></div>
    </div>

    <script>
        function openModal(src, caption) {{
            document.getElementById('modalImg').src = src;
            document.getElementById('modalCaption').innerText = caption;
            document.getElementById('modalBox').style.display = 'flex';
        }}
        function closeModal() {{
            document.getElementById('modalBox').style.display = 'none';
        }}
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') closeModal();
        }});
    </script>
</body>
</html>
"""
        html_path = os.path.join(carpeta_dia, "REPORTE_JORNADA.html")
        with open(html_path, "w", encoding="utf-8") as f_html:
            f_html.write(html_content)

        return html_path

ENGINE = CorviAsistenciaEngine()

# =============================================================================
# SERVIDOR WEB LOCAL Y DASHBOARDS (ONBOARDING + CONTROL DIARIO)
# =============================================================================
ONBOARDING_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Configuración de Puesto Remoto — CORVI CONSULTORES</title>
    <style>
        :root {
            --burgundy-deep: #160826;
            --burgundy-vivid: #9e0e47;
            --emerald: #059669;
            --bg-light: #eceff4;
            --text-main: #1a202c;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        html, body {
            width: 100%;
            height: 100%;
            margin: 0;
            padding: 0;
            background: #ffffff;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: var(--text-main);
            overflow-x: hidden;
            overflow-y: auto;
        }
        .card {
            width: 100%;
            min-height: 100%;
            background: #ffffff;
            display: flex;
            flex-direction: column;
            border: none;
            border-radius: 0;
            box-shadow: none;
        }
        .header {
            background: linear-gradient(135deg, var(--burgundy-deep) 0%, var(--burgundy-vivid) 100%);
            color: #ffffff;
            padding: 20px 18px 16px 18px;
            text-align: center;
        }
        .header h1 { font-size: 16px; font-weight: 800; margin-bottom: 2px; letter-spacing: -0.2px; }
        .header p { font-size: 11.5px; opacity: 0.9; }
        .body {
            padding: 16px 18px;
            flex: 1;
        }
        .info-note {
            background: #f8fafc;
            border-left: 4px solid var(--burgundy-vivid);
            padding: 12px 14px;
            border-radius: 0 8px 8px 0;
            font-size: 12.5px;
            color: #475569;
            margin-bottom: 22px;
            line-height: 1.5;
        }
        .form-group {
            margin-bottom: 16px;
        }
        label {
            display: block;
            font-size: 13px;
            font-weight: 700;
            color: #334155;
            margin-bottom: 6px;
        }
        input, select {
            width: 100%;
            padding: 11px 14px;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            font-size: 14px;
            color: #1e293b;
            outline: none;
            transition: all 0.2s;
        }
        input:focus, select:focus {
            border-color: var(--burgundy-vivid);
            box-shadow: 0 0 0 3px rgba(158, 14, 71, 0.15);
        }
        .btn-submit {
            width: 100%;
            background: linear-gradient(135deg, var(--burgundy-deep) 0%, var(--burgundy-vivid) 100%);
            color: #ffffff;
            border: none;
            padding: 13px;
            border-radius: 8px;
            font-size: 14.5px;
            font-weight: 700;
            cursor: pointer;
            margin-top: 8px;
            transition: transform 0.1s, opacity 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        .btn-submit:hover { opacity: 0.95; transform: translateY(-1px); }
        .btn-submit:active { transform: translateY(0); }
        .footer-note {
            text-align: center;
            font-size: 11px;
            color: #94a3b8;
            margin-top: 18px;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <div style="font-size: 11px; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase; color: #f9a8d4; margin-bottom: 4px;">CORVI CONSULTORES S.A.S.</div>
            <h1>Configuración de Puesto Remoto</h1>
            <p>CORVI Control de Asistencia — Activación Inicial</p>
        </div>
        <div class="body">
            <div class="info-note">
                <strong>📌 Registro único de este equipo:</strong> Ingrese sus datos para vincular este computador a su jornada laboral en CORVI. Esta configuración solo se realiza una sola vez.
            </div>
            <form id="onboardingForm" onsubmit="guardarRegistro(event)">
                <div class="form-group">
                    <label for="empresa">Empresa / Razón Social *</label>
                    <input type="text" id="empresa" name="empresa" value="CORVI CONSULTORES S.A.S." placeholder="Ej. CORVI CONSULTORES / Empresa Cliente" required>
                </div>
                <div class="form-group">
                    <label for="nombre">Nombre Completo del Colaborador *</label>
                    <input type="text" id="nombre" name="nombre" placeholder="Ej. __COLABORADOR_NOMBRE__" required autofocus>
                </div>
                <div class="form-group">
                    <label for="cedula">Cédula de Ciudadanía *</label>
                    <input type="text" id="cedula" name="cedula" placeholder="Ej. 1.020.345.678" required>
                </div>
                <div class="form-group">
                    <label for="cargo">Cargo Asignado * <span style="font-size: 11px; font-weight: normal; color: #64748b;">(Escriba libremente o seleccione de la lista)</span></label>
                    <input type="text" id="cargo" name="cargo" list="lista-cargos" placeholder="Escriba su cargo (ej. Auxiliar Contable, Jefe de Bodega, Comercial...)" required autocomplete="off">
                    <datalist id="lista-cargos">
                        <!-- Finanzas, Contabilidad & Tributaria -->
                        <option value="Auxiliar Contable y Tributario">
                        <option value="Analista Contable Sénior">
                        <option value="Contador General">
                        <option value="Asistente de Control Operativo">
                        <option value="Revisor Fiscal">
                        <option value="Tesorero / Auxiliar de Tesorería">
                        <option value="Jefe de Cartera y Cobranzas">
                        <option value="Auxiliar de Facturación Electrónica">
                        <!-- Operaciones, Logística & Bodega -->
                        <option value="Líder de Operaciones">
                        <option value="Jefe de Bodega e Inventarios (WMS)">
                        <option value="Coordinador de Logística y Despachos">
                        <option value="Auxiliar de Bodega">
                        <option value="Jefe de Compras y Suministros">
                        <!-- Ventas & Comercial -->
                        <option value="Director Comercial B2B">
                        <option value="Ejecutivo de Cuentas / Comercial">
                        <option value="Asesor de Ventas">
                        <option value="Coordinador de Mercadeo / Marketing">
                        <!-- Administrativo & Gerencial -->
                        <option value="Gerente General / Representante Legal">
                        <option value="Gerente de Operaciones">
                        <option value="Asistente de Gerencia / Administrativo">
                        <option value="Coordinador de Talento Humano / Nómina">
                        <!-- Tecnología & Soporte -->
                        <option value="Desarrollador de Software / Programador">
                        <option value="Especialista TI / Soporte Técnico">
                        <option value="Analista de Procesos">
                    </datalist>
                </div>
                <div class="form-group">
                    <label for="correo">Correo Electrónico de Contacto *</label>
                    <input type="email" id="correo" name="correo" placeholder="ejemplo@corviconsultores.com" required>
                </div>
                <button type="submit" id="btnGuardar" class="btn-submit">
                    💾 Guardar y Vincular Puesto de Trabajo &rarr;
                </button>
            </form>
            <div class="footer-note">
                Seguridad & Telemetría Corporativa • Ley 1581 de 2012 • CORVI CONSULTORES
            </div>
        </div>
    </div>
    <script>
        async function guardarRegistro(e) {
            e.preventDefault();
            const btn = document.getElementById('btnGuardar');
            btn.disabled = true;
            btn.innerText = '⏳ Guardando y vinculando...';

            const payload = {
                empresa: document.getElementById('empresa').value.trim() || 'CORVI CONSULTORES S.A.S.',
                nombre: document.getElementById('nombre').value.trim(),
                cedula: document.getElementById('cedula').value.trim(),
                cargo: document.getElementById('cargo').value.trim(),
                correo: document.getElementById('correo').value.trim()
            };

            try {
                const res = await fetch('/api/registrar_colaborador', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.status === 'ok') {
                    window.location.reload();
                } else {
                    alert('Error al registrar: ' + (data.message || 'Intente nuevamente.'));
                    btn.disabled = false;
                    btn.innerText = '💾 Guardar y Vincular Puesto de Trabajo →';
                }
            } catch (err) {
                alert('Error de conexión: ' + err);
                btn.disabled = false;
                btn.innerText = '💾 Guardar y Vincular Puesto de Trabajo →';
            }
        }
    </script>
</body>
</html>
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CORVI Control de Asistencia</title>
    <style>
        :root {
            --burgundy-deep: #160826;
            --burgundy-vivid: #9e0e47;
            --emerald: #059669;
            --emerald-glow: #10b981;
            --gold: #d4af37;
            --bg-light: #f8fafc;
            --text-main: #0f172a;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        html, body {
            width: 100%;
            height: 100%;
            margin: 0;
            padding: 0;
            background: #ffffff;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            color: var(--text-main);
            overflow: hidden;
            user-select: none;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .app-window {
            width: 100%;
            max-width: 430px;
            height: 100%;
            max-height: 440px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            background: #ffffff;
            margin: 0 auto;
        }
        .header {
            background: linear-gradient(135deg, var(--burgundy-deep) 0%, var(--burgundy-vivid) 100%);
            color: #ffffff;
            padding: 16px 20px 14px 20px;
            text-align: center;
            border-bottom: 2px solid rgba(212, 175, 55, 0.4);
            flex-shrink: 0;
        }
        .header h1 {
            font-size: 15px;
            font-weight: 800;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            margin-bottom: 2px;
        }
        .header p {
            font-size: 11px;
            opacity: 0.85;
            margin-bottom: 8px;
        }
        .header-meta {
            display: flex;
            justify-content: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        .user-tag {
            background: rgba(255, 255, 255, 0.16);
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }
        .net-tag {
            background: #15803d;
            color: #ffffff;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 700;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }
        .net-tag.offline {
            background: #dc2626;
            animation: pulse 1.5s infinite;
        }
        
        .status-bar {
            background: #f8fafc;
            padding: 12px 20px;
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-shrink: 0;
        }
        .badge {
            font-size: 11.5px;
            font-weight: 700;
            padding: 5px 12px;
            border-radius: 20px;
            text-transform: uppercase;
            letter-spacing: 0.4px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .badge.detenido { background: #e2e8f0; color: #475569; }
        .badge.activo { background: #dcfce7; color: #166534; animation: pulse 2s infinite; }
        .badge.pausado { background: #fef3c7; color: #92400e; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.7; } 100% { opacity: 1; } }

        .time-display {
            text-align: right;
            font-size: 11px;
            color: #64748b;
        }
        .time-display span {
            display: block;
            text-transform: uppercase;
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 0.3px;
        }
        .time-display strong {
            display: block;
            font-size: 22px;
            font-weight: 800;
            color: var(--burgundy-deep);
            font-variant-numeric: tabular-nums;
            line-height: 1.1;
        }

        .main-body {
            padding: 16px 20px;
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 12px;
        }
        .controls-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .btn {
            border: none;
            padding: 13px 16px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 700;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: all 0.15s ease;
        }
        .btn:hover { transform: translateY(-1px); box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        .btn:active { transform: translateY(0); }
        .btn-start {
            background: linear-gradient(135deg, #059669 0%, #10b981 100%);
            color: #ffffff;
            grid-column: span 2;
            font-size: 15px;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
        }
        .btn-pause { background: #d97706; color: #ffffff; }
        .btn-stop { background: #dc2626; color: #ffffff; }

        .btn-silencio {
            width: 100%;
            background: #f1f5f9;
            color: #334155;
            border: 1px solid #cbd5e1;
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }
        .btn-silencio:hover {
            background: #e2e8f0;
            color: #0f172a;
            border-color: #94a3b8;
        }

        .btn-notif-toggle {
            background: transparent;
            border: 1px dashed #94a3b8;
            color: #64748b;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 11px;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .btn-notif-toggle:hover {
            border-color: var(--burgundy-vivid);
            color: var(--burgundy-vivid);
            background: #fff1f2;
        }

        .footer-bar {
            padding: 10px 16px;
            background: #0f172a;
            color: #94a3b8;
            text-align: center;
            font-size: 10px;
            letter-spacing: 0.3px;
            flex-shrink: 0;
        }
    </style>
</head>
<body>

    <div class="app-window">
        <div class="header">
            <h1>CORVI CONTROL DE ASISTENCIA</h1>
            <p>Registro de Jornada Laboral y Horario Remoto</p>
            <div class="header-meta">
                <div class="user-tag" id="userTag">__COLABORADOR_Y_CARGO__</div>
                <div class="net-tag" id="netTag">🌐 INTERNET CONECTADO</div>
            </div>
        </div>

        <div class="status-bar">
            <div>
                <span id="badgeEstado" class="badge detenido">⚪ DETENIDO</span>
            </div>
            <div class="time-display">
                <span>Tiempo Laborado</span>
                <strong id="cronometro">00:00:00</strong>
            </div>
        </div>

        <div class="main-body">
            <div class="controls-grid">
                <button id="btnStart" class="btn btn-start" onclick="enviarAccion('iniciar')">
                    ▶ INICIAR JORNADA
                </button>
                <button id="btnPause" class="btn btn-pause" onclick="enviarAccion('pausar')">
                    ⏸ PAUSA / ALMUERZO
                </button>
                <button id="btnStop" class="btn btn-stop" onclick="enviarAccion('finalizar')">
                    ⏹ FINALIZAR TURNO
                </button>
            </div>

            <button id="btnSilencio" class="btn-silencio" onclick="trabajarEnSilencio()" title="Cierra esta ventana para que no estorbe en Alt+Tab mientras el control de asistencia sigue activo en segundo plano">
                👁️ TRABAJAR EN SEGUNDO PLANO (CERRAR VENTANA)
            </button>

            <div style="text-align: center; margin-top: 4px;">
                <button id="btnNotifToggle" class="btn-notif-toggle" onclick="toggleNotificaciones()" title="Activar o silenciar los recordatorios automáticos de escritorio">
                    🔔 Recordatorios: ACTIVADOS (Clic para silenciar)
                </button>
            </div>
        </div>

        <div class="footer-bar">
            CORVI CONSULTORES S.A.S. • Control de Jornada Laboral Remota
        </div>
    </div>

    <script>
                let estadoActual = 'DETENIDO';
        let segundosBase = 0;
        let marcaTiempoSync = Date.now();

        function segToHMS(s) {
            const secNum = Math.max(0, Math.floor(s));
            const h = Math.floor(secNum / 3600).toString().padStart(2, '0');
            const m = Math.floor((secNum % 3600) / 60).toString().padStart(2, '0');
            const sec = (secNum % 60).toString().padStart(2, '0');
            return `${h}:${m}:${sec}`;
        }

        // Cronómetro matemático continuo: calcula segundos exactos transcurridos en tiempo real
        // Garantiza avance fluido segundo a segundo (43, 44, 45...) con 0.0% CPU y cero saltos de 10s
        function refrescarCronometroVisual() {
            let mostrar = segundosBase;
            if (estadoActual === 'ACTIVO') {
                const deltaSeg = Math.floor((Date.now() - marcaTiempoSync) / 1000);
                mostrar = segundosBase + Math.max(0, deltaSeg);
            }
            const el = document.getElementById('cronometro');
            if (el) el.innerText = segToHMS(mostrar);
        }

        // Ticking continuo cada 250ms para sincronización visual perfecta
        setInterval(refrescarCronometroVisual, 250);

        async function actualizarEstado() {
            try {
                const res = await fetch('/api/estado');
                const data = await res.json();
                
                document.getElementById('userTag').innerText = `${data.colaborador} — ${data.cargo}`;
                
                const netTag = document.getElementById('netTag');
                if (data.estado_internet && data.estado_internet.online) {
                    netTag.className = 'net-tag';
                    netTag.innerHTML = `🌐 INTERNET ACTIVO (${data.estado_internet.latencia_ms} ms)`;
                } else {
                    netTag.className = 'net-tag offline';
                    netTag.innerHTML = `❌ SIN CONEXIÓN A INTERNET`;
                }

                const badge = document.getElementById('badgeEstado');
                const btnStart = document.getElementById('btnStart');
                const btnPause = document.getElementById('btnPause');
                const btnStop = document.getElementById('btnStop');

                estadoActual = data.estado;
                segundosBase = data.segundos_efectivos;
                marcaTiempoSync = Date.now();
                refrescarCronometroVisual();

                if (data.estado === 'ACTIVO') {
                    badge.className = 'badge activo';
                    badge.innerHTML = '🟢 EN JORNADA ACTIVA';
                    btnStart.style.display = 'none';
                    btnPause.style.display = 'flex';
                    btnStop.style.display = 'flex';
                } else if (data.estado === 'PAUSADO') {
                    badge.className = 'badge pausado';
                    badge.innerHTML = '🟡 EN PAUSA / TIEMPO PERSONAL';
                    btnStart.style.display = 'flex';
                    btnStart.innerHTML = '▶ REANUDAR JORNADA';
                    btnPause.style.display = 'none';
                    btnStop.style.display = 'flex';
                } else {
                    badge.className = 'badge detenido';
                    badge.innerHTML = '⚪ JORNADA DETENIDA';
                    btnStart.style.display = 'flex';
                    btnStart.innerHTML = '▶ INICIAR JORNADA';
                    btnPause.style.display = 'none';
                    btnStop.style.display = 'none';
                }

                if (data.notificaciones_activas !== undefined) {
                    actualizarBotonNotif(data.notificaciones_activas);
                }
            } catch (err) {
                console.error('Error al sincronizar estado:', err);
            }
        }

        async function toggleNotificaciones() {
            try {
                const res = await fetch('/api/toggle_notificaciones', { method: 'POST' });
                const data = await res.json();
                actualizarBotonNotif(data.notificaciones_activas);
            } catch (err) {
                alert('Error al cambiar notificaciones: ' + err);
            }
        }

        function actualizarBotonNotif(activas) {
            const btn = document.getElementById('btnNotifToggle');
            if (activas) {
                btn.innerHTML = '🔔 Recordatorios: ACTIVADOS (Clic para silenciar)';
                btn.style.color = '#059669';
                btn.style.borderColor = '#10b981';
            } else {
                btn.innerHTML = '🔕 Recordatorios: SILENCIADOS (Clic para activar)';
                btn.style.color = '#94a3b8';
                btn.style.borderColor = '#cbd5e1';
            }
        }

        function trabajarEnSilencio() {
            window.close();
            setTimeout(function() {
                alert("Control de asistencia activo en segundo plano. Puede cerrar esta ventana para liberar su pantalla.");
            }, 300);
        }

        async function enviarAccion(accion) {
            if (accion === 'finalizar') {
                if (!confirm("¿Desea finalizar su jornada de trabajo de hoy?\\n\\nAl finalizar, su horario quedará registrado formalmente.")) {
                    return;
                }
            }
            try {
                let res = await fetch(`/api/${accion}`, { method: 'POST' });
                if (!res.ok) {
                    await new Promise(r => setTimeout(r, 600));
                    res = await fetch(`/api/${accion}`, { method: 'POST' });
                }
                const data = await res.json();
                if (accion === 'finalizar') {
                    estadoActual = 'DETENIDO';
                    const badge = document.getElementById('badgeEstado');
                    badge.className = 'badge detenido';
                    badge.innerHTML = '⚪ JORNADA FINALIZADA';
                    const grid = document.querySelector('.controls-grid');
                    grid.innerHTML = '<div style="grid-column: span 2; padding: 20px; background: #ecfdf5; border: 1px solid #10b981; border-radius: 12px; color: #065f46; font-size: 14px; font-weight: 600; text-align: center; line-height: 1.5;">✅ Turno laboral finalizado con éxito.<br><span style="font-size: 12px; font-weight: 400; color: #047857;">Sus horas trabajadas han sido registradas formalmente. Puede cerrar esta ventana con total tranquilidad.</span></div>';
                    const btnSilencio = document.getElementById('btnSilencio');
                    if (btnSilencio) btnSilencio.style.display = 'none';
                    return;
                }
                actualizarEstado();
            } catch (err) {
                console.warn('Reintento de conexión:', err);
                try {
                    await new Promise(r => setTimeout(r, 800));
                    const retryRes = await fetch(`/api/${accion}`, { method: 'POST' });
                    if (retryRes.ok) {
                        actualizarEstado();
                        return;
                    }
                } catch (retryErr) {}
                alert('El servicio de Control de Asistencia se está conectando en segundo plano. Por favor pulse nuevamente en unos segundos.');
            }
        }

        setInterval(actualizarEstado, 2000);
        actualizarEstado();

        // Asegurar ventana compacta y elegante al cargar
        window.addEventListener('load', function() {
            try {
                if (window.outerWidth > 450 || window.outerHeight > 480) {
                    window.resizeTo(430, 440);
                }
            } catch(e) {}
        });
    </script>
</body>
</html>
"""

class CorviHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            if not CONFIG.get("registrado", False) or not CONFIG.get("colaborador_nombre"):
                self.wfile.write(ONBOARDING_HTML.encode("utf-8"))
            else:
                colab = CONFIG.get("colaborador_nombre", "David Rodriguez")
                cargo = CONFIG.get("colaborador_cargo", "Director Comercial B2B")
                rendered = DASHBOARD_HTML.replace("__COLABORADOR_Y_CARGO__", f"{colab} — {cargo}")
                rendered = rendered.replace("__COLABORADOR_NOMBRE__", colab)
                self.wfile.write(rendered.encode("utf-8"))

        elif path == "/api/estado":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resumen = ENGINE.get_resumen_en_vivo()
            self.wfile.write(json.dumps(resumen).encode("utf-8"))

        elif path == "/api/version":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            est = ENGINE.estado if 'ENGINE' in globals() and ENGINE else "DETENIDO"
            self.wfile.write(json.dumps({"version": VERSION_LOCAL, "estado": est}).encode("utf-8"))

        elif path == "/api/cerrar_servidor":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok","message":"Cerrando instancia previa para actualizar..."}')
            def _terminar():
                time.sleep(0.4)
                os._exit(0)
            threading.Thread(target=_terminar, daemon=True).start()

        elif path == "/reporte":
            admin_token = params.get("auth", [""])[0]
            if admin_token != "corvi_admin" and not CONFIG.get("permitir_reporte_local", False):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write("""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <title>CORVI Control de Asistencia</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #eceff4; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .card { background: #ffffff; padding: 32px; border-radius: 12px; box-shadow: 0 10px 25px rgba(22, 8, 38, 0.08); text-align: center; max-width: 440px; border: 1px solid #e2e8f0; }
        h2 { color: #160826; font-size: 18px; margin-bottom: 12px; }
        p { color: #64748b; font-size: 13px; line-height: 1.6; }
    </style>
</head>
<body>
    <div class="card">
        <h2>CORVI Control de Asistencia</h2>
        <p>El reporte de jornada laboral interactivo ha sido consolidado y despachado de forma segura a los registros oficiales de la firma.</p>
    </div>
</body>
</html>""".encode("utf-8"))
                return

            dia = params.get("dia", [ENGINE.fecha_hoy])[0]
            reporte_file = os.path.join(REGISTROS_DIR, dia, "REPORTE_JORNADA.html")
            if not os.path.exists(reporte_file):
                ENGINE.generar_reporte_diario()

            if os.path.exists(reporte_file):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                with open(reporte_file, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "Reporte no encontrado")

        elif path == "/captura_img" or path.startswith("/capturas/"):
            if path == "/captura_img":
                dia = params.get("dia", [ENGINE.fecha_hoy])[0]
                img_name = params.get("img", [""])[0]
                img_path = os.path.join(REGISTROS_DIR, dia, "capturas", os.path.basename(img_name))
            else:
                img_name = os.path.basename(path)
                img_path = os.path.join(REGISTROS_DIR, ENGINE.fecha_hoy, "capturas", img_name)

            if os.path.exists(img_path):
                self.send_response(200)
                self.send_header("Content-Type", "image/webp")
                self.end_headers()
                with open(img_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "Imagen no encontrada")

        else:
            self.send_error(404, "Ruta no encontrada")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/registrar_colaborador":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                empresa = data.get("empresa", "CORVI CONSULTORES S.A.S.").strip() or "CORVI CONSULTORES S.A.S."
                nombre = data.get("nombre", "").strip()
                cedula = data.get("cedula", "").strip()
                cargo = data.get("cargo", "").strip()
                correo = data.get("correo", "").strip()

                if not nombre:
                    self._send_json({"status": "error", "message": "El nombre es obligatorio"})
                    return

                CONFIG["colaborador_empresa"] = empresa
                CONFIG["colaborador_nombre"] = nombre
                CONFIG["colaborador_cedula"] = cedula
                CONFIG["colaborador_cargo"] = cargo
                CONFIG["colaborador_correo"] = correo
                CONFIG["registrado"] = True
                guardar_config(CONFIG)

                # Notificar a David por correo en segundo plano
                notificar_registro_colaborador(nombre, cedula, cargo, correo, empresa)

                print(f"[CONTROL DE ASISTENCIA] ✅ Puesto de trabajo vinculado con éxito a: {nombre} ({cargo}) - CC {cedula}")
                self._send_json({"status": "ok"})
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)})

        elif path == "/api/toggle_notificaciones":
            actual = CONFIG.get("notificaciones_activas", True)
            CONFIG["notificaciones_activas"] = not actual
            guardar_config(CONFIG)
            self._send_json({"status": "ok", "notificaciones_activas": CONFIG["notificaciones_activas"]})
        elif path == "/api/reenviar_reporte":
            dia = params.get("dia", [ENGINE.fecha_hoy])[0]
            carpeta = os.path.join(REGISTROS_DIR, dia)
            html_path = os.path.join(carpeta, "REPORTE_JORNADA.html")
            json_path = os.path.join(carpeta, "REPORTE_JORNADA.json")
            if os.path.exists(html_path) and os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f_j:
                        resumen = json.load(f_j)
                    enviar_reporte_diario_email(resumen, json_path, html_path)
                    self._send_json({"status": "ok", "message": f"Reporte del {dia} despachado exitosamente a tecnologia@corviconsultores.com y r.davidmauriciop@gmail.com"})
                except Exception as e:
                    self._send_json({"status": "error", "message": str(e)})
            else:
                self._send_json({"status": "error", "message": f"No se encontró reporte generado para el día {dia}."})

        elif path == "/api/iniciar":
            res = ENGINE.iniciar()
            self._send_json(res)
        elif path == "/api/pausar":
            res = ENGINE.pausar()
            self._send_json(res)
        elif path == "/api/finalizar":
            res = ENGINE.finalizar()
            self._send_json(res)

            # Cierre limpio del proceso tras finalizar la jornada (Lanzador silencioso Windows o turnos individuales)
            if IS_WINDOWS or CONFIG.get("cerrar_al_finalizar", True):
                def _apagar_proceso():
                    import time
                    global HILO_ENVIO_CORREO
                    if HILO_ENVIO_CORREO and HILO_ENVIO_CORREO.is_alive():
                        print("[CONTROL DE ASISTENCIA] ⏳ Asegurando entrega completa del reporte por correo antes de apagar...")
                        HILO_ENVIO_CORREO.join(timeout=30)
                    time.sleep(2.0)
                    print("[CONTROL DE ASISTENCIA] Finalización de turno completada con éxito. Proceso cerrado limpiamente.")
                    os._exit(0)
                threading.Thread(target=_apagar_proceso, daemon=True).start()
        elif path == "/api/captura_prueba":
            cap = ENGINE.tomar_captura("Captura Manual de Prueba")
            self._send_json(cap or {"status": "error"})
        else:
            self.send_error(404, "API endpoint no encontrado")

    def _send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

def iniciar_servidor_web(puerto=8765):
    server_address = ("", puerto)
    try:
        httpd = HTTPServer(server_address, CorviHTTPHandler)
        print(f"[CONTROL DE ASISTENCIA] Panel de control disponible en: http://127.0.0.1:{puerto}")
        httpd.serve_forever()
    except OSError:
        puerto_alt = puerto + 1
        httpd = HTTPServer(("", puerto_alt), CorviHTTPHandler)
        print(f"[CONTROL DE ASISTENCIA] Puerto {puerto} ocupado. Iniciado en: http://127.0.0.1:{puerto_alt}")
        httpd.serve_forever()

def abrir_interfaz(puerto=8765):
    url = f"http://127.0.0.1:{puerto}"
    window_args = [f"--app={url}", "--window-size=430,440"]
    if IS_LINUX:
        def _ajustar_tamano_linux():
            for _ in range(8):
                time.sleep(0.4)
                try:
                    res = subprocess.run(["wmctrl", "-r", "CORVI Control de Asistencia", "-e", "0,-1,-1,430,440"], capture_output=True)
                    if res.returncode == 0:
                        break
                except Exception:
                    pass
        threading.Thread(target=_ajustar_tamano_linux, daemon=True).start()

        # Si la ventana ya está abierta en segundo plano o minimizada, traerla al frente de inmediato
        try:
            res = subprocess.run(["wmctrl", "-a", "CORVI Control de Asistencia"], capture_output=True)
            if res.returncode == 0:
                return
        except Exception:
            pass

        for cmd in ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"]:
            try:
                subprocess.Popen([cmd] + window_args)
                return
            except Exception:
                pass
    elif IS_WINDOWS:
        def _ajustar_tamano_windows():
            import ctypes
            try:
                WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
                def enum_cb(hwnd, lparam):
                    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                        t = buff.value
                        if "Control de Asistencia" in t or "CORVI" in t:
                            # 0x0002 = SWP_NOMOVE, 0x0004 = SWP_NOZORDER, 0x0040 = SWP_SHOWWINDOW
                            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 430, 440, 0x0002 | 0x0004 | 0x0040)
                            return False
                    return True
                cb = WNDENUMPROC(enum_cb)
                for _ in range(15):
                    time.sleep(0.3)
                    ctypes.windll.user32.EnumWindows(cb, 0)
            except Exception:
                pass
        threading.Thread(target=_ajustar_tamano_windows, daemon=True).start()

        edge_paths = [
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe")
        ]
        for p in edge_paths:
            if os.path.exists(p):
                try:
                    subprocess.Popen([p] + window_args)
                    return
                except Exception:
                    pass
    webbrowser.open(url)

# =============================================================================
# AUTO-ACTUALIZADOR SILENCIOSO OTA (REPOSITORIO PÚBLICO OFICIAL CORVI)
# =============================================================================
VERSION_LOCAL = "1.3.7"
GITHUB_REPO = "Tecnologiacorvi/setup"

def verificar_y_aplicar_actualizaciones():
    def _tarea_update():
        try:
            import urllib.request
            import shutil
            import json

            url_version = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/version.json"
            req = urllib.request.Request(url_version, headers={
                "User-Agent": "CORVI-Updater",
                "Cache-Control": "no-cache"
            })
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                if resp.status == 200:
                    info = json.loads(resp.read().decode("utf-8"))
                    remota = str(info.get("version", VERSION_LOCAL)).strip()

                    def parse_v(v):
                        return [int(x) for x in v.split(".") if x.isdigit()]

                    if parse_v(remota) > parse_v(VERSION_LOCAL):
                        url_script = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/corvi_asistencia.py"
                        req_script = urllib.request.Request(url_script, headers={
                            "User-Agent": "CORVI-Updater",
                            "Cache-Control": "no-cache"
                        })
                        with urllib.request.urlopen(req_script, timeout=8.0) as s_resp:
                            if s_resp.status == 200:
                                nuevo_codigo = s_resp.read().decode("utf-8")
                                compile(nuevo_codigo, "corvi_asistencia.py", "exec")

                                ruta_actual = os.path.abspath(__file__)
                                ruta_tmp = ruta_actual + ".tmp"
                                with open(ruta_tmp, "w", encoding="utf-8") as f_tmp:
                                    f_tmp.write(nuevo_codigo)
                                shutil.move(ruta_tmp, ruta_actual)
        except Exception:
            pass

    threading.Thread(target=_tarea_update, daemon=True).start()

import atexit
def _al_cerrar_aplicacion():
    global ENGINE, HILO_ENVIO_CORREO
    if 'ENGINE' in globals() and ENGINE and ENGINE.estado == "ACTIVO":
        print("[CONTROL DE ASISTENCIA] Cierre de aplicación detectado. Finalizando y despachando reportes...")
        ENGINE.finalizar()
        if HILO_ENVIO_CORREO and HILO_ENVIO_CORREO.is_alive():
            HILO_ENVIO_CORREO.join(timeout=25)
atexit.register(_al_cerrar_aplicacion)

if __name__ == "__main__":
    verificar_y_aplicar_actualizaciones()
    puerto = CONFIG.get("puerto_web", 8765)

    def parse_version_str(v):
        return [int(x) for x in str(v).split(".") if x.isdigit()]

    # Chequeo y reciclaje inteligente de instancia previa:
    # Si detecta una versión vieja en memoria, la cierra limpiamente y levanta v1.3.7
    import urllib.request
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{puerto}/api/version", headers={'User-Agent': 'CORVI-Launcher'})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            if resp.status == 200:
                data_inst = json.loads(resp.read().decode("utf-8"))
                v_inst = data_inst.get("version", "1.0.0")
                if parse_version_str(v_inst) < parse_version_str(VERSION_LOCAL):
                    print(f"[ACTUALIZADOR] Instancia anterior v{v_inst} detectada. Cerrando para arrancar v{VERSION_LOCAL}...")
                    try:
                        urllib.request.urlopen(f"http://127.0.0.1:{puerto}/api/cerrar_servidor", timeout=1.0)
                    except Exception:
                        pass
                    time.sleep(1.2)
                else:
                    print(f"[CONTROL DE ASISTENCIA] Instancia v{v_inst} activa en puerto {puerto}. Abriendo panel de control...")
                    abrir_interfaz(puerto)
                    sys.exit(0)
    except Exception:
        # Si /api/version no respondió pero /api/estado sí responde, es una instancia antigua (v1.3.6 o inferior)
        try:
            req_old = urllib.request.Request(f"http://127.0.0.1:{puerto}/api/estado", headers={'User-Agent': 'CORVI-Launcher'})
            with urllib.request.urlopen(req_old, timeout=0.8) as resp_old:
                if resp_old.status == 200:
                    if sys.platform == "win32":
                        try:
                            import subprocess
                            subprocess.run(f"powershell -Command \"Get-Process pythonw | Where-Object {{ $_.Id -ne {os.getpid()} }} | Stop-Process -Force\"", shell=True, timeout=3)
                        except Exception:
                            pass
                    time.sleep(1.2)
        except Exception:
            pass

    print("=" * 70)
    print("   CORVI CONTROL DE ASISTENCIA — SISTEMA DE TELEMETRÍA LABORAL")
    print("   Firma: CORVI CONSULTORES S.A.S.")
    print("=" * 70)
    print(f"Colaborador asignado: {CONFIG.get('colaborador_nombre', 'N/A')} ({CONFIG.get('colaborador_cargo', 'N/A')})")
    print(f"Oficina Virtual:      {CONFIG.get('oficina_virtual_url')}")
    print(f"Intervalo telemetría: {CONFIG.get('intervalo_telemetria_seg', 10)} seg | Capturas: cada {CONFIG.get('intervalo_captura_min', 5)} min")
    print(f"Directorio de datos:  {REGISTROS_DIR}")
    print("Iniciando interfaz y servidor de fondo...")

    t_browser = threading.Thread(target=abrir_interfaz, args=(puerto,), daemon=True)
    t_browser.start()

    iniciar_servidor_web(puerto)
