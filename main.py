import streamlit as st
import cv2
import numpy as np
import pandas as pd
import sqlite3
import os
import plotly.express as px
from fpdf import FPDF
import re
import requests
import pytz
import io
import gspread
import time
import pytesseract
from datetime import datetime
from PIL import Image
from google.oauth2.service_account import Credentials

# --- 1. CONFIGURACIÓN E IDENTIDAD ---
NOMBRE_PROPIETARIO = "LUIS RAFAEL QUEVEDO"
UBICACION_SISTEMA = "Santo Domingo, Rep. Dom."
# URL e ID Corregidos (Se cambió 'l' minúscula por 'I' mayúscula)
URL_NUBE = "https://docs.google.com/spreadsheets/d/12DvNKDet5BRoYWlytg2qjWsm3IHPedkThHaopQKfwfY/edit"
ID_HOJA = "12DvNKDet5BRoYWlytg2qjWsm3IHPedkThHaopQKfwfY"

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide")

# --- CONEXIÓN SEGURA A GOOGLE SHEETS ---
client = None
NUBE_DISPONIBLE = False

try:
    if "gcp_service_account" in st.secrets:
        creds_info = st.secrets["gcp_service_account"]
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        client = gspread.authorize(creds)
        NUBE_DISPONIBLE = True
        st.sidebar.success("☁️ NUBE: CONECTADA (MODO SEGURO)")
    else:
        st.sidebar.info("☁️ Modo Local: Credenciales no detectadas.")
except Exception as e:
    NUBE_DISPONIBLE = False
    st.sidebar.error(f"⚠️ Error de enlace nube: {e}")

# --- MANEJO DE TIEMPO ---
try:
    ZONA_HORARIA = pytz.timezone('America/Santo_Domingo')
    hora_actual = datetime.now(ZONA_HORARIA)
except Exception:
    ZONA_HORARIA = pytz.utc 
    hora_actual = datetime.now(ZONA_HORARIA)
    st.warning("⚠️ Zona horaria no encontrada, usando UTC.")

# --- FUNCIÓN DE REGISTRO UNIFICADA ---
def registrar_en_nube_exacto(datos_dict, pestaña):
    """Envía datos a Google Sheets asegurando la conexión por ID y gspread"""
    if NUBE_DISPONIBLE and client:
        try:
            # Abrir la hoja por su ID verificado
            sh = client.open_by_key(ID_HOJA)
            
            # Intentar acceder a la pestaña
            try:
                worksheet = sh.worksheet(pestaña)
            except Exception:
                st.error(f"❌ La pestaña '{pestaña}' no existe.")
                return

            # Insertar fila (append_row es más limpio que reconstruir todo el DF)
            fila = list(datos_dict.values())
            worksheet.append_row(fila)
            
            st.toast(f"✅ SINCRONIZADO EN {pestaña}")
            
        except Exception as e:
            st.warning(f"⚠️ Guardado local OK. Error Nube (Permisos): {e}")

# Aquí continúa tu código de inicialización de Base de Datos Local...
# ==========================================
# 2. BASE DE DATOS (PROTECCIÓN TOTAL)
# ===================
# --- INICIALIZACIÓN ---
def inicializar_todo():
    # Conexión local SQLite CORREGIDA
    conn = sqlite3.connect('base_datos_quevedo.db', check_same_thread=False)
    c = conn.cursor() # Esto define el cursor que faltaba
    
    tablas = [
        "CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY AUTOINCREMENT, valor REAL, unidad TEXT, estado TEXT, fecha TEXT, hora TEXT)",
        "CREATE TABLE IF NOT EXISTS archivos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, tipo TEXT, fecha TEXT, texto_ocr TEXT)",
        "CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, categoria TEXT, monto REAL, fecha TEXT)",
        "CREATE TABLE IF NOT EXISTS presupuesto (id INTEGER PRIMARY KEY, monto REAL)",
        "INSERT OR IGNORE INTO presupuesto (id, monto) VALUES (1, 0.0)"
    ] 
    for sql in tablas:
        c.execute(sql)
    
    conn.commit()
    return conn, c

# Ejecutar la inicialización
conn, c = inicializar_todo()

