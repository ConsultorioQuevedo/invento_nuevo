import streamlit as st
import cv2
import numpy as np
import pandas as pd
import sqlite3
import pytesseract 
from PIL import Image
import os
import plotly.express as px
from fpdf import FPDF
import re 
import requests
import pytz
from pyzbar.pyzbar import decode
import unicodedata
import io
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# ==========================================
## ==========================================
# 1. CONFIGURACIÓN E IDENTIDAD
# ==========================================

# Configuración de la página (Debe ser lo primero)
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide", page_icon="💎")

NOMBRE_PROPIETARIO = "LUIS RAFAEL QUEVEDO"
UBICACION_SISTEMA = "Santo Domingo, Rep. Dom."

# Manejo de Zona Horaria
try:
    ZONA_HORARIA = pytz.timezone('America/Santo_Domingo')
    hora_actual = datetime.now(ZONA_HORARIA)
except Exception:
    ZONA_HORARIA = pytz.utc 
    hora_actual = datetime.now(ZONA_HORARIA)
    st.warning("⚠️ Zona horaria no encontrada, usando UTC.")

# URL Directa de tu Google Sheet
URL_NUBE = "https://docs.google.com/spreadsheets/d/18030cQtLcVWdHXMMX2MhCu4aeyvB_ytVUYJX4wCpTbl/edit"

#=======
# 2. BASE DE DATOS (PROTECCIÓN TOTAL)
# ==========================================

try:
    conn_google = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    conn_google = None
    st.warning("⚠️ Conexión a la nube en espera (Modo Local activo)")

# CORRECCIÓN: Ahora acepta la pestaña como parámetro para no mezclar Salud con Dinero
def registrar_en_nube_exacto(datos_dict, pestaña="DB_QUEVEDO1"):
    try:
        # Leemos la nube usando la URL directa y la pestaña indicada
        df_nube = conn_google.read(spreadsheet=URL_NUBE, worksheet=pestaña)
        nueva_fila = pd.DataFrame([datos_dict])
        df_final = pd.concat([df_nube, nueva_fila], ignore_index=True)
        
        # Actualizamos la hoja de Google
        conn_google.update(spreadsheet=URL_NUBE, worksheet=pestaña, data=df_final)
        st.success(f"✅ Sincronizado en la Nube -> {pestaña}")
    except Exception as e:
        st.error(f"❌ Error de sincronización en {pestaña}: {e}")

def inicializar_todo():
    # Carpetas esenciales
    base = "archivador_quevedo"
    folders = ["BIOMONITOR", "FINANZAS", "ARCHIVADOR", "ESCANER"]
    if not os.path.exists(base):
        os.makedirs(base)
    for f in folders:
        os.makedirs(os.path.join(base, f), exist_ok=True)
    
    # Conexión Local SQLite
    conn = sqlite3.connect("sistema_quevedo_integral.db", check_same_thread=False)
    c = conn.cursor()
    
    # TABLAS PURIFICADAS (Nombres unificados para evitar errores de 'Tabla no encontrada')
    tablas = [
        "CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY AUTOINCREMENT, valor REAL, unidad TEXT, estado TEXT, fecha TEXT, hora TEXT)",
        "CREATE TABLE IF NOT EXISTS archivos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, tipo TEXT, fecha TEXT, texto_ocr TEXT)",
        "CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, categoria TEXT, monto REAL, fecha TEXT)",
        "CREATE TABLE IF NOT EXISTS inventario (id INTEGER PRIMARY KEY AUTOINCREMENT, producto TEXT, cantidad INTEGER, precio REAL, fecha TEXT)",
        "CREATE TABLE IF NOT EXISTS presupuesto (id INTEGER PRIMARY KEY, monto REAL)",
        "INSERT OR IGNORE INTO presupuesto (id, monto) VALUES (1, 0.0)"
    ] 
    for sql in tablas:
        c.execute(sql)
    
    conn.commit()
    return conn, c

# Ejecutar inicialización
conn, c = inicializar_todo()

# ==========================================
# 3. FUNCIONES COMPLEMENTARIAS
# ==========================================

