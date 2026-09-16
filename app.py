"""
LAS AMALIAS — CRM
App en Streamlit conectada a Supabase (PostgreSQL).

Ejecutar localmente:
    streamlit run app.py

Requiere un archivo .streamlit/secrets.toml (ver secrets_example.toml)
con SUPABASE_URL, SUPABASE_KEY y credenciales de acceso a la app.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
from supabase import create_client

st.set_page_config(page_title="Las Amalias — CRM", page_icon="🌱", layout="wide")

# =====================================================================
# CONEXIÓN A SUPABASE
# =====================================================================
@st.cache_resource
def get_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


supabase = get_client()


def fetch(table: str, select: str = "*", order_by: str | None = None, desc: bool = True) -> pd.DataFrame:
    query = supabase.table(table).select(select)
    if order_by:
        query = query.order(order_by, desc=desc)
    res = query.execute()
    return pd.DataFrame(res.data)


def clear_cache():
    st.cache_data.clear()


@st.cache_data(ttl=30)
def cached_fetch(table: str, select: str = "*", order_by: str | None = None, desc: bool = True) -> pd.DataFrame:
    return fetch(table, select, order_by, desc)


# =====================================================================
# LOGIN SIMPLE
# =====================================================================
def check_login():
    if st.session_state.get("auth_ok"):
        return True

    st.title("🌱 Las Amalias — CRM")
    st.subheader("Iniciar sesión")
    users = st.secrets.get("APP_USERS", {})
    with st.form("login_form"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Ingresar")
    if submitted:
        if u in users and users[u] == p:
            st.session_state["auth_ok"] = True
            st.session_state["auth_user"] = u
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos.")
    return False


if not check_login():
    st.stop()

# =====================================================================
# NAVEGACIÓN
# =====================================================================
st.sidebar.title("🌱 Las Amalias")
st.sidebar.caption(f"Sesión: {st.session_state.get('auth_user','')}")
page = st.sidebar.radio(
    "Navegación",
    ["📊 Dashboard", "👥 Clientes", "📞 Comunicaciones", "🧾 Productos",
     "💰 Ventas", "📦 Compras", "📈 Proyecciones", "🤝 Postventa"],
)
if st.sidebar.button("Cerrar sesión"):
    st.session_state.clear()
    st.rerun()

st.sidebar.divider()
st.sidebar.caption("Catálogos de referencia:")
st.sidebar.markdown("- [Kioshi Stone / Legacy / Böhm](https://claudio391.github.io/las-amalias-web/)")


def clientes_options():
    df = cached_fetch("clientes", "id, empresa")
    if df.empty:
        return {}, []
    opts = dict(zip(df["empresa"] + " · " + df["id"].str[:8], df["id"]))
    return opts, df


def productos_options():
    df = cached_fetch("productos", "id, nombre, marca, precio_unitario")
    if df.empty:
        return {}, df
    opts = dict(zip(df["marca"] + " — " + df["nombre"], df["id"]))
    return opts, df


# =====================================================================
# DASHBOARD
# =====================================================================
if page == "📊 Dashboard":
    st.title("📊 Panel General")

    clientes = cached_fetch("clientes")
    comunicaciones = cached_fetch("comunicaciones")
    ventas = cached_fetch("ventas")
    proyecciones = cached_fetch("proyecciones_ventas")
    postventa = cached_fetch("postventa")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Clientes totales", len(clientes))
    c2.metric("Clientes activos", int((clientes["estado"] == "Activo").sum()) if not clientes.empty else 0)
    c3.metric("Prospectos", int((clientes["estado"] == "Prospecto").sum()) if not clientes.empty else 0)
    pend = int((comunicaciones["estado"] == "Pendiente").sum()) if not comunicaciones.empty else 0
    c4.metric("Seguimientos pendientes", pend)

    c5, c6, c7 = st.columns(3)
    total_ventas = ventas["monto_total"].sum() if not ventas.empty else 0
    c5.metric("Ventas totales (USD)", f"{total_ventas:,.2f}")
    proy_total = proyecciones["monto_proyectado"].sum() if not proyecciones.empty else 0
    real_total = proyecciones["monto_real"].sum() if not proyecciones.empty else 0
    c6.metric("Proyectado (USD)", f"{proy_total:,.2f}")
    c7.metric("Real vs proyectado", f"{real_total:,.2f}", delta=f"{real_total - proy_total:,.2f}")

    st.divider()
    colA, colB = st.columns(2)

    with colA:
        st.subheader("Ventas por mes")
        if not ventas.empty:
            v = ventas.copy()
            v["mes"] = pd.to_datetime(v["fecha_venta"]).dt.to_period("M").astype(str)
            g = v.groupby("mes")["monto_total"].sum().reset_index()
            fig = px.bar(g, x="mes", y="monto_total", labels={"monto_total": "USD", "mes": "Mes"})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Todavía no hay ventas cargadas.")

    with colB:
        st.subheader("Proyectado vs Real por mes")
        if not proyecciones.empty:
            p = proyecciones.copy()
            p["mes"] = pd.to_datetime(p["mes"]).dt.to_period("M").astype(str)
            g = p.groupby("mes")[["monto_proyectado", "monto_real"]].sum().reset_index()
            g = g.melt(id_vars="mes", value_vars=["monto_proyectado", "monto_real"],
                       var_name="tipo", value_name="usd")
            fig = px.bar(g, x="mes", y="usd", color="tipo", barmode="group")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Todavía no hay proyecciones cargadas.")

    st.subheader("Postventa pendiente de seguimiento")
    if not postventa.empty:
        pendientes = postventa[postventa["estado"] == "En seguimiento"]
        st.dataframe(pendientes, use_container_width=True, hide_index=True)
    else:
        st.info("No hay registros de postventa todavía.")

# =====================================================================
# CLIENTES
# =====================================================================
elif page == "👥 Clientes":
    st.title("👥 Clientes")

    tab1, tab2 = st.tabs(["Listado", "Agregar / Editar"])

    with tab1:
        df = cached_fetch("clientes", order_by="fecha_alta")
        filtro = st.text_input("Buscar por empresa o contacto")
        if filtro and not df.empty:
            df = df[df["empresa"].str.contains(filtro, case=False, na=False) |
                     df["contacto_principal"].str.contains(filtro, case=False, na=False)]
        st.dataframe(df, use_container_width=True, hide_index=True)

    with tab2:
        opts, df_all = clientes_options()
        modo = st.radio("Acción", ["Nuevo cliente", "Editar existente"], horizontal=True)
        registro = {}
        cliente_id = None
        if modo == "Editar existente" and opts:
            sel = st.selectbox("Seleccioná el cliente", list(opts.keys()))
            cliente_id = opts[sel]
            registro = df_all[df_all["id"] == cliente_id].iloc[0].to_dict() if not df_all.empty else {}
            full = fetch("clientes")
            full_row = full[full["id"] == cliente_id].iloc[0].to_dict()
            registro.update(full_row)

        with st.form("form_cliente", clear_on_submit=(modo == "Nuevo cliente")):
            empresa = st.text_input("Empresa / Productor *", value=registro.get("empresa", ""))
            contacto = st.text_input("Contacto principal", value=registro.get("contacto_principal", "") or "")
            telefono = st.text_input("Teléfono", value=registro.get("telefono", "") or "")
            email = st.text_input("Email", value=registro.get("email", "") or "")
            colc1, colc2 = st.columns(2)
            ciudad = colc1.text_input("Ciudad", value=registro.get("ciudad", "") or "")
            provincia = colc2.text_input("Provincia", value=registro.get("provincia", "") or "")
            producto_interes = st.text_input("Producto de interés", value=registro.get("producto_interes", "") or "")
            estado = st.selectbox("Estado", ["Prospecto", "Activo", "Inactivo"],
                                   index=["Prospecto", "Activo", "Inactivo"].index(registro.get("estado", "Prospecto")))
            responsable = st.text_input("Responsable comercial", value=registro.get("responsable_comercial", "") or "")
            notas = st.text_area("Notas", value=registro.get("notas", "") or "")
            colb1, colb2 = st.columns(2)
            guardar = colb1.form_submit_button("💾 Guardar")
            eliminar = colb2.form_submit_button("🗑️ Eliminar") if modo == "Editar existente" else False

            if guardar:
                if not empresa:
                    st.error("El campo Empresa es obligatorio.")
                else:
                    payload = {
                        "empresa": empresa, "contacto_principal": contacto, "telefono": telefono,
                        "email": email, "ciudad": ciudad, "provincia": provincia,
                        "producto_interes": producto_interes, "estado": estado,
                        "responsable_comercial": responsable, "notas": notas,
                    }
                    if modo == "Nuevo cliente":
                        payload["fecha_alta"] = str(date.today())
                        supabase.table("clientes").insert(payload).execute()
                        st.success("Cliente creado.")
                    else:
                        supabase.table("clientes").update(payload).eq("id", cliente_id).execute()
                        st.success("Cliente actualizado.")
                    clear_cache()
                    st.rerun()

            if eliminar and cliente_id:
                supabase.table("clientes").delete().eq("id", cliente_id).execute()
                st.success("Cliente eliminado.")
                clear_cache()
                st.rerun()

# =====================================================================
# COMUNICACIONES
# =====================================================================
elif page == "📞 Comunicaciones":
    st.title("📞 Seguimiento de Comunicaciones")
    opts, _ = clientes_options()

    tab1, tab2 = st.tabs(["Listado", "Nuevo registro"])
    with tab1:
        df = fetch("comunicaciones", "*, clientes(empresa)", order_by="fecha", desc=True)
        if not df.empty and "clientes" in df.columns:
            df["cliente"] = df["clientes"].apply(lambda x: x.get("empresa") if isinstance(x, dict) else None)
            df = df.drop(columns=["clientes", "cliente_id"])
        st.dataframe(df, use_container_width=True, hide_index=True)

    with tab2:
        if not opts:
            st.warning("Primero cargá al menos un cliente.")
        else:
            with st.form("form_comunicacion", clear_on_submit=True):
                sel = st.selectbox("Cliente", list(opts.keys()))
                fecha = st.date_input("Fecha", value=date.today())
                canal = st.selectbox("Canal", ["Llamada telefónica", "Email", "WhatsApp", "Visita presencial", "Otro"])
                resumen = st.text_area("Resumen de la conversación")
                proxima_accion = st.text_input("Próxima acción")
                fecha_prox = st.date_input("Fecha próximo seguimiento", value=None)
                responsable = st.text_input("Responsable")
                estado = st.selectbox("Estado", ["Pendiente", "Realizado", "Cancelado"])
                if st.form_submit_button("💾 Guardar"):
                    supabase.table("comunicaciones").insert({
                        "cliente_id": opts[sel], "fecha": str(fecha), "canal": canal,
                        "resumen": resumen, "proxima_accion": proxima_accion,
                        "fecha_proximo_seguimiento": str(fecha_prox) if fecha_prox else None,
                        "responsable": responsable, "estado": estado,
                    }).execute()
                    st.success("Comunicación registrada.")
                    clear_cache()
                    st.rerun()

# =====================================================================
# PRODUCTOS
# =====================================================================
elif page == "🧾 Productos":
    st.title("🧾 Catálogo de Productos")
    st.caption("Basado en las líneas Kioshi Stone, Legacy Rural y Böhm.")

    tab1, tab2 = st.tabs(["Catálogo", "Agregar / Editar"])
    with tab1:
        df = cached_fetch("productos", order_by="marca")
        marca_filtro = st.multiselect("Filtrar por marca", sorted(df["marca"].unique()) if not df.empty else [])
        if marca_filtro:
            df = df[df["marca"].isin(marca_filtro)]
        st.dataframe(df, use_container_width=True, hide_index=True)
        if not df.empty:
            bajo_stock = df[df["stock_actual"] <= df["stock_minimo"]]
            if not bajo_stock.empty:
                st.warning(f"⚠️ {len(bajo_stock)} producto(s) por debajo del stock mínimo.")
                st.dataframe(bajo_stock[["marca", "nombre", "stock_actual", "stock_minimo"]],
                             use_container_width=True, hide_index=True)

    with tab2:
        opts, df_all = productos_options()
        modo = st.radio("Acción", ["Nuevo producto", "Editar existente"], horizontal=True, key="modo_prod")
        registro = {}
        prod_id = None
        if modo == "Editar existente" and opts:
            sel = st.selectbox("Seleccioná el producto", list(opts.keys()))
            prod_id = opts[sel]
            full = fetch("productos")
            registro = full[full["id"] == prod_id].iloc[0].to_dict()

        with st.form("form_producto", clear_on_submit=(modo == "Nuevo producto")):
            categoria = st.selectbox("Categoría", ["Fertilización", "Indumentaria", "Calzado"],
                                      index=["Fertilización", "Indumentaria", "Calzado"].index(registro.get("categoria", "Fertilización")))
            marca = st.text_input("Marca", value=registro.get("marca", ""))
            linea = st.text_input("Línea", value=registro.get("linea", "") or "")
            nombre = st.text_input("Nombre del producto *", value=registro.get("nombre", ""))
            descripcion = st.text_area("Descripción", value=registro.get("descripcion", "") or "")
            unidad = st.text_input("Unidad de medida", value=registro.get("unidad_medida", "unidad"))
            colp1, colp2, colp3, colp4 = st.columns(4)
            precio = colp1.number_input("Precio unitario (USD)", min_value=0.0, value=float(registro.get("precio_unitario", 0) or 0))
            costo = colp2.number_input("Costo unitario (USD)", min_value=0.0, value=float(registro.get("costo_unitario", 0) or 0))
            stock = colp3.number_input("Stock actual", min_value=0.0, value=float(registro.get("stock_actual", 0) or 0))
            stock_min = colp4.number_input("Stock mínimo", min_value=0.0, value=float(registro.get("stock_minimo", 0) or 0))
            activo = st.checkbox("Activo", value=registro.get("activo", True))
            colb1, colb2 = st.columns(2)
            guardar = colb1.form_submit_button("💾 Guardar")
            eliminar = colb2.form_submit_button("🗑️ Eliminar") if modo == "Editar existente" else False

            if guardar:
                if not nombre or not marca:
                    st.error("Marca y Nombre son obligatorios.")
                else:
                    payload = {
                        "categoria": categoria, "marca": marca, "linea": linea, "nombre": nombre,
                        "descripcion": descripcion, "unidad_medida": unidad, "precio_unitario": precio,
                        "costo_unitario": costo, "stock_actual": stock, "stock_minimo": stock_min,
                        "activo": activo,
                    }
                    if modo == "Nuevo producto":
                        supabase.table("productos").insert(payload).execute()
                        st.success("Producto creado.")
                    else:
                        supabase.table("productos").update(payload).eq("id", prod_id).execute()
                        st.success("Producto actualizado.")
                    clear_cache()
                    st.rerun()

            if eliminar and prod_id:
                supabase.table("productos").delete().eq("id", prod_id).execute()
                st.success("Producto eliminado.")
                clear_cache()
                st.rerun()

# =====================================================================
# VENTAS
# =====================================================================
elif page == "💰 Ventas":
    st.title("💰 Ventas")
    opts_c, _ = clientes_options()
    opts_p, df_prod = productos_options()

    tab1, tab2 = st.tabs(["Listado", "Nueva venta"])
    with tab1:
        df = fetch("ventas", "*, clientes(empresa), productos(nombre, marca)", order_by="fecha_venta", desc=True)
        if not df.empty:
            df["cliente"] = df["clientes"].apply(lambda x: x.get("empresa") if isinstance(x, dict) else None)
            df["producto"] = df["productos"].apply(lambda x: x.get("nombre") if isinstance(x, dict) else None)
            df = df.drop(columns=["clientes", "productos"])
        st.dataframe(df, use_container_width=True, hide_index=True)
        if not df.empty:
            st.metric("Total ventas listadas (USD)", f"{df['monto_total'].sum():,.2f}")

    with tab2:
        if not opts_c or not opts_p:
            st.warning("Necesitás al menos un cliente y un producto cargados.")
        else:
            with st.form("form_venta", clear_on_submit=True):
                sel_c = st.selectbox("Cliente", list(opts_c.keys()))
                sel_p = st.selectbox("Producto", list(opts_p.keys()))
                fecha = st.date_input("Fecha de venta", value=date.today())
                cantidad = st.number_input("Cantidad", min_value=0.0, value=1.0)
                precio_sugerido = float(df_prod[df_prod["id"] == opts_p[sel_p]]["precio_unitario"].iloc[0])
                precio = st.number_input("Precio unitario (USD)", min_value=0.0, value=precio_sugerido)
                estado = st.selectbox("Estado", ["Cotizado", "Confirmado", "Facturado", "Cancelado"], index=1)
                responsable = st.text_input("Responsable")
                notas = st.text_area("Notas")
                if st.form_submit_button("💾 Guardar venta"):
                    supabase.table("ventas").insert({
                        "cliente_id": opts_c[sel_c], "producto_id": opts_p[sel_p],
                        "fecha_venta": str(fecha), "cantidad": cantidad, "precio_unitario": precio,
                        "estado": estado, "responsable": responsable, "notas": notas,
                    }).execute()
                    st.success("Venta registrada.")
                    clear_cache()
                    st.rerun()

# =====================================================================
# COMPRAS
# =====================================================================
elif page == "📦 Compras":
    st.title("📦 Compras a Proveedores")
    opts_p, df_prod = productos_options()

    tab1, tab2 = st.tabs(["Listado", "Nueva compra"])
    with tab1:
        df = fetch("compras", "*, productos(nombre, marca)", order_by="fecha_compra", desc=True)
        if not df.empty:
            df["producto"] = df["productos"].apply(lambda x: x.get("nombre") if isinstance(x, dict) else None)
            df = df.drop(columns=["productos"])
        st.dataframe(df, use_container_width=True, hide_index=True)

    with tab2:
        if not opts_p:
            st.warning("Necesitás al menos un producto cargado.")
        else:
            with st.form("form_compra", clear_on_submit=True):
                proveedor = st.text_input("Proveedor *")
                sel_p = st.selectbox("Producto", list(opts_p.keys()))
                fecha = st.date_input("Fecha de compra", value=date.today())
                cantidad = st.number_input("Cantidad", min_value=0.0, value=1.0)
                costo = st.number_input("Costo unitario (USD)", min_value=0.0, value=0.0)
                estado = st.selectbox("Estado", ["Pendiente", "Recibido", "Cancelado"])
                notas = st.text_area("Notas")
                if st.form_submit_button("💾 Guardar compra"):
                    if not proveedor:
                        st.error("El proveedor es obligatorio.")
                    else:
                        supabase.table("compras").insert({
                            "proveedor": proveedor, "producto_id": opts_p[sel_p],
                            "fecha_compra": str(fecha), "cantidad": cantidad,
                            "costo_unitario": costo, "estado": estado, "notas": notas,
                        }).execute()
                        if estado == "Recibido":
                            prod_row = df_prod[df_prod["id"] == opts_p[sel_p]].iloc[0]
                            nuevo_stock = float(prod_row["stock_actual"]) + cantidad
                            supabase.table("productos").update({"stock_actual": nuevo_stock}).eq("id", opts_p[sel_p]).execute()
                        st.success("Compra registrada.")
                        clear_cache()
                        st.rerun()

# =====================================================================
# PROYECCIONES DE VENTAS
# =====================================================================
elif page == "📈 Proyecciones":
    st.title("📈 Proyección de Ventas")
    opts_c, _ = clientes_options()
    opts_p, _ = productos_options()

    tab1, tab2 = st.tabs(["Listado", "Nueva proyección"])
    with tab1:
        df = fetch("proyecciones_ventas", "*, clientes(empresa), productos(nombre)", order_by="mes", desc=True)
        if not df.empty:
            df["cliente"] = df["clientes"].apply(lambda x: x.get("empresa") if isinstance(x, dict) else None)
            df["producto"] = df["productos"].apply(lambda x: x.get("nombre") if isinstance(x, dict) else None)
            df = df.drop(columns=["clientes", "productos"])
            df["% cumplimiento"] = df.apply(
                lambda r: (r["monto_real"] / r["monto_proyectado"] * 100) if r["monto_proyectado"] else 0, axis=1)
        st.dataframe(df, use_container_width=True, hide_index=True)

    with tab2:
        if not opts_c or not opts_p:
            st.warning("Necesitás al menos un cliente y un producto cargados.")
        else:
            with st.form("form_proyeccion", clear_on_submit=True):
                sel_c = st.selectbox("Cliente", list(opts_c.keys()))
                sel_p = st.selectbox("Producto", list(opts_p.keys()))
                mes = st.date_input("Mes (elegí cualquier día del mes)", value=date.today())
                monto_proy = st.number_input("Monto proyectado (USD)", min_value=0.0, value=0.0)
                monto_real = st.number_input("Monto real (USD)", min_value=0.0, value=0.0)
                estado = st.selectbox("Estado", ["Abierto", "Cerrado", "Perdido"])
                if st.form_submit_button("💾 Guardar proyección"):
                    mes_normalizado = mes.replace(day=1)
                    supabase.table("proyecciones_ventas").insert({
                        "cliente_id": opts_c[sel_c], "producto_id": opts_p[sel_p],
                        "mes": str(mes_normalizado), "monto_proyectado": monto_proy,
                        "monto_real": monto_real, "estado": estado,
                    }).execute()
                    st.success("Proyección registrada.")
                    clear_cache()
                    st.rerun()

# =====================================================================
# POSTVENTA
# =====================================================================
elif page == "🤝 Postventa":
    st.title("🤝 Seguimiento Postventa")
    opts_c, _ = clientes_options()
    opts_p, _ = productos_options()

    tab1, tab2 = st.tabs(["Listado", "Nuevo registro"])
    with tab1:
        df = fetch("postventa", "*, clientes(empresa), productos(nombre)", order_by="fecha_venta", desc=True)
        if not df.empty:
            df["cliente"] = df["clientes"].apply(lambda x: x.get("empresa") if isinstance(x, dict) else None)
            df["producto"] = df["productos"].apply(lambda x: x.get("nombre") if isinstance(x, dict) else None)
            df = df.drop(columns=["clientes", "productos"])
        st.dataframe(df, use_container_width=True, hide_index=True)

    with tab2:
        if not opts_c:
            st.warning("Necesitás al menos un cliente cargado.")
        else:
            with st.form("form_postventa", clear_on_submit=True):
                sel_c = st.selectbox("Cliente", list(opts_c.keys()))
                sel_p = st.selectbox("Producto", list(opts_p.keys())) if opts_p else None
                fecha_venta = st.date_input("Fecha de venta", value=date.today())
                llamada_fecha = st.date_input("Fecha llamada de control (+7 días)", value=None)
                encuesta = st.selectbox("Encuesta de satisfacción", ["Pendiente", "Positiva", "Neutra", "Negativa"])
                fecha_recompra = st.date_input("Fecha estimada de recompra", value=None)
                estado = st.selectbox("Estado", ["En seguimiento", "Completado", "Sin respuesta"])
                notas = st.text_area("Notas")
                if st.form_submit_button("💾 Guardar"):
                    supabase.table("postventa").insert({
                        "cliente_id": opts_c[sel_c],
                        "producto_id": opts_p[sel_p] if sel_p else None,
                        "fecha_venta": str(fecha_venta),
                        "llamada_control_fecha": str(llamada_fecha) if llamada_fecha else None,
                        "encuesta_satisfaccion": encuesta,
                        "fecha_estimada_recompra": str(fecha_recompra) if fecha_recompra else None,
                        "estado": estado, "notas": notas,
                    }).execute()
                    st.success("Registro de postventa guardado.")
                    clear_cache()
                    st.rerun()