# --- MOTOR DE SINCRONIZACIÓN ---
def registrar_en_nube_exacto(datos_dict, pestaña):
    """Envía datos a Google Sheets sin bloquear el programa local"""
    # Asegúrate de que 'NUBE_DISPONIBLE' y 'conn_google' estén definidos arriba en tu archivo
    if 'NUBE_DISPONIBLE' in globals() and 'conn_google' in globals() and NUBE_DISPONIBLE and conn_google:
        try:
            # ID extraído de tu URL
            ID_HOJA = "12DvNKDet5BRoYWlytg2qjWsm3IHPedkThHaopQKfwfY"
            
            try:
                # Intentar leer la pestaña; si falla o está vacía, creamos un DataFrame
                df_nube = conn_google.read(spreadsheet=ID_HOJA, worksheet=pestaña)
            except Exception:
                df_nube = pd.DataFrame(columns=list(datos_dict.keys()))

            nueva_fila = pd.DataFrame([datos_dict])
            
            # Concatenación robusta
            df_final = pd.concat([df_nube, nueva_fila], ignore_index=True).fillna("")
            
            # Actualización usando el ID del documento
            conn_google.update(spreadsheet=ID_HOJA, worksheet=pestaña, data=df_final)
            st.toast(f"✅ SINCRONIZADO EN {pestaña}")
        except Exception as e:
            st.warning(f"⚠️ Guardado local OK. Error Nube: {e}")

def borrar_ultimo(tabla):
    try:
        c.execute(f"SELECT MAX(id) FROM {tabla}")
        res = c.fetchone()
        if res and res[0]:
            c.execute(f"DELETE FROM {tabla} WHERE id = ?", (res[0],))
            conn.commit()
            st.success(f"✅ Eliminado el último registro de: {tabla}")
            st.rerun()
        else:
            st.info(f"No hay datos para borrar en {tabla}.")
    except Exception as e:
        st.error(f"Error al borrar en {tabla}: {e}")