def borrar_ultimo(tabla):
    try:
        # Buscamos el ID más alto de la tabla indicada
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
# 4. INTERFAZ Y ESTILOS (MANTENIENDO TU DISEÑO)
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

# NAVEGACIÓN (Los 4 Pilares + Gestión)
st.sidebar.title("💎 LUIS R. QUEVEDO")
menu = st.sidebar.radio("MENÚ PRINCIPAL", 
    ["🏠 INICIO", "🩺 BIOMONITOR", "💰 FINANZAS", "📂 ARCHIVADOR", "📸 ESCÁNER IA", "🤖 ASISTENTE"])

# ==========================================
# 5. LÓGICA DE MÓDULOS (INICIO PERPETUO)
# ==========================================

if menu == "🏠 INICIO":
    st.header(f"📊 Panel de Control: {NOMBRE_PROPIETARIO}")
    
    # --- CÁLCULOS HISTÓRICOS (Aquí evitamos que se ponga en 0 a las 12:00) ---
    try:
        # Sumamos TODO el historial de finanzas acumulado
        total_ingresos = pd.read_sql_query("SELECT SUM(monto) FROM finanzas WHERE tipo = 'Ingreso'", conn).iloc[0,0] or 0
        total_gastos = pd.read_sql_query("SELECT SUM(monto) FROM finanzas WHERE tipo = 'Gasto'", conn).iloc[0,0] or 0
        balance_acumulado = total_ingresos - total_gastos

        # Buscamos la última glucosa registrada sin importar la fecha
        # Primero intentamos en 'biomonitor', si falla vamos a 'glucosa'
        try:
            df_glu = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1", conn)
        except:
            df_glu = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1", conn)
        
        valor_g = df_glu['valor'].iloc[0] if not df_glu.empty else 0
    except Exception as e:
        balance_acumulado, valor_g = 0, 0

    # --- MÉTRICAS EN PANTALLA ---
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="resumen-card">', unsafe_allow_html=True)
        st.metric("💰 BALANCE TOTAL", f"RD$ {balance_acumulado:,.2f}")
        st.write("Historial Acumulado")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="resumen-card">', unsafe_allow_html=True)
        st.metric("🩺 ÚLTIMA GLUCOSA", f"{valor_g} mg/dL")
        st.write("Último valor guardado")
        st.markdown('</div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="resumen-card">', unsafe_allow_html=True)
        st.metric("📅 ESTADO", "OPERATIVO")
        st.write("Búnker Sincronizado")
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # --- REGISTROS EN TIEMPO REAL (TODO EL HISTORIAL) ---
    st.subheader("📝 Registros en Tiempo Real")
    df_historial = pd.read_sql_query("SELECT id, tipo, categoria, monto, fecha FROM finanzas ORDER BY id DESC", conn)
    
    if not df_historial.empty:
        # Mostramos la tabla completa para que la veas siempre
        st.dataframe(df_historial, use_container_width=True, height=250)
    else:
        st.info("No hay datos en el historial. Comienza a registrar en el módulo de Finanzas.")

    # --- BOTONES DE FUNCIÓN (Sin quitar ninguno) ---
    st.subheader("⚙️ Gestión de Datos")
    col_acc1, col_acc2 = st.columns(2)
    
    with col_acc1:
        # Mantenemos tu función de borrado
        if st.button("♻️ BORRAR ÚLTIMO REGISTRO"):
            c.execute("DELETE FROM finanzas WHERE id = (SELECT MAX(id) FROM finanzas)")
            conn.commit()
            st.success("Último movimiento eliminado.")
            st.rerun()

    with col_acc2:
        if st.button("📊 ACTUALIZAR VISTA"):
            st.rerun()

    # --- ENLACES DE COMUNICACIÓN ---
    st.divider()
    col_l1, col_l2, col_l3 = st.columns(3)
    
    # Cambia estos datos por los tuyos reales
    num_wa = "18090000000" 
    correo = "luisrafaelquevedo@gmail.com"

    col_l1.link_button("💬 WHATSAPP", f"https://wa.me/{num_wa}")
    col_l2.link_button("📧 GMAIL", f"mailto:{correo}")
    col_l3.link_button("🏥 REFERENCIA", "https://www.referencia.do")

    
