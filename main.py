import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px
from fpdf import FPDF
from datetime import datetime
import pytz
import numpy as np
import unicodedata
from PIL import Image
import io
from streamlit_gsheets import GSheetsConnection
# 1. CONFIGURACIÓN E INTERFAZ DE ALTO NIVEL
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide", page_icon="💎")
# --- CONFIGURACIÓN DE IDENTIDAD MAESTRA ---
NOMBRE_PROPIETARIO = "LUIS RAFAEL QUEVEDO"
UBICACION_SISTEMA = "Santo Domingo, Rep. Dom."

# Función para limpiar acentos y evitar errores en el PDF (Seguro de caracteres)
def limpiar_texto(texto):
    if not texto: return ""
    return "".join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn')

# --- SISTEMA DE SEGURIDAD (LOGIN) ---
def verificar_acceso():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        st.markdown("<h1 style='text-align: center; color: #4CAF50;'>💎 SISTEMA QUEVEDO</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>🔐 Acceso Privado - Luis Rafael Quevedo</p>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.button("DESBLOQUEAR SISTEMA"):
                if u == "Amin" and p == "1234":
                    st.session_state["autenticado"] = True
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas")
        return False
    return True

if verificar_acceso():
    # Directorios y Base de Datos
    if not os.path.exists("archivador_quevedo"):
        os.makedirs("archivador_quevedo")

    def iniciar_db():
        conn = sqlite3.connect("sistema_quevedo_integral.db", check_same_thread=False)
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, categoria TEXT, monto REAL, fecha TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS presupuesto (id INTEGER PRIMARY KEY AUTOINCREMENT, limite REAL)')
        c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY AUTOINCREMENT, valor INTEGER, fecha TEXT, hora TEXT, estado TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS medicinas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor TEXT, fecha TEXT, hora TEXT)')
        conn.commit()
        return conn

    conn = iniciar_db()
    c = conn.cursor()

    # --- FUNCIÓN: GENERADOR REPORTE MAESTRO PDF (VERSIÓN ANTIBALAS) ---
    def generar_reporte_maestro_pdf():
        try:
            pdf = FPDF()
            pdf.add_page()
            # Cambiamos a Courier para mayor compatibilidad en la Nube
            pdf.set_font("Courier", 'B', 16)
            
            titulo = limpiar_texto("REPORTE MAESTRO - SISTEMA QUEVEDO")
            pdf.cell(0, 10, titulo, ln=True, align='C')
            pdf.ln(5)

            def agregar_seccion(titulo_sec, query, columnas):
                pdf.set_font("Courier", 'B', 12)
                pdf.set_fill_color(200, 200, 200)
                pdf.cell(0, 10, limpiar_texto(titulo_sec), ln=True, fill=True)
                pdf.ln(2)
                
                try:
                    df = pd.read_sql_query(query, conn)
                    if not df.empty:
                        pdf.set_font("Courier", 'B', 10)
                        # Cabeceras
                        for col in columnas:
                            pdf.cell(47, 8, limpiar_texto(col), 1)
                        pdf.ln()
                        # Datos: Forzamos el encode aquí mismo
                        pdf.set_font("Courier", size=9)
                        for _, row in df.iterrows():
                            for val in row:
                                # LA CLAVE: Limpiamos y forzamos el string
                                texto_celda = limpiar_texto(str(val))
                                pdf.cell(47, 7, texto_celda, 1)
                            pdf.ln()
                    else:
                        pdf.cell(0, 8, "Sin datos.", ln=True)
                except:
                    pdf.cell(0, 8, "Error en seccion.", ln=True)
                pdf.ln(5)

            # 1. Finanzas
            df_f = pd.read_sql_query("SELECT SUM(monto) as bal FROM finanzas", conn)
            bal = df_f['bal'].iloc[0] if df_f['bal'].iloc[0] else 0.0
            pdf.set_font("Courier", 'B', 11)
            pdf.cell(0, 10, f"BALANCE TOTAL: RD$ {bal:,.2f}", ln=True)
            
            agregar_seccion("FINANZAS", "SELECT fecha, categoria, monto FROM finanzas ORDER BY id DESC LIMIT 10", ["Fecha", "Concepto", "Monto"])
            agregar_seccion("GLUCOSA", "SELECT fecha, hora, valor, estado FROM glucosa ORDER BY id DESC LIMIT 10", ["Fecha", "Hora", "Valor", "Estado"])
            agregar_seccion("MEDICINAS", "SELECT nombre, horario FROM medicinas", ["Medicina", "Horario"])
            agregar_seccion("CITAS", "SELECT doctor, fecha FROM citas", ["Doctor", "Fecha"])

            # Cerramos el PDF internamente antes de pedir el output
            pdf.close()
            # El secreto: output() sin parámetros para obtener el string y luego codificar
            cuerpo_pdf = pdf.output(dest='S')
            return cuerpo_pdf.encode('latin-1', 'replace')
            
        except Exception as e:
            st.error(f"Error interno del PDF: {e}")
            return None
    
    # --- FUNCIÓN GENERAR PDF SALUD ---
    def generar_pdf_salud(df_g, df_m):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, limpiar_texto("REPORTE MEDICO - LUIS RAFAEL QUEVEDO"), ln=True, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12); pdf.cell(200, 10, "1. MEDICAMENTOS ACTIVOS:"); pdf.ln()
        pdf.set_font("Arial", size=10)
        for _, r in df_m.iterrows():
            pdf.cell(200, 8, limpiar_texto(f"- {r['nombre']} ({r['horario']})"), ln=True)
        pdf.ln(5); pdf.set_font("Arial", 'B', 12); pdf.cell(200, 10, "2. GLUCOSA:"); pdf.ln()
        for _, r in df_g.tail(10).iterrows():
            pdf.cell(200, 8, f"{r['fecha']} {r['hora']}: {r['valor']} mg/dL", ln=True)
        nombre = f"Salud_{datetime.now().strftime('%Y%m%d')}.pdf"
        pdf.output(os.path.join("archivador_quevedo", nombre))
        return nombre

    # DISEÑO VISUAL CSS
    st.markdown("""
        <style>
        .main { background-color: #0e1117; }
        .stButton>button { width: 100%; border-radius: 12px; background-color: #1b5e20; color: white; height: 3.5em; font-weight: bold; }
        .resumen-card { background: linear-gradient(135deg, #1e2130 0%, #1b5e20 100%); padding: 15px; border-radius: 15px; border: 1px solid #4CAF50; text-align: center; }
        .semaforo-rojo { background-color: #c62828; padding: 20px; border-radius: 15px; color: white; animation: pulse 2s infinite; text-align: center; border: 2px solid white; }
        @keyframes pulse { 0% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0.7);} 70% {box-shadow: 0 0 0 20px rgba(198, 40, 40, 0);} 100% {box-shadow: 0 0 0 0px rgba(198, 40, 40, 0);} }
        </style>
        """, unsafe_allow_html=True)

    contactos_data = {"Nombre": ["Mi Hijo", "Mi Hija", "Franklin", "Hermanito", "Dorka", "Rosa", "Pedro"],
                      "Telefono": ["18292061693", "18292581449", "16463746377", "14077975432", "18298811692", "18293800425", "18097100995"]}

    # NAVEGACIÓN
    st.sidebar.title("💎 SISTEMA QUEVEDO")
    
    # MEJORA: RECORDATORIO DE CITAS EN SIDEBAR
    df_c_prox = pd.read_sql_query("SELECT doctor, fecha FROM citas ORDER BY fecha ASC LIMIT 1", conn)
    if not df_c_prox.empty:
        st.sidebar.warning(f"🔔 PRÓXIMA CITA:\n{df_c_prox['doctor'][0]} - {df_c_prox['fecha'][0]}")

    with st.sidebar:
        st.subheader("🚀 Reportes Globales")
        if st.button("📊 GENERAR REPORTE MAESTRO"):
            pdf_data = generar_reporte_maestro_pdf()
            st.download_button("📥 Descargar Reporte", pdf_data, f"MAESTRO_{datetime.now().strftime('%Y%m%d')}.pdf", "application/pdf")
        st.divider()

    menu = st.sidebar.radio("MODULOS", ["🏠 INICIO (RESUMEN)", "💰 FINANZAS IA", "🩺 BIOMONITOR", "💊 AGENDA MEDICA", "📸 ESCANER", "📂 ARCHIVADOR", "🤖 ASISTENTE"])

    # --- SECCIÓN INICIO: RESUMEN EJECUTIVO ---
    if menu == "🏠 INICIO (RESUMEN)":
        st.header("📊 Resumen Ejecutivo del Sistema")
        c1, c2, c3 = st.columns(3)
        
        df_fin = pd.read_sql_query("SELECT SUM(monto) as total FROM finanzas", conn)
        df_glu = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1", conn)
        df_med = pd.read_sql_query("SELECT nombre FROM medicinas LIMIT 1", conn)

        with c1: 
            st.markdown('<div class="resumen-card">', unsafe_allow_html=True); st.metric("💰 BALANCE NETO", f"RD$ {df_fin['total'][0] or 0:,.2f}"); st.markdown('</div>', unsafe_allow_html=True)
        with c2: 
            st.markdown('<div class="resumen-card">', unsafe_allow_html=True); st.metric("🩺 ÚLTIMA GLUCOSA", f"{df_glu['valor'][0] if not df_glu.empty else 'N/A'} mg/dL"); st.markdown('</div>', unsafe_allow_html=True)
        with c3: 
            st.markdown('<div class="resumen-card">', unsafe_allow_html=True); st.metric("💊 MEDICINA ACTUAL", f"{df_med['nombre'][0] if not df_med.empty else 'Ninguna'}"); st.markdown('</div>', unsafe_allow_html=True)

    # --- SECCIÓN 1: FINANZAS IA ---
    elif menu == "💰 FINANZAS IA":
        st.header("💰 Gestión de Finanzas - SISTEMA QUEVEDO")
        
        # 1. ENTRADA DE DATOS
        with st.expander("➕ Registrar Nuevo Movimiento", expanded=False):
            with st.form("nuevo_gasto_quevedo"):
                col_a, col_b = st.columns(2)
                with col_a:
                    categoria = st.selectbox("Categoría", ["Alimentos", "Salud", "Servicios", "Transporte", "Hogar", "Otros"])
                with col_b:
                    monto = st.number_input("Monto en RD$", min_value=0.0, step=100.0)
                
                detalles = st.text_input("Detalle (ej: Farmacia, Supermercado, Luz)")
                boton_guardar = st.form_submit_button("Guardar en Base de Datos")
                
                if boton_guardar:
                    if monto > 0:
                        fecha_hoy = datetime.now().strftime("%d/%m/%Y")
                        # Insertamos respetando su lógica de negocio
                        c.execute("INSERT INTO finanzas (fecha, categoria, monto) VALUES (?,?,?)", 
                                  (f"{categoria}: {detalles}" if detalles else categoria, fecha_hoy, monto))
                        conn.commit()
                        st.success(f"✅ Registrado: RD$ {monto:,.2f}")
                        st.rerun()
                    else:
                        st.error("Error: El monto debe ser mayor a cero.")

        # 2. TABLA DE HISTORIAL (DISEÑO PROFESIONAL)
        st.subheader("📋 Historial de Movimientos")
        df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", conn)
        
        if not df_f.empty:
            # Mostramos la tabla limpia para lectura fácil
            st.dataframe(df_f[['fecha', 'categoria', 'monto']], 
                         column_config={
                             "fecha": "Fecha",
                             "categoria": "Concepto",
                             "monto": st.column_config.NumberColumn("Monto (RD$)", format="RD$ %.2f")
                         }, 
                         use_container_width=True, 
                         hide_index=True)
            
            # 3. EL BORRADOR MAESTRO (Para rectificar errores)
            st.markdown("---")
            with st.expander("🗑️ ZONA DE CORRECCIÓN (Eliminar Registro)"):
                st.write("Seleccione el dato erróneo para sacarlo del sistema:")
                
                opciones_borrar = {f"{r['fecha']} | {r['categoria']} | RD$ {r['monto']}": r['id'] 
                                   for _, r in df_f.iterrows()}
                
                seleccion = st.selectbox("Movimiento a eliminar:", 
                                         options=list(opciones_borrar.keys()), 
                                         key="del_fin_quevedo")
                
                if st.button("Confirmar Borrado Permanente", type="primary"):
                    c.execute("DELETE FROM finanzas WHERE id=?", (opciones_borrar[seleccion],))
                    conn.commit()
                    st.success("Registro eliminado satisfactoriamente.")
                    st.rerun()
        else:
            st.info("No hay datos financieros registrados.")

    # --- SECCIÓN 2: BIOMONITOR ---
    elif menu == "🩺 BIOMONITOR":
        st.header("🩺 Monitoreo de Glucosa")
        
        # 1. Entrada de datos
        val_g = st.number_input("Ingresar nivel actual (mg/dL):", min_value=0, key="input_glucosa")
        
        # Alerta de Pánico
        if val_g > 160:
            st.markdown(f'<div class="semaforo-rojo">🚨 ALERTA CRÍTICA: {val_g} mg/dL</div>', unsafe_allow_html=True)
            st.subheader("🆘 TABLA DE AVISO RÁPIDO")
            for i in range(len(contactos_data["Nombre"])):
                n, t = contactos_data["Nombre"][i], contactos_data["Telefono"][i]
                msg = f"Emergencia: Luis tiene la glucosa en {val_g}. Favor contactar."
                url = f"https://api.whatsapp.com/send?phone={t}&text={msg.replace(' ', '%20')}"
                c1, c2 = st.columns([3,1])
                c1.write(f"👤 **{n}**")
                c2.link_button(f"📲 AVISAR", url)
            st.divider()

        # 2. Botón de Guardar con Refresco Automático
        if st.button("💾 GUARDAR TOMA ACTUAL"):
            if val_g > 0:
                tz = pytz.timezone('America/Santo_Domingo')
                ahora = datetime.now(tz)
                est = "NORMAL" if val_g <= 140 else "ALERTA" if val_g <= 160 else "CRITICO"
                
                conn.execute("INSERT INTO glucosa (valor, fecha, hora, estado) VALUES (?,?,?,?)", 
                             (val_g, ahora.strftime("%d/%m/%y"), ahora.strftime("%I:%M %p"), est))
                conn.commit()
                st.success(f"✅ Registrado: {val_g} mg/dL")
                st.rerun()
            else:
                st.warning("Por favor, ingrese un valor válido.")

        st.markdown("---")
        
        # 3. Visualización en Tiempo Real (Historial)
        st.subheader("📊 Historial de Registros")
        df_g = pd.read_sql_query("SELECT fecha as Fecha, hora as Hora, valor as Valor, estado as Estado FROM glucosa ORDER BY id DESC", conn)
        
        if not df_g.empty:
            df_grafico = df_g.iloc[::-1] 
            fig = px.line(df_grafico, x="Fecha", y="Valor", title="Evolución de su Glucosa", markers=True)
            fig.update_traces(line_color='#4CAF50')
            st.plotly_chart(fig, use_container_width=True)
            
            st.write("📋 **Últimas mediciones:**")
            st.dataframe(df_g.head(15), use_container_width=True)
            
            with st.expander("🗑️ Zona de Peligro"):
                if st.button("BORRAR TODO EL HISTORIAL DE GLUCOSA"):
                    conn.execute("DELETE FROM glucosa")
                    conn.commit()
                    st.rerun()



    else:
            st.info("Aún no hay registros de glucosa. Ingrese el primero arriba.")    

   # --- SECCIÓN: ESCANER (Línea 317 - REPARADA) ---
