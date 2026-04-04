import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime
import pytz
from sklearn.linear_model import LinearRegression
import numpy as np

def iniciar_db():
    # Nota el guion bajo en check_same_thread
    conn = sqlite3.connect("miapp.db", check_same_thread=False)
    return conn

# Usar la función para crear la conexión
conn = iniciar_db()
c = conn.cursor()

# Crear tabla si no existe
c.execute('CREATE TABLE IF NOT EXISTS inventario (item TEXT, cantidad INTEGER, fecha TEXT)')
conn.commit()

st.setpageconfig(page_title="App Finanzas & Salud Quevedo", layout="wide")
st.title("📊💉 Dashboard Finanzas & Salud Inteligente")

tab1, tab2, tab3 = st.tabs(["💰 Finanzas", "🩺 Salud", "🧠 IA Predictiva"])


with tab1:
    st.subheader("Registro Financiero")
    with st.form("formfinanzas", clearon_submit=True):
        tipo = st.selectbox("Tipo", ["GASTO", "INGRESO"])
        categoria = st.text_input("Categoría")
        detalle = st.text_input("Detalle")
        monto = st.numberinput("Monto RD$", minvalue=0.0, step=1.0)
        if st.formsubmitbutton("Registrar"):
            ahora = datetime.now()
            monto_final = -abs(monto) if tipo == "GASTO" else abs(monto)
            conn.execute("INSERT INTO finanzas (fecha,tipo,categoria,detalle,monto) VALUES (?,?,?,?,?)",
                         (ahora.strftime("%d/%m/%Y %H:%M"), tipo, categoria.upper(), detalle.upper(), monto_final))
            conn.commit()
            st.success("✅ Registro guardado")
    dff = pd.readsql_query("SELECT * FROM finanzas ORDER BY id DESC", conn)
    if not df_f.empty:
        st.dataframe(dff, usecontainer_width=True)
        fig = px.bar(df_f, x="categoria", y="monto", color="tipo", title="Movimientos por Categoría")
        st.plotlychart(fig, usecontainer_width=True)

with tab2:
    st.subheader("Gestor de Salud")
    # Glucosa
    with st.form("formglucosa", clearon_submit=True):
        valor = st.numberinput("Glucosa mg/dL", minvalue=0, max_value=500)
        momento = st.selectbox("Momento", ["Ayunas", "Post-Desayuno", "Antes Cena", "Post-Cena"])
        notas = st.text_area("Notas")
        if st.formsubmitbutton("Guardar Glucosa"):
            zona = pytz.timezone('America/Santo_Domingo')
            ahora = datetime.now(zona)
            conn.execute("INSERT INTO glucosa (fecha,hora,momento,valor,notas) VALUES (?,?,?,?,?)",
                         (ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), momento, valor, notas))
            conn.commit()
            st.success("✅ Glucosa registrada")
    dfg = pd.readsql_query("SELECT * FROM glucosa ORDER BY id DESC", conn)
    if not df_g.empty:
        st.dataframe(dfg, usecontainer_width=True)
        fig = px.line(df_g, x="fecha", y="valor", title="Evolución Glucosa", markers=True)
        st.plotlychart(fig, usecontainer_width=True)

with tab3:
    st.subheader("Motor IA Predictivo")

    # Predicción Financiera
    dff = pd.readsql_query("SELECT * FROM finanzas ORDER BY id ASC", conn)
    if not df_f.empty:
        st.write("### 📈 Predicción Financiera")
        X = np.arange(len(df_f)).reshape(-1,1)
        y = df_f["monto"].values
        model = LinearRegression().fit(X,y)
        futuro = model.predict([[len(df_f)+1]])
        st.info(f"🔮 Consejo de Ahorro: Se estima que tu próximo movimiento será RD$ {futuro[0]:,.2f}")

    # Alertas de Salud
    dfg = pd.readsql_query("SELECT * FROM glucosa ORDER BY id ASC", conn)
    if not df_g.empty:
        st.write("### ❤️ Alertas de Salud")
        ultimo = df_g["valor"].iloc[-1]
        if ultimo < 70:
            st.error("⚠️ Alerta: Glucosa muy baja")
        elif ultimo > 180:
            st.warning("⚠️ Alerta: Glucosa elevada")
        else:
            st.success("✅ Glucosa en rango óptimo")