# --- MÓDULO FINANZAS: INTELIGENTE Y PERSISTENTE ---
elif menu == "💰 FINANZAS":
    st.header("💰 Ingeniería Financiera: Control de Capital")
    st.markdown(f"**Propietario:** {NOMBRE_PROPIETARIO} | **Estado:** Auditoría Activa")

    # --- 1. MOTOR DE CÁLCULO DE PRESUPUESTO ---
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

    # --- 2. DASHBOARD DE ESTADO FINANCIERO ---
    with st.container(border=True):
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("💎 CAPITAL TOTAL", f"RD$ {capital_itinerante:,.2f}")
        with col_m2:
            # Corrección: Búsqueda de gastos del mes actual de forma más precisa
            mes_act = datetime.now().strftime('%Y-%m') 
            df_mes = pd.read_sql_query("SELECT SUM(monto) as total FROM finanzas WHERE fecha LIKE ? AND monto < 0", 
                                       conn, params=(f"{mes_act}%",))
            
            # Manejo de valores Nulos en el total
            valor_gastos = df_mes['total'].iloc[0]
            gastos_mes = abs(float(valor_gastos)) if valor_gastos is not None else 0.0
            st.metric("📉 GASTOS DEL MES", f"RD$ {gastos_mes:,.2f}", delta_color="inverse")
        with col_m3:
            estado_caja = "🔵 ESTABLE" if capital_itinerante > 10000 else "🔴 CRÍTICO"
            st.subheader(f"Status: {estado_caja}")

    st.divider()

    # --- 3. REGISTRO DE TRANSACCIONES ---
    with st.expander("➕ EJECUTAR NUEVA OPERACIÓN BANCARIA", expanded=True):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            tipo_op = st.radio("Naturaleza:", ["GASTO (Resta)", "INGRESO (Suma)"], horizontal=True)
            monto_op = st.number_input("Monto (RD$):", min_value=0.0, step=500.0)
        
        with col_f2:
            categoria_op = st.selectbox("Categoría:", 
                ["Supermercado", "Salud/Medicinas", "Combustible", "Servicios (Luz/Agua)", "Cobro/Ingresos", "Otros"])
            # Usar la ZONA_HORARIA definida al inicio
            fecha_op = st.date_input("Fecha:", datetime.now(ZONA_HORARIA))

        if st.button("🔐 VALIDAR Y EJECUTAR TRANSACCIÓN", use_container_width=True):
            if monto_op > 0:
                try:
                    monto_final = -abs(monto_op) if "GASTO" in tipo_op else abs(monto_op)
                    f_str = fecha_op.strftime('%Y-%m-%d')

                    # A. Local
                    c.execute("INSERT INTO finanzas (tipo, categoria, monto, fecha) VALUES (?, ?, ?, ?)",
                              (tipo_op, categoria_op, monto_final, f_str))
                    
                    # B. Presupuesto
                    nuevo_balance = actualizar_presupuesto_maestro(monto_final)

                    # C. Nube (Verificando que existe la conexión y la función)
                    try:
                        paquete_nube = {
                            "FECHA": f_str,
                            "DETALLE": categoria_op,
                            "MONTO": monto_final,
                            "SALDO_RESULTANTE": nuevo_balance,
                            "TIPO": tipo_op,
                            "USUARIO": NOMBRE_PROPIETARIO
                        }
                        registrar_en_nube_exacto(paquete_nube, pestaña="DB_QUEVEDO1")
                    except NameError:
                        st.info("☁️ Sincronización de nube no configurada aún.")

                    st.success(f"✅ Procesado. Nuevo Capital: RD$ {nuevo_balance:,.2f}")
                    st.toast("Actualizando bóveda...")
                    import time
                    time.sleep(1)
                    st.rerun()

                except Exception as e:
                    st.error(f"🚨 Fallo en el Motor: {e}")
            else:
                st.warning("⚠️ El monto debe ser superior a cero.")

    # --- 4. AUDITORÍA DE MOVIMIENTOS ---
    st.subheader("📋 Libro Mayor (Últimos Movimientos)")
    df_history = pd.read_sql_query("SELECT fecha, categoria, monto FROM finanzas ORDER BY id DESC LIMIT 10", conn)
    
    if not df_history.empty:
        def color_monto(val):
            color = 'red' if val < 0 else 'green'
            return f'color: {color}; font-weight: bold'
        
        # CORRECCIÓN: .map() en lugar de .applymap() para evitar el AttributeError
        st.dataframe(
            df_history.style.map(color_monto, subset=['monto']).format({'monto': 'RD$ {:,.2f}'}), 
            use_container_width=True, 
            hide_index=True
        )
    
    # --- 5. AJUSTE MANUAL ---
    with st.popover("⚙️ Ajuste de Auditoría"):
        st.write("Solo para correcciones de saldo inicial.")
        nuevo_valor_base = st.number_input("Corregir Capital Total a:", value=float(capital_itinerante))
        if st.button("Confirmar Ajuste Maestro"):
            c.execute("UPDATE presupuesto SET monto = ? WHERE id = 1", (nuevo_valor_base,))
            conn.commit()
            st.rerun()

   

    