elif menu == "📸 ESCANER":
            st.header("📸 Escáner de Documentos Quevedo Pro")
            st.markdown("---")
            st.info("Paso a paso: Este módulo procesará tus recetas y códigos QR.")
            archivo = st.file_uploader("Sube una imagen para escanear", type=['png', 'jpg', 'jpeg'])
            if archivo:
                img = Image.open(archivo)
                st.image(img, caption="Documento listo para procesar", use_container_width=True)
                st.success("✅ Imagen cargada. Procesando datos...")

        # --- SECCIÓN: ARCHIVADOR ---
elif menu == "📂 ARCHIVADOR":
            st.header("📂 Archivador de Documentos")
            st.markdown("---")
            st.write(f"Carpeta de destino: `archivador_quevedo/`")
            # Listar archivos locales si existen
            archivos_locales = os.listdir("archivador_quevedo")
            if archivos_locales:
                st.write("### Documentos Guardados:")
                for arc in archivos_locales:
                    st.text(f"📄 {arc}")
            else:
                st.info("El archivador local está vacío.")

        # --- SECCIÓN: ASISTENTE (CONEXIÓN SEGURA) ---
elif menu == "🤖 ASISTENTE":
            st.header("🤖 Asistente Inteligente")
            st.markdown("---")
            st.warning("⚠️ Conexión con Google Sheets en mantenimiento. Usando base de datos local.")
            
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                if st.button("📧 ENVIAR REPORTE A GMAIL"):
                    st.info("Generando reporte...")
            with col_a2:
                if st.button("📲 COTIZAR EN FARMACIAS"):
                    st.success("Abriendo comunicación con farmacias...")

# =========================================================
# CRÉDITOS FINALES (FUERA DE LOS MÓDULOS)
# =========================================================
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.markdown(
    f"""
    <div style="text-align: center; padding: 20px; border: 2px solid #4CAF50; border-radius: 15px; background-color: #f9f9f9;">
        <h3 style="color: #1b5e20;">💎 SISTEMA QUEVEDO PRO v2.5</h3>
        <p><b>Propiedad de:</b> {NOMBRE_PROPIETARIO}</p>
        <p><i>"Paso a paso, primero una cosa y luego la otra."</i></p>
    </div>
    """, 
    unsafe_allow_html=True
)     