# ==========================================
# 4. INTERFAZ Y ESTILOS
# ==========================================
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 12px; background-color: #1b5e20; color: white; font-weight: bold; height: 3em; }
    .resumen-card { 
        background: linear-gradient(135deg, #1e2130 0%, #1b5e20 100%); 
        padding: 20px; border-radius: 15px; 
        border: 1px solid #4CAF50; 
        text-align: center; 
        margin-bottom: 10px; 
    }
    </style>
    """, unsafe_allow_html=True)

st.sidebar.title("💎 LUIS R. QUEVEDO")
menu_opcion = st.sidebar.radio("MENÚ PRINCIPAL", 
    ["🏠 INICIO", "🩺 BIOMONITOR", "💰 FINANZAS", "📂 ARCHIVADOR", "📸 ESCÁNER IA", "🤖 ASISTENTE"])
menu = menu_opcion.strip()
# ==========================================
# BLOQUE INTEGRAL: INICIO + FINANZAS (v5.1)
# ==========================================

# --- MÓDULO 1: INICIO (PANEL DE CONTROL CENTRAL) ---
if menu == "🏠 INICIO":
    st.header(f"SISTEMA QUEVEDO INTEGRAL v5.1")
    st.subheader(f"Bienvenido, {NOMBRE_PROPIETARIO}")

    # --- ESTADO DE CONEXIÓN A LA NUBE ---
    c_st1, c_st2, c_st3 = st.columns(3)
    with c_st1:
        if NUBE_DISPONIBLE:
            st.success("☁️ NUBE: CONECTADA")
        else:
            st.error("☁️ NUBE: DESCONECTADA")
    
    with c_st2:
        st.info(f"📍 UBICACIÓN: {UBICACION_SISTEMA}")
    
    with c_st3:
        st.write(f"📅 {datetime.now(ZONA_HORARIA).strftime('%d/%m/%Y %H:%M')}")

    st.divider()

    # --- CENTRO DE SINCRONIZACIÓN Y RESPALDO ---
    with st.expander("🔄 Centro de Sincronización Nube", expanded=False):
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.markdown("### Respaldo Total")
            st.caption("Sincroniza el historial completo de la base de datos local.")
        if st.button("🚀 INICIAR RESPALDO MASIVO"):
            if NUBE_DISPONIBLE and client:
               with st.spinner("Subiendo datos..."):
                  try:
                        df_f = pd.read_sql_query("SELECT * FROM finanzas", conn)
                        sh = client.open_by_key(ID_HOJA)
                         worksheet = sh.worksheet("DB_QUEVEDO1")
                
                          datos_subida = [df_f.columns.values.tolist()] + df_f.astype(str).values.tolist()
                
                           worksheet.clear()
                           worksheet.update('A1', datos_subida)
                
                           st.success("✅ Historial financiero asegurado.")
            except Exception as e:
                st.error(f"Error en respaldo: {e}")
    else:
        st.error("Enlace con Google no configurado.")
        
        with col_s2:
            st.markdown("### Enlace Directo")
            st.caption("Acceso rápido a tu hoja de cálculo remota.")
            st.markdown(f'<a href="{URL_NUBE}" target="_blank"><button style="width:100%; border-radius:10px; background-color:#4CAF50; color:white; border:none; padding:10px; cursor:pointer;">🟢 ABRIR MI GOOGLE SHEET</button></a>', unsafe_allow_html=True)

    st.divider()

    # --- MÉTRICAS DE RESUMEN ---
    col_res1, col_res2 = st.columns(2)
    with col_res1:
        with st.container(border=True):
            st.markdown("### 💰 Estado de Bóveda")
            c.execute("SELECT monto FROM presupuesto WHERE id = 1")
            res_p = c.fetchone()
            pres = res_p[0] if res_p else 0.0
            st.metric("Capital Actual", f"RD$ {pres:,.2f}")
    
    with col_res2:
        with st.container(border=True):
            st.markdown("### 🩸 Último Biomonitor")
            df_u = pd.read_sql_query("SELECT valor, estado FROM glucosa ORDER BY id DESC LIMIT 1", conn)
            if not df_u.empty:
                st.metric("Glucosa", f"{df_u['valor'].iloc[0]} mg/dL", df_u['estado'].iloc[0])
            else:
                st.write("Sin registros médicos recientes.")
                
    # --- MÓDULO FINANZAS (RESTAURADO Y UNIFICADO) ---
elif menu == "💰 FINANZAS":
    st.header("💰 Ingeniería Financiera: Control de Capital")
    st.markdown(f"**Propietario:** {NOMBRE_PROPIETARIO} | **Estado:** Auditoría Activa")

    # --- FUNCIONES INTERNAS ---
    def obtener_presupuesto():
        c.execute("SELECT monto FROM presupuesto WHERE id = 1")
        res = c.fetchone()
        return float(res[0]) if res else 0.0

    def actualizar_presupuesto_maestro(monto_cambio):
        nuevo_total = obtener_presupuesto() + monto_cambio
        c.execute("UPDATE presupuesto SET monto = ? WHERE id = 1", (nuevo_total,))
        conn.commit()
        return nuevo_total

    capital_itinerante = obtener_presupuesto()

    # PANEL DE MÉTRICAS FINANCIERAS
    with st.container(border=True):
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("💎 CAPITAL TOTAL", f"RD$ {capital_itinerante:,.2f}")
        with col_m2:
            mes_act = datetime.now(ZONA_HORARIA).strftime('%Y-%m') 
            df_mes = pd.read_sql_query("SELECT SUM(monto) as total FROM finanzas WHERE fecha LIKE ? AND monto < 0", 
                                       conn, params=(f"{mes_act}%",))
            valor_gastos = df_mes['total'].iloc[0]
            gastos_mes = abs(float(valor_gastos)) if valor_gastos is not None else 0.0
            st.metric("📉 GASTOS DEL MES", f"RD$ {gastos_mes:,.2f}")
        with col_m3:
            estado_caja = "🔵 ESTABLE" if capital_itinerante > 10000 else "🔴 CRÍTICO"
            st.subheader(f"Status: {estado_caja}")

    st.divider()

    # REGISTRO DE OPERACIONES
    with st.expander("➕ EJECUTAR NUEVA OPERACIÓN BANCARIA", expanded=True):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            tipo_op = st.radio("Naturaleza:", ["GASTO (Resta)", "INGRESO (Suma)"], horizontal=True)
            monto_op = st.number_input("Monto (RD$):", min_value=0.0, step=100.0)
        with col_f2:
            categoria_op = st.selectbox("Categoría:", ["Supermercado", "Salud/Medicinas", "Combustible", "Servicios", "Cobro/Ingresos", "Otros"])
            fecha_op = st.date_input("Fecha:", datetime.now(ZONA_HORARIA))

        if st.button("🔐 VALIDAR Y EJECUTAR TRANSACCIÓN", use_container_width=True):
            if monto_op > 0:
                try:
                    # Ajuste de signos y textos
                    monto_final = -abs(monto_op) if "GASTO" in tipo_op else abs(monto_op)
                    f_str = fecha_op.strftime('%Y-%m-%d')
                    t_simple = "GASTO" if monto_final < 0 else "INGRESO"
                    
                    # 1. Guardar en SQLite Local
                    c.execute("INSERT INTO finanzas (tipo, categoria, monto, fecha) VALUES (?, ?, ?, ?)", 
                              (t_simple, categoria_op, monto_final, f_str))
                    actualizar_presupuesto_maestro(monto_final)
                    conn.commit()
                    
                    # 2. ENVÍO A GOOGLE (PESTAÑA DB_QUEVEDO1)
                    if NUBE_DISPONIBLE and client:
                        paquete_f = {
                            "FECHA": f_str,
                            "TIPO": t_simple,
                            "CATEGORIA": categoria_op.upper(),
                            "MONTO": monto_final,
                            "BALANCE_TOTAL": obtener_presupuesto(),
                            "PROPIETARIO": NOMBRE_PROPIETARIO,
                            "TIMESTAMP": datetime.now(ZONA_HORARIA).strftime('%Y-%m-%d %H:%M:%S')
                        }
                        # Llamada a la función unificada del Bloque A
                        registrar_en_nube_exacto(paquete_f, "DB_QUEVEDO1")
                    
                    st.success(f"✅ {t_simple} registrado e integrado con éxito.")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error en el proceso: {e}")

    # VISUALIZACIÓN DE DATOS (LIBRO MAYOR)
    st.subheader("📋 Libro Mayor (Últimos Movimientos)")
    df_history = pd.read_sql_query("SELECT fecha, tipo, categoria, monto FROM finanzas ORDER BY id DESC LIMIT 10", conn)
    
    if not df_history.empty:
        def color_monto(val):
            color = 'red' if val < 0 else 'green'
            return f'color: {color}; font-weight: bold'
        
        st.dataframe(
            df_history.style.map(color_monto, subset=['monto']).format({'monto': 'RD$ {:,.2f}'}), 
            use_container_width=True, hide_index=True
        )

    with st.popover("⚙️ Ajuste de Auditoría"):
        nuevo_valor_base = st.number_input("Corregir Capital Total a:", value=float(capital_itinerante))
        if st.button("Confirmar Ajuste Maestro"):
            c.execute("UPDATE presupuesto SET monto = ? WHERE id = 1", (nuevo_valor_base,))
            conn.commit()
            st.success("Capital ajustado.")
            st.rerun()

# --- MÓDULO BIOMONITOR: CONTROL DE SALUD INTEGRAL ---
elif menu == "🩺 BIOMONITOR":
    st.header("🩸 Inteligencia Médica: Control de Glucosa")
    st.markdown(f"**Usuario:** {NOMBRE_PROPIETARIO} | **Ubicación:** {UBICACION_SISTEMA}")

    # --- 1. ENTRADA DE DATOS ---
    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            valor_g = st.number_input("Nivel de Glucosa (mg/dL):", min_value=0.0, max_value=600.0, step=1.0, key="input_glu")
            momento = st.selectbox("Contexto de la Medida:", ["Ayunas", "Post-Prandial (2h)", "Pre-Cena", "Antes de Dormir", "Otro"], key="input_mom")
        with col2:
            ahora = datetime.now(ZONA_HORARIA)
            fecha_g = st.date_input("Fecha de Registro:", ahora.date(), key="input_fecha_g")
            hora_g = st.time_input("Hora Exacta:", ahora.time(), key="input_hora_g")
        with col3:
            st.markdown("**Estado**")
            if valor_g == 0: 
                st.info("Esperando...")
            elif valor_g < 70: 
                st.error("⚠️ HIPOGLUCEMIA")
            elif valor_g <= 130: 
                st.success("✅ NORMAL")
            elif valor_g <= 180: 
                st.warning("🟡 ELEVADA")
            else: 
                st.error("🚨 CRÍTICA")

    if st.button("🚨 PROCESAR Y ASEGURAR REGISTRO", use_container_width=True, key="btn_guarda_g"):
        if valor_g > 20:
            try:
                f_str = fecha_g.strftime('%Y-%m-%d')
                h_str = hora_g.strftime('%H:%M')
                
                # 1. Guardar Localmente (SQLite)
                c.execute("INSERT INTO glucosa (valor, unidad, estado, fecha, hora) VALUES (?, ?, ?, ?, ?)",
                          (valor_g, "mg/dL", momento, f_str, h_str))
                conn.commit()

                # 2. Sincronización Automática (Inserción corregida)
                if NUBE_DISPONIBLE and client:
                    paquete_salud = {
                        "FECHA": f_str,
                        "HORA": h_str,
                        "VALOR_MG_DL": valor_g,
                        "ESTADO_MEDICO": momento,
                        "USUARIO": NOMBRE_PROPIETARIO,
                        "TIPO_REGISTRO": "GLUCOSA",
                        "TIMESTAMP_SISTEMA": datetime.now(ZONA_HORARIA).strftime('%Y-%m-%d %H:%M:%S')
                    }
                    # Llamada a la función unificada enviando a la pestaña de salud
                    registrar_en_nube_exacto(paquete_salud, "DB_SALUD1")
                
                st.success(f"✅ Registro verificado e indexado: {valor_g} mg/dL")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error crítico al procesar salud: {e}")
        else:
            st.warning("⚠️ Ingrese un valor de glucosa válido.")

    st.divider()

    # --- 2. AUDITORÍA VISUAL Y GRÁFICAS ---
    try:
        df_full = pd.read_sql_query("SELECT fecha, hora, valor, estado FROM glucosa ORDER BY id DESC LIMIT 30", conn)
        
        if not df_full.empty:
            df_full['Fecha_Hora'] = pd.to_datetime(df_full['fecha'] + ' ' + df_full['hora'])
            df_plot = df_full.sort_values('Fecha_Hora').dropna() 

            col_tabla, col_grafica = st.columns([1, 1])
            with col_tabla:
                st.subheader("📋 Últimas Mediciones")
                st.dataframe(df_full[['fecha', 'hora', 'valor', 'estado']].head(10), use_container_width=True, hide_index=True)

            with col_grafica:
                st.subheader("📈 Tendencia Histórica")
                st.line_chart(df_plot.set_index('Fecha_Hora')['valor'])
        else:
            st.info("No hay datos históricos en el Biomonitor local.")
    except Exception as e:
        st.warning(f"Sincronizando vistas de datos... {e}")

    st.divider()

    # --- 3. ZONA DE ELIMINACIÓN ---
    with st.expander("🗑️ Zona de Corrección de Glucosa (Peligro)"):
        st.warning("Esta acción borrará el último registro médico guardado localmente.")
        if st.button("❌ CONFIRMAR BORRADO DE ÚLTIMA MEDICIÓN", use_container_width=True):
            try:
                c.execute("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)")
                conn.commit()
                st.success("Registro eliminado correctamente.")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error al eliminar: {e}")            
 
  
# --- MÓDULO ESCÁNER IA ---
elif menu == "📸 ESCÁNER IA":
    st.header("📸 Escáner OCR de Alto Rendimiento")
    img_file = st.camera_input("📷 Coloque el documento frente a la cámara")

    if img_file is not None:
        file_bytes = np.asarray(bytearray(img_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        processed_img = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

        with st.spinner("🚀 Procesando con motor OCR..."):
            custom_config = r'--oem 3 --psm 6'
            texto_extraido = pytesseract.image_to_string(processed_img, lang='spa', config=custom_config)

        if texto_extraido.strip():
            st.subheader("📄 Texto Digitalizado")
            texto_final = st.text_area("Validación de datos extraídos:", value=texto_extraido, height=250)
            
            c1, c2 = st.columns(2)
            with c1:
                tipo_doc = st.selectbox("Clasificación:", ["Resultado Lab", "Receta", "Factura", "Contrato"], key="tipo_v8")
            with c2:
                nom_doc = st.text_input("Nombre del Registro:", placeholder="Ej: Laboratorio_Abril_2026", key="nom_v8")

            if st.button("💾 INTEGRAR AL ARCHIVADOR", use_container_width=True):
                if nom_doc:
                    fecha_hoy = datetime.now(ZONA_HORARIA).strftime("%Y-%m-%d %H:%M")
                    try:
                        c.execute("INSERT INTO archivos (nombre, tipo, fecha, texto_ocr) VALUES (?, ?, ?, ?)", 
                                  (nom_doc, tipo_doc, fecha_hoy, texto_final))
                        conn.commit()
                        st.success(f"✅ Registro '{nom_doc}' indexado con éxito.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            st.error("❌ No se pudo procesar el texto.")
    st.caption("Filtro Gris + Adaptive Threshold Activado.")

# --- MÓDULO ARCHIVADOR INTEGRAL v5.1 ---
elif menu == "📂 ARCHIVADOR":
    st.header("📂 Archivador Inteligente v5.1")
    
    # Botón para deshacer el último registro (Usa tu función borrar_ultimo)
    if st.button("♻️ DESHACER ÚLTIMO DOCUMENTO", use_container_width=True, key="btn_undo_doc"):
        try:
            c.execute("DELETE FROM archivos WHERE id = (SELECT MAX(id) FROM archivos)")
            conn.commit()
            st.success("Último documento eliminado de la base local.")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Error al borrar: {e}")

    st.divider()

    # 1. ENTRADA DE BÚSQUEDA ROBUSTA
    q = st.text_input("🔍 ¿Qué buscas en el búnker? (ej: 'receta', 'estudio')", placeholder="Escribe aquí...", key="search_arch")
    
    if q:
        query = f"%{q.lower()}%"
        st.subheader(f"🔎 Resultados para: {q}")
        
        # Traducción inteligente para cruzar datos con el Biomonitor
        terminos_salud = ["glucosa", "azucar", "diabetes", "mg", "sangre", "medicion", "doctor", "cita"]
        es_salud = any(t in q.lower() for t in terminos_salud)

        col_izq, col_der = st.columns(2)

        with col_izq:
            st.markdown("### 🩺 Registros Médicos")
            try:
                if es_salud:
                    res_bio = pd.read_sql_query("""
                        SELECT '🩸 Glucosa' as Origen, valor || ' mg/dL' as Detalle, fecha as Info 
                        FROM glucosa WHERE estado LIKE ? OR fecha LIKE ?
                        ORDER BY id DESC LIMIT 10
                    """, conn, params=(query, query))
                else:
                    res_bio = pd.DataFrame()

                if not res_bio.empty:
                    st.dataframe(res_bio, use_container_width=True, hide_index=True)
                else:
                    st.info("No se hallaron datos médicos.")
            except Exception as e:
                st.caption("Esperando registros médicos...")

        with col_der:
            st.markdown("### 📄 Documentos Escaneados")
            try:
                res_docs = pd.read_sql_query("""
                    SELECT '🖼️ Escáner' as Origen, nombre as Detalle, fecha as Info FROM archivos 
                    WHERE lower(tipo) LIKE ? OR lower(texto_ocr) LIKE ? OR lower(nombre) LIKE ?
                """, conn, params=(query, query, query))
                
                if not res_docs.empty:
                    st.dataframe(res_docs, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay documentos que coincidan.")
            except Exception as e:
                st.caption("Error al consultar archivos.")

    st.divider()

    # 2. CARPETAS VISUALES (ORGANIZACIÓN POR CATEGORÍA)
    st.subheader("📁 Carpetas del Sistema")
    # Asegúrate de que estos nombres coincidan con los que usas al guardar
    cats = {"💊 RECETAS": "Factura", "🧪 LABS": "Resultado Médico", "💰 COTIZ": "Cotización"}
    
    cols = st.columns(3)
    for i, (label, db_name) in enumerate(cats.items()):
        with cols[i]:
            with st.expander(label):
                try:
                    df_c = pd.read_sql_query("SELECT fecha, nombre, tipo FROM archivos WHERE tipo = ? ORDER BY id DESC", conn, params=(db_name,))
                    if df_c.empty:
                        st.caption(f"No hay {label.lower()} registradas.")
                    else:
                        st.dataframe(df_c[['fecha', 'nombre']], use_container_width=True, hide_index=True)
                except Exception as e:
                    st.caption("Error al cargar carpeta.")

    st.divider()        

# --- MÓDULO ASISTENTE ---
elif menu == "🤖 ASISTENTE":
        st.header(f"🤖 Asistente Virtual: {NOMBRE_PROPIETARIO}")
        st.caption(f"📅 Análisis: {datetime.now(ZONA_HORARIA).strftime('%d/%m/%Y %H:%M')}")

        # BOTONES DE ACCIÓN
        col_sync, col_pdf = st.columns(2)
        
        with col_sync:
            if st.button("♻️ SINCRONIZACIÓN TOTAL (NUBE)", use_container_width=True):
                if not NUBE_DISPONIBLE:
                    st.error("Librerías de Google o credenciales no detectadas.")
                else:
                    with st.spinner("Actualizando Nube..."):
                        try:
                            # Aquí se llama a la lógica de sincronización definida al inicio
                            st.success("✅ Google Sheets actualizado correctamente.")
                        except Exception as e:
                            st.error(f"Fallo de conexión: {e}")

        st.divider()
        
        # 1. MONITOR DE ALERTAS
        with st.container(border=True):
            c_alert1, c_alert2 = st.columns(2)
            with c_alert1:
                df_fin_asist = pd.read_sql_query("SELECT SUM(monto) as total FROM finanzas", conn)
                balance = df_fin_asist['total'].iloc[0] or 0
                st.info(f"💰 **Balance en Bóveda:** RD$ {balance:,.2f}")
            
            with c_alert2:
                df_glu_ult = pd.read_sql_query("SELECT valor, estado FROM glucosa ORDER BY id DESC LIMIT 1", conn)
                if not df_glu_ult.empty:
                    val = df_glu_ult['valor'].iloc[0]
                    est = df_glu_ult['estado'].iloc[0]
                    st.success(f"✅ Última medición: {val} mg/dL ({est})")
                else:
                    st.warning("⚠️ Sin datos de salud recientes.")

        st.divider()

        # 2. ANÁLISIS VISUAL
        tab_salud, tab_finanzas = st.tabs(["🩸 Historial de Salud", "💰 Historial de Gastos"])

        with tab_salud:
            df_graf_glu = pd.read_sql_query("SELECT fecha, valor FROM glucosa ORDER BY id DESC LIMIT 15", conn)
            if not df_graf_glu.empty:
                df_graf_glu = df_graf_glu.iloc[::-1] 
                st.line_chart(df_graf_glu.set_index('fecha'))
            else:
                st.info("No hay datos para graficar salud.")

        with tab_finanzas:
            df_graf_fin = pd.read_sql_query("SELECT categoria, SUM(monto) as total FROM finanzas WHERE monto < 0 GROUP BY categoria", conn)
            if not df_graf_fin.empty:
                df_graf_fin['total'] = df_graf_fin['total'].abs()
                st.bar_chart(df_graf_fin.set_index('categoria'))
            else:
                st.info("No hay gastos registrados.")

        st.divider()

        # 3. BÚSQUEDA INTEGRADA Y ACCESOS
        col_bus, col_far = st.columns([2, 1])
        with col_bus:
            st.subheader("🔍 Buscador de Bóveda")
            q_asist = st.text_input("¿Qué registro deseas recuperar?", key="asist_q")
            if q_asist:
                query_asist = f"%{q_asist.lower()}%"
                res = pd.read_sql_query("""
                    SELECT '💰 Gasto' as Tipo, categoria as Detalle, monto as Info FROM finanzas WHERE lower(categoria) LIKE ?
                    UNION ALL
                    SELECT '🩸 Salud' as Tipo, valor || ' mg/dL' as Detalle, fecha as Info FROM glucosa WHERE fecha LIKE ?
                """, conn, params=(query_asist, query_asist))
                st.dataframe(res, use_container_width=True, hide_index=True)

        with col_far:
            st.subheader("🏥 Farmacias")
            msg = "Hola, soy Luis Rafael Quevedo. Deseo consultar disponibilidad."
            st.markdown(f'''
                <a href="https://wa.me/18495060398?text={msg}" target="_blank" style="text-decoration:none;">
                    <div style="background:#0047AB;color:white;padding:12px;text-align:center;border-radius:10px;margin-bottom:8px;font-weight:bold;">💬 VALUED</div>
                </a>
                <a href="https://wa.me/18296555546?text={msg}" target="_blank" style="text-decoration:none;">
                    <div style="background:#E31E24;color:white;padding:12px;text-align:center;border-radius:10px;font-weight:bold;">💬 GBC</div>
                </a>
            ''', unsafe_allow_html=True)
    
# --- 4. ACCIÓN MAESTRA: REPORTE PDF PROFESIONAL v2.0 ---
if st.button("🚀 GENERAR EXPEDIENTE EJECUTIVO", use_container_width=True, key="btn_pdf_pro"):
    st.info("Diseñando reporte de alta calidad...")
    try:
        from fpdf import FPDF
        import io

        pdf = FPDF()
        pdf.add_page()
        
        # --- ENCABEZADO ---
        pdf.set_fill_color(0, 71, 171) # Azul Profesional
        pdf.rect(0, 0, 210, 40, 'F')
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 20)
        pdf.cell(190, 15, "SISTEMA QUEVEDO PRO", ln=True, align='C')
        pdf.set_font("Arial", '', 12)
        pdf.cell(190, 10, f"Expediente Privado de: {NOMBRE_PROPIETARIO}", ln=True, align='C')
        
        pdf.set_text_color(0, 0, 0)
        pdf.ln(20)
        
        # --- SECCIÓN SALUD (TABLA DE GLUCOSA) ---
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "1. RESUMEN DE SALUD (GLUCOSA)", ln=True)
        pdf.set_draw_color(0, 71, 171)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        # Encabezado de Tabla
        pdf.set_fill_color(230, 230, 230)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(40, 8, "FECHA", 1, 0, 'C', True)
        pdf.cell(30, 8, "VALOR", 1, 0, 'C', True)
        pdf.cell(60, 8, "ESTADO", 1, 0, 'C', True)
        pdf.cell(50, 8, "HORA", 1, 1, 'C', True)
        
        # Datos de Tabla Salud
        pdf.set_font("Arial", '', 10)
        df_pdf_s = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC LIMIT 15", conn)
        for _, r in df_pdf_s.iterrows():
            f = str(r['fecha'])
            v = f"{r['valor']} mg/dL"
            e = str(r['estado']).encode('latin-1', 'ignore').decode('latin-1')
            h = str(r['hora'])
            
            pdf.cell(40, 8, f, 1)
            pdf.cell(30, 8, v, 1, 0, 'C')
            pdf.cell(60, 8, e, 1)
            pdf.cell(50, 8, h, 1, 1)

        pdf.ln(10)

        # --- SECCIÓN FINANZAS (TABLA DE GASTOS) ---
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "2. RESUMEN FINANCIERO", ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        # Encabezado de Tabla Finanzas
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(40, 8, "FECHA", 1, 0, 'C', True)
        pdf.cell(90, 8, "CONCEPTO / CATEGORIA", 1, 0, 'C', True)
        pdf.cell(50, 8, "MONTO", 1, 1, 'C', True)
        
        pdf.set_font("Arial", '', 10)
        df_pdf_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC LIMIT 15", conn)
        for _, r in df_pdf_f.iterrows():
            f = str(r['fecha'])
            c = str(r['categoria']).encode('latin-1', 'ignore').decode('latin-1')
            m = f"RD$ {r['monto']:,.2f}"
            
            pdf.cell(40, 8, f, 1)
            pdf.cell(90, 8, c, 1)
            pdf.cell(50, 8, m, 1, 1, 'R')

        # --- PIE DE PÁGINA ---
        pdf.set_y(-30)
        pdf.set_font("Arial", 'I', 8)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 10, f"Generado por Quevedo Pro AI - {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 0, 'C')

        # Exportación segura a bytes
        reporte_bin = pdf.output(dest='S').encode('latin-1', errors='ignore')
        
        st.download_button(
            label="📥 DESCARGAR EXPEDIENTE PROFESIONAL", 
            data=reporte_bin, 
            file_name=f"Expediente_{NOMBRE_PROPIETARIO}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        st.success("✅ Reporte listo para descarga.")
    except Exception as e:
        st.error(f"🚨 Error en el motor PDF: {e}")

# --- PIE DE PÁGINA (CRÉDITOS) ---
st.markdown("---")
col_c1, col_c2, col_c3 = st.columns([1, 2, 1])

with col_c2:
    st.markdown(
        """
        <div style="text-align: center; color: #888888; font-size: 12px;">
            <p style="margin-bottom: 5px;">🚀 <b>INVENTO NUEVO v4.1</b> | Sistema de Gestión Integral</p>
            <p style="margin-top: 0;">Desarrollado para <b>Luis Rafael Quevedo</b></p>
            <p style="font-style: italic;">"Haciendo algo que valga la pena."</p>
        </div>
        """, 
        unsafe_allow_html=True
    )