# --- MÓDULO BIOMONITOR: RECONSTRUCCIÓN ANTI-ERRORES ---
elif menu == "🩸 BIOMONITOR":
    st.header("🩸 Inteligencia Médica: Control de Glucosa")
    st.markdown(f"**Usuario:** {NOMBRE_PROPIETARIO} | **Ubicación:** {UBICACION_SISTEMA}")

    # --- 1. ENTRADA DE DATOS (PROTEGIDA) ---
    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            valor_g = st.number_input("Nivel de Glucosa (mg/dL):", min_value=0.0, max_value=600.0, step=1.0, key="gluc_val_input")
            momento = st.selectbox("Contexto de la Medida:", ["Ayunas", "Post-Prandial (2h)", "Pre-Cena", "Antes de Dormir", "Otro"], key="gluc_mom_input")
        with col2:
            ahora = datetime.now(ZONA_HORARIA)
            fecha_g = st.date_input("Fecha de Registro:", ahora.date(), key="gluc_fec_input")
            hora_g = st.time_input("Hora Exacta:", ahora.time(), key="gluc_hor_input")
        with col3:
            st.markdown("**Estado**")
            if valor_g == 0: st.info("Esperando...")
            elif valor_g < 70: st.error("⚠️ HIPOGLUCEMIA")
            elif valor_g <= 130: st.success("✅ NORMAL")
            elif valor_g <= 180: st.warning("🟡 ELEVADA")
            else: st.error("🚨 CRÍTICA")

        if st.button("🔐 PROCESAR Y ASEGURAR REGISTRO", use_container_width=True):
            if valor_g > 20: 
                try:
                    f_str = fecha_g.strftime('%Y-%m-%d')
                    h_str = hora_g.strftime('%H:%M')
                    c.execute("INSERT INTO glucosa (valor, unidad, estado, fecha, hora) VALUES (?, ?, ?, ?, ?)", 
                              (valor_g, "mg/dL", momento, f_str, h_str))
                    conn.commit()
                    
                    # Verificación segura de conexión a la nube
                    try:
                        if 'conn_google' in globals() and conn_google is not None:
                            paquete_nube = {
                                "ID_SISTEMA": "QUEVEDO_PRO_V4", "FECHA": f_str, "HORA": h_str,
                                "VALOR_MG_DL": valor_g, "ESTADO_MEDICO": momento,
                                "PROPIETARIO": NOMBRE_PROPIETARIO,
                                "TIMESTAMP": datetime.now(ZONA_HORARIA).strftime('%Y-%m-%d %H:%M:%S')
                            }
                            registrar_en_nube_exacto(paquete_nube, pestaña="DB_QUEVEDO1")
                    except:
                        pass # Si falla la nube, que no rompa el local
                    
                    st.success(f"✅ Registro verificado: {valor_g} mg/dL")
                    import time
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"🚨 Error: {e}")

    st.divider()

    # --- 3. AUDITORÍA Y GRÁFICA (EL BLINDAJE REAL) ---
    try:
        # Cargamos datos crudos
        df_full = pd.read_sql_query("SELECT fecha, hora, valor FROM glucosa ORDER BY id DESC LIMIT 30", conn)
        
        if not df_full.empty:
            # LIMPIEZA DE DATOS: Convertimos a string y evitamos nulos que ponen la pantalla blanca
            df_full['fecha'] = df_full['fecha'].astype(str)
            df_full['hora'] = df_full['hora'].astype(str)
            
            # El secreto: errors='coerce' convierte lo malo en 'NaT' en lugar de romper la app
            df_full['Fecha_Hora'] = pd.to_datetime(df_full['fecha'] + ' ' + df_full['hora'], errors='coerce')
            
            # Quitamos filas que no pudieron convertirse
            df_plot = df_full.dropna(subset=['Fecha_Hora']).copy()
            df_plot = df_plot.sort_values('Fecha_Hora')

            col_tabla, col_grafica = st.columns([1, 1])

            with col_tabla:
                st.subheader("📋 Últimos Registros")
                st.dataframe(df_full[['fecha', 'hora', 'valor']].head(10), use_container_width=True, hide_index=True)

            with col_grafica:
                st.subheader("📈 Curva de Glucosa")
                if not df_plot.empty:
                    st.line_chart(df_plot.set_index('Fecha_Hora')['valor'])
                else:
                    st.warning("⚠️ Datos con formato incompatible para gráfica.")
        else:
            st.info("No hay datos suficientes para generar tendencias.")
            
    except Exception as e:
        # Este catch evita que la pantalla se ponga blanca si la DB tiene basura
        st.warning("⚡ Sincronizando motor de análisis...")

                  

