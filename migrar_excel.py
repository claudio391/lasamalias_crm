"""
Migración puntual: carga los datos del Excel LasAmalias_CRM.xlsx a Supabase.
Usalo UNA sola vez para no duplicar el ejemplo de la planilla; después toda
la carga se hace desde la app de Streamlit.

Uso:
    pip install pandas openpyxl supabase
    export SUPABASE_URL="https://bwmeqifblrabsayiybkk.supabase.co"
    export SUPABASE_KEY="tu_service_role_key"
    python migrar_excel.py /ruta/a/LasAmalias_CRM.xlsx
"""

import sys
import os
import pandas as pd
from supabase import create_client

EXCLUIR_SI_CONTIENE = ["Completá una fila", "Se actualiza automáticamente",
                        "Un registro por cada", "Cargá el monto", "Registrá cada venta"]


def limpiar_hoja(path, hoja, fila_encabezado):
    df = pd.read_excel(path, sheet_name=hoja, header=fila_encabezado)
    df = df.dropna(how="all")
    # descarta filas de totales/instrucciones residuales
    primera_col = df.columns[0]
    df = df[~df[primera_col].astype(str).str.contains("TOTALES", na=False)]
    return df.reset_index(drop=True)


def main():
    if len(sys.argv) < 2:
        print("Uso: python migrar_excel.py /ruta/a/LasAmalias_CRM.xlsx")
        sys.exit(1)

    path = sys.argv[1]
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("Definí las variables de entorno SUPABASE_URL y SUPABASE_KEY antes de correr esto.")
        sys.exit(1)

    supabase = create_client(url, key)
    cliente_id_por_nombre = {}

    # --- Clientes ---
    df_clientes = limpiar_hoja(path, "Clientes", fila_encabezado=3)
    for _, row in df_clientes.iterrows():
        empresa = row.get("Empresa / Productor")
        if pd.isna(empresa):
            continue
        payload = {
            "empresa": str(empresa),
            "contacto_principal": str(row.get("Contacto principal", "") or ""),
            "telefono": str(row.get("Teléfono", "") or ""),
            "email": str(row.get("Email", "") or ""),
            "producto_interes": str(row.get("Producto de interés", "") or ""),
            "estado": str(row.get("Estado", "Prospecto") or "Prospecto"),
            "responsable_comercial": str(row.get("Responsable comercial", "") or ""),
            "notas": str(row.get("Notas", "") or ""),
        }
        ciudad_prov = str(row.get("Ciudad / Provincia", "") or "")
        if "," in ciudad_prov:
            ciudad, provincia = [x.strip() for x in ciudad_prov.split(",", 1)]
            payload["ciudad"], payload["provincia"] = ciudad, provincia
        res = supabase.table("clientes").insert(payload).execute()
        cliente_id_por_nombre[str(empresa)] = res.data[0]["id"]
        print(f"Cliente cargado: {empresa}")

    # --- Comunicaciones ---
    df_com = limpiar_hoja(path, "Comunicaciones", fila_encabezado=3)
    for _, row in df_com.iterrows():
        cliente = row.get("Cliente")
        if pd.isna(cliente) or cliente not in cliente_id_por_nombre:
            continue
        supabase.table("comunicaciones").insert({
            "cliente_id": cliente_id_por_nombre[cliente],
            "canal": str(row.get("Canal", "") or ""),
            "resumen": str(row.get("Resumen de la conversación", "") or ""),
            "proxima_accion": str(row.get("Próxima acción", "") or ""),
            "responsable": str(row.get("Responsable", "") or ""),
            "estado": str(row.get("Estado", "Pendiente") or "Pendiente"),
        }).execute()
        print(f"Comunicación cargada para: {cliente}")

    # --- Postventa ---
    df_post = limpiar_hoja(path, "Postventa", fila_encabezado=3)
    for _, row in df_post.iterrows():
        cliente = row.get("Cliente")
        if pd.isna(cliente) or cliente not in cliente_id_por_nombre:
            continue
        supabase.table("postventa").insert({
            "cliente_id": cliente_id_por_nombre[cliente],
            "encuesta_satisfaccion": str(row.get("Encuesta de satisfacción", "") or ""),
            "estado": str(row.get("Estado", "En seguimiento") or "En seguimiento"),
            "notas": str(row.get("Notas", "") or ""),
        }).execute()
        print(f"Postventa cargada para: {cliente}")

    print("\nListo. Revisá los datos en Supabase > Table Editor.")
    print("NOTA: Los montos de 'Proyección Ventas' no se migraron automáticamente")
    print("porque requieren asociar también un producto del catálogo; cargalos")
    print("desde la pestaña Proyecciones de la app.")


if __name__ == "__main__":
    main()
