import streamlit as st
import numpy as np
import pandas as pd
import numpy_financial as npf
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Simulador Financiero de Vivienda - Medellín",
    page_icon="🏠",
    layout="wide"
)

st.title("🏠 Simulador Financiero de Adquisición de Vivenda")
st.subtitle("Planificación de Cuota Inicial (36 Meses), Crédito Hipotecario (20 Años) y Abonos Inteligentes a Capital")
st.markdown("---")

# Sidebar - Parámetros de Entrada
st.sidebar.header("📌 Parámetros de Entrada")

st.sidebar.subheader("1. Cuota Inicial")
valor_inmueble = st.sidebar.number_input("Valor Comercial del Inmueble ($):", value=250000000, step=5000000, format="%d")
pct_cuota_inicial = st.sidebar.slider("Porcentaje de Cuota Inicial (%):", min_value=10, max_value=50, value=30, step=5) / 100.0
valor_separacion = st.sidebar.number_input("Cuota / Valor de Separación ($):", value=5000000, step=1000000, format="%d")
plazo_cuota_inicial = st.sidebar.number_input("Plazo de Pago Cuota Inicial (Meses):", value=36, step=1)
abonos_extra_construccion = st.sidebar.number_input("Abonos Extraordinarios (Primas/Cesantías) ($):", value=0, step=500000, format="%d")

st.sidebar.subheader("2. Crédito Hipotecario")
es_usada = st.sidebar.checkbox("¿Es Vivienda Usada?", value=False)
plazo_credito_anos = st.sidebar.slider("Plazo Pactado del Crédito (Años):", min_value=5, max_value=30, value=20, step=1)
tasa_ea = st.sidebar.number_input("Tasa de Interés Efectiva Anual (E.A. %):", value=13.35, step=0.1) / 100.0
pct_seguro_vida = 0.0004
pct_seguro_incendio = 0.0003
pct_escrituracion = 0.03
costo_avaluo = 800000 if es_usada else 0
costo_titulos = 350000 if es_usada else 0

st.sidebar.subheader("3. Abonos Inteligentes a Capital")
abono_mensual_extra = st.sidebar.number_input("Abono Adicional Mensual a Capital ($):", value=200000, step=50000, format="%d")
abono_anual_extra = st.sidebar.number_input("Abono Extraordinario Anual ($):", value=3000000, step=500000, format="%d")

# Cálculos PARTE I: Cuota Inicial
monto_cuota_inicial = valor_inmueble * pct_cuota_inicial
saldo_cuota_inicial = max(0, monto_cuota_inicial - valor_separacion - abonos_extra_construccion)
cuota_mensual_inicial = saldo_cuota_inicial / plazo_cuota_inicial if plazo_cuota_inicial > 0 else 0

# Cálculos PARTE II: Crédito Hipotecario
monto_credito = valor_inmueble - monto_cuota_inicial
tasa_em = (1 + tasa_ea)**(1/12) - 1
plazo_meses = plazo_credito_anos * 12

# Cuota ordinaria fija (PMT)
if tasa_em > 0:
    cuota_ordinaria_capital_int = npf.pmt(tasa_em, plazo_meses, -monto_credito)
else:
    cuota_ordinaria_capital_int = monto_credito / plazo_meses

seguros_iniciales = (monto_credito * pct_seguro_vida) + (valor_inmueble * pct_seguro_incendio)
cuota_total_base = cuota_ordinaria_capital_int + seguros_iniciales

gastos_escrituracion = valor_inmueble * pct_escrituracion
total_gastos_cierre = gastos_escrituracion + costo_avaluo + costo_titulos

# Generar Tabla de Amortización Dinámica
filas = []
saldo_actual = monto_credito

for mes in range(1, plazo_meses + 1):
    if saldo_actual <= 0:
        break
    
    saldo_inicial = saldo_actual
    interes_mes = saldo_inicial * tasa_em
    
    # Abono adicional
    abono_extra_mes = abono_mensual_extra
    if mes % 12 == 0:
        abono_extra_mes += abono_anual_extra
        
    capital_regular = min(saldo_inicial, cuota_ordinaria_capital_int - interes_mes)
    capital_total_mes = capital_regular + abono_extra_mes
    
    if capital_total_mes > saldo_inicial:
        abono_extra_mes = max(0, saldo_inicial - capital_regular)
        capital_total_mes = saldo_inicial
        
    seguros_mes = (saldo_inicial * pct_seguro_vida) + (valor_inmueble * pct_seguro_incendio)
    pago_total_mes = capital_regular + interes_mes + abono_extra_mes + seguros_mes
    saldo_final = max(0, saldo_inicial - capital_total_mes)
    
    filas.append({
        "Mes": mes,
        "Saldo Inicial": saldo_inicial,
        "Capital Regular": capital_regular,
        "Intereses": interes_mes,
        "Abono Extraordinario": abono_extra_mes,
        "Seguros": seguros_mes,
        "Pago Total Mes": pago_total_mes,
        "Saldo Final": saldo_final
    })
    
    saldo_actual = saldo_final

df_amort = pd.DataFrame(filas)

meses_reales = len(df_amort)
anos_reales = meses_reales / 12.0
total_intereses_pagados = df_amort["Intereses"].sum() if not df_amort.empty else 0

# Visualización de KPIs Principales
col1, col2, col3, col4 = st.columns(4)
col1.metric("Cuota Constructora (36M)", f"${cuota_mensual_inicial:,.0f} COP")
col2.metric("Cuota Banco Base (Mes 1)", f"${cuota_total_base:,.0f} COP")
col3.metric("Plazo Real de Pago", f"{meses_reales} Meses ({anos_reales:.1f} Años)")
col4.metric("Total Intereses a Pagados", f"${total_intereses_pagados:,.0f} COP")

st.markdown("---")

# Pestañas de Análisis
tab1, tab2, tab3 = st.tabs(["📊 Gráfica de Amortización", "📑 Resumen de Gastos", "📋 Tabla de Amortización Completa"])

with tab1:
    st.subheader("Evolución del Saldo Pendiente del Crédito")
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df_amort["Mes"], df_amort["Saldo Final"], color="#1F4E78", linewidth=2.5, label="Saldo de la Deuda ($)")
    ax.fill_between(df_amort["Mes"], df_amort["Saldo Final"], color="#D9E1F2", alpha=0.5)
    ax.set_xlabel("Meses")
    ax.set_ylabel("Saldo Pendiente ($)")
    ax.set_title("Reducción del Plazo por Efecto de Abonos Inteligentes a Capital")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    st.pyplot(fig)

with tab2:
    st.subheader("Resumen General de la Operación")
    st.write(f"**Valor del Inmueble:** ${valor_inmueble:,.0f} COP")
    st.write(f"**Cuota Inicial ({pct_cuota_inicial*100:.0f}%):** ${monto_cuota_inicial:,.0f} COP")
    st.write(f"**Monto Financiar con Banco:** ${monto_credito:,.0f} COP")
    st.write(f"**Gastos de Cierre Iniciales (Escrituración/Avalúo):** ${total_gastos_cierre:,.0f} COP")

with tab3:
    st.subheader("Detalle Mes a Mes")
    st.dataframe(df_amort.style.format({
        "Saldo Inicial": "${:,.0f}",
        "Capital Regular": "${:,.0f}",
        "Intereses": "${:,.0f}",
        "Abono Extraordinario": "${:,.0f}",
        "Seguros": "${:,.0f}",
        "Pago Total Mes": "${:,.0f}",
        "Saldo Final": "${:,.0f}"
    }))