####-----------------------------
##ESCANER
###-------------------------------
elif menu == "📸 ESCÁNER IA":
    st.header("📸 Escáner IA - Gestión de Inventario")
    st.markdown("---")
    
    # 1. ENTRADA DE CÁMARA
    # Nota: En tu Pixel 8, dale al icono de "girar cámara" para usar el lente trasero
    img_file = st.camera_input("📷 Enfoca el código de barras del producto")

    if img_file is not None:
        # 2. PROCESAMIENTO CON PYZBAR (Adiós al error de Tesseract)
        img_pil = Image.open(img_file)
        # Convertimos a escala de grises para que sea ultra rápido
        img_gray = img_pil.convert('L') 
        objetos = decode(img_gray)

        if objetos:
            # Tomamos el primer código que encuentre
            codigo_leido = objetos[0].data.decode('utf-8')
            st.success(f"✅ CÓDIGO DETECTADO: **{codigo_leido}**")
            st.divider()

            # 3. INTELIGENCIA DE BÚSQUEDA EN TU BASE DE DATOS
            c.execute("SELECT id, producto, cantidad, precio FROM inventario WHERE producto = ?", (codigo_leido,))
            producto_db = c.fetchone()

            if producto_db:
                # --- CASO: EL PRODUCTO YA EXISTE ---
                pid, p_nombre, p_cant, p_precio = producto_db
                st.subheader(f"📦 Producto: {p_nombre}")
                
                c1, c2 = st.columns(2)
                c1.metric("Stock Actual", p_cant)
                c2.metric("Precio Venta", f"RD$ {p_precio:,.2f}")

                # Botones de Acción Rápida
                mov = st.number_input("Cantidad a mover", min_value=1, value=1, step=1)
                col_btn1, col_btn2 = st.columns(2)
                
                if col_btn1.button("➕ SUMAR AL STOCK"):
                    c.execute("UPDATE inventario SET cantidad = cantidad + ? WHERE id = ?", (mov, pid))
                    conn.commit()
                    st.success(f"Añadidas {mov} unidades a {p_nombre}")
                    st.rerun()
                    
                if col_btn2.button("➖ REGISTRAR VENTA"):
                    if p_cant >= mov:
                        c.execute("UPDATE inventario SET cantidad = cantidad - ? WHERE id = ?", (mov, pid))
                        conn.commit()
                        st.success(f"Venta de {mov} unidades registrada")
                        st.rerun()
                    else:
                        st.error("No hay suficiente stock")
            else:
                # --- CASO: PRODUCTO NUEVO ---
                st.warning("🆕 Producto no encontrado en el Archivador.")
                with st.form("registro_rapido"):
                    st.write("Registrar como nuevo:")
                    nuevo_nom = st.text_input("Nombre del Producto", value=codigo_leido)
                    nuevo_pre = st.number_input("Precio de Venta", min_value=1.0, step=5.0)
                    nuevo_can = st.number_input("Cantidad Inicial", min_value=1, value=1)
                    
                    if st.form_submit_button("💾 GUARDAR EN ARCHIVADOR"):
                        fecha_hoy = datetime.now(ZONA_HORARIA).strftime("%Y-%m-%d")
                        c.execute("INSERT INTO inventario (producto, cantidad, precio, fecha) VALUES (?,?,?,?)",
                                 (nuevo_nom, nuevo_can, nuevo_pre, fecha_hoy))
                        conn.commit()
                        st.success("¡Producto guardado exitosamente!")
                        st.rerun()
        else:
            st.warning("🔍 Buscando código... Mantén el celular firme y asegúrate de que el código esté plano.")

  


# --- ARCHIVADOR INTEGRAL v5.1: RECTIFICACIÓN DE VARIABLES ---
elif menu == "📂 ARCHIVADOR":
    st.header("📂 Archivador Inteligente v5.1")
    if st.button("♻️ DESHACER ÚLTIMO DOCUMENTO", use_container_width=True):
        borrar_ultimo("documentos")
    st.divider()

           
          
    
    # 1. Entrada de búsqueda
    q = st.text_input("🔍 ¿Qué buscas? (ej: 'glucosa', 'doctor', 'receta')", placeholder="Escribe aquí...")
    
    if q:
        query = f"%{q.lower()}%"
        st.subheader(f"🔎 Resultados para: {q}")
        
        # --- TRADUCCIÓN INTELIGENTE PARA GLUCOSA ---
        terminos_glucosa = ["glucosa", "azucar", "diabetes", "mg", "sangre", "medicion"]
        busca_glucosa = any(t in q.lower() for t in terminos_glucosa)

        col_izq, col_der = st.columns(2)

        with col_izq:
           ### st.markdown("### 🩺 Salud y Citas")
            try:
                # Buscamos en Medicinas y Citas
                res_agenda = pd.read_sql_query("""
                    SELECT '💊 Medicina' as Origen, nombre as Detalle, frecuencia as Info FROM medicinas 
                    WHERE lower(nombre) LIKE ? 
                    UNION
                    SELECT '📅 Cita' as Origen, doctor as Detalle, clinica as Info FROM citas 
                    WHERE lower(doctor) LIKE ? OR lower(clinica) LIKE ?
                """, conn, params=(query, query, query))

                # Lógica para Glucosa
                if busca_glucosa:
                    res_bio = pd.read_sql_query("""
                        SELECT '🩸 Biomonitor' as Origen, valor || ' mg/dL' as Detalle, fecha as Info 
                        FROM glucosa ORDER BY id DESC LIMIT 10
                    """, conn)
                else:
                    res_bio = pd.read_sql_query("""
                        SELECT '🩸 Biomonitor' as Origen, valor || ' mg/dL' as Detalle, fecha as Info 
                        FROM glucosa ORDER BY id DESC LIMIT 10
                    """, conn)
                # Unión de resultados
                todo_salud = pd.concat([res_agenda, res_bio])
                if not todo_salud.empty:
                    st.dataframe(todo_salud, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay coincidencias en Salud.")
            except:
                st.warning("Asegúrate de tener registros en Biomonitor y Agenda.")

        with col_der:
            st.markdown("### 📄 Documentos")
            try:
                res_docs = pd.read_sql_query("""
                    SELECT '🖼️ Escáner' as Origen, tipo as Detalle, fecha as Info FROM archivos 
                    WHERE lower(tipo) LIKE ? OR lower(fecha) LIKE ?
                """, conn, params=(query, query))
                
                if not res_docs.empty:
                    st.table(res_docs)
                else:
                    st.info("No hay documentos guardados.")
            except:
                pass

    st.divider()

    # --- 2. CARPETAS VISUALES (CORREGIDO EL NAMEERROR) ---
    st.subheader("📁 Carpetas")
    cats = {"💊 RECETAS": "Receta Médica", "🧪 LABS": "Resultado Lab", "💰 COTIZ": "Cotización"}
    
    cols = st.columns(3)
    for i, (label, db_name) in enumerate(cats.items()):
        with cols[i]:
            with st.expander(label):
                # Aquí estaba el error, ahora usamos df_c correctamente
                df_c = pd.read_sql_query("SELECT * FROM archivos WHERE tipo = ?", conn, params=(db_name,))
                
                if df_c.empty:
                    st.caption("Vacío")
                else:
                    for idx, row in df_c.iterrows():
                        f1, f2 = st.columns([4, 1])
                        f1.write(f"📄 {row['fecha']}")
                       
    try: pass
    except: pass 


# --- ASISTENTE ANALÍTICO v5.0 ---
elif menu == "🤖 ASISTENTE":
    st.header(f"🤖 Asistente Virtual: {NOMBRE_PROPIETARIO}")
    st.caption(f"📅 Análisis actualizado al: {datetime.now().strftime('%d de %B, %Y')}")

    # --- 1. MONITOR DE ALERTAS ---
    with st.container():
        c_alert1, c_alert2 = st.columns(2)
        with c_alert1:
            # Estado Financiero
            df_fin_asist = pd.read_sql_query("SELECT SUM(monto) as total FROM finanzas", conn)
            balance = df_fin_asist['total'][0] or 0
            st.info(f"💰 **Balance Total:** RD$ {balance:,.2f}")
        
        with c_alert2:
            # Glucosa (Sin filtro de medianoche para que siempre se vea la última)
            df_glu_ult = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1", conn)
            if not df_glu_ult.empty:
                st.success(f"✅ Última glucosa: {df_glu_ult['valor'][0]} mg/dL")
            else:
                st.warning("⚠️ Pendiente registrar glucosa")

    st.divider()

  # --- 2. ANÁLISIS DE DATOS (VISUALIZACIÓN PRO) ---
    st.subheader("📊 Panel de Control Visual")
    
    tab_salud, tab_finanzas = st.tabs(["🩸 Tendencia de Salud", "💰 Flujo de Caja"])

    with tab_salud:
        # Gráfica de Glucosa (Últimos 15 registros)
        df_graf_glu = pd.read_sql_query("""
            SELECT fecha, valor FROM glucosa 
            ORDER BY id DESC LIMIT 15
        """, conn)
        
        if not df_graf_glu.empty:
            # Invertimos para que el tiempo corra de izquierda a derecha
            df_graf_glu = df_graf_glu.iloc[::-1] 
            st.line_chart(df_graf_glu.set_index('fecha'), color="#0047AB")
            st.caption("📈 Variación de tus niveles de azúcar en los últimos registros.")
        else:
            st.info("Aún no hay datos de glucosa para graficar.")

    with tab_finanzas:
        # Gráfica de Gastos por Categoría
        df_graf_fin = pd.read_sql_query("""
            SELECT categoria, SUM(monto) as total FROM finanzas 
            WHERE monto < 0 GROUP BY categoria
        """, conn)
        
        if not df_graf_fin.empty:
            # Convertimos gastos a positivo para que la barra se vea bien
            df_graf_fin['total'] = df_graf_fin['total'].abs()
            st.bar_chart(df_graf_fin.set_index('categoria'), color="#E31E24")
            st.caption("🛒 Distribución de tus gastos por categoría.")
        else:
            st.info("No hay gastos registrados este mes.")

    st.divider()

   

    # --- 3. BÚSQUEDA Y FARMACIAS ---
    col_bus, col_far = st.columns([2, 1])
    with col_bus:
        st.subheader("🔍 Buscador")
        q_asist = st.text_input("¿Qué buscas hoy?", placeholder="Ej: farmacia, mg...")
        if q_asist:
            query = f"%{q_asist.lower()}%"
            res = pd.read_sql_query("""
                SELECT '💰 Gasto' as T, categoria as D, monto as I FROM finanzas WHERE lower(categoria) LIKE ?
                UNION ALL
                SELECT '🩸 Salud' as T, valor || ' mg/dL' as D, fecha as I FROM glucosa WHERE valor LIKE ?
            """, conn, params=(query, query))
            st.dataframe(res, use_container_width=True, hide_index=True)

    with col_far:
        st.subheader("🏥 Farmacias")
        msg = "Hola, soy Luis Rafael. Necesito consultar algo."
        st.markdown(f'<a href="https://wa.me/18495060398?text={msg}" target="_blank" style="text-decoration:none;"><div style="background:#0047AB;color:white;padding:10px;text-align:center;border-radius:10px;margin-bottom:5px;">VALUED</div></a>', unsafe_allow_html=True)
        st.markdown(f'<a href="https://wa.me/18296555546?text={msg}" target="_blank" style="text-decoration:none;"><div style="background:#E31E24;color:white;padding:10px;text-align:center;border-radius:10px;">GBC</div></a>', unsafe_allow_html=True)

    st.divider()
    
            

     # --- 4. ACCIÓN MAESTRA: REPORTE PDF PROFESIONAL v2.0 ---
    if st.button("🚀 GENERAR EXPEDIENTE EJECUTIVO", use_container_width=True, key="btn_pdf_pro"):
        st.info("Diseñando reporte de alta calidad...")
        try:
            pdf = FPDF()
            pdf.add_page()
            
            # --- ENCABEZADO ---
            pdf.set_fill_color(0, 71, 171) # Azul Profesional
            pdf.rect(0, 0, 210, 40, 'F')
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", 'B', 20)
            pdf.cell(190, 15, f"SISTEMA QUEVEDO PRO", ln=True, align='C')
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
            pdf.cell(60, 8, "HORA", 1, 1, 'C', True)
            
            # Datos de Tabla
            pdf.set_font("Arial", '', 10)
            df_pdf_s = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC LIMIT 15", conn)
            for _, r in df_pdf_s.iterrows():
                # Limpieza de caracteres para evitar errores de codificación
                f = str(r['fecha']).encode('latin-1', 'ignore').decode('latin-1')
                v = f"{r['valor']} mg/dL"
                e = str(r['estado']).encode('latin-1', 'ignore').decode('latin-1')
                h = str(r['hora']).encode('latin-1', 'ignore').decode('latin-1')
                
                pdf.cell(40, 8, f, 1)
                pdf.cell(30, 8, v, 1, 0, 'C')
                pdf.cell(60, 8, e, 1)
                pdf.cell(60, 8, h, 1, 1)

            pdf.ln(10)

            # --- SECCIÓN FINANZAS (TABLA DE GASTOS) ---
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, "2. RESUMEN FINANCIERO", ln=True)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            
            # Encabezado de Tabla Finanzas
            pdf.set_fill_color(230, 230, 230)
            pdf.cell(40, 8, "FECHA", 1, 0, 'C', True)
            pdf.cell(100, 8, "CONCEPTO / CATEGORIA", 1, 0, 'C', True)
            pdf.cell(50, 8, "MONTO", 1, 1, 'C', True)
            
            pdf.set_font("Arial", '', 10)
            df_pdf_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC LIMIT 15", conn)
            for _, r in df_pdf_f.iterrows():
                f = str(r['fecha'])
                c = str(r['categoria']).encode('latin-1', 'ignore').decode('latin-1')
                m = f"RD$ {r['monto']:,.2f}"
                
                pdf.cell(40, 8, f, 1)
                pdf.cell(100, 8, c, 1)
                pdf.cell(50, 8, m, 1, 1, 'R')

            # --- PIE DE PÁGINA ---
            pdf.set_y(-30)
            pdf.set_font("Arial", 'I', 8)
            pdf.set_text_color(150, 150, 150)
            pdf.cell(0, 10, f"Reporte generado por Quevedo Pro AI - {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 0, 'C')

            reporte_bin = pdf.output(dest='S').encode('latin-1', 'ignore')
            st.download_button(
                label="📥 DESCARGAR EXPEDIENTE PROFESIONAL", 
                data=reporte_bin, 
                file_name=f"Expediente_{NOMBRE_PROPIETARIO}.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Error en diseño: {e}")    

         


            
    

   
  
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

