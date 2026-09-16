# Las Amalias — CRM

Sistema de gestión (clientes, comunicaciones, catálogo de productos, ventas,
compras, proyecciones y postventa) sobre **Supabase** (base de datos) +
**Streamlit** (interfaz web accesible desde cualquier lugar).

## Archivos de este paquete

| Archivo | Para qué sirve |
|---|---|
| `supabase_schema.sql` | Crea todas las tablas en tu base de Supabase |
| `app.py` | La aplicación web (CRM) |
| `requirements.txt` | Librerías que necesita la app |
| `.streamlit/secrets_example.toml` | Plantilla de credenciales |
| `migrar_excel.py` | (Opcional) sube los datos que ya tenías en el Excel |

---

## Paso 1 — Crear las tablas en Supabase

1. Entrá a tu proyecto: `https://supabase.com/dashboard/project/bwmeqifblrabsayiybkk`
2. En el menú lateral, andá a **SQL Editor** → **New query**.
3. Abrí `supabase_schema.sql`, copiá todo el contenido y pegalo ahí.
4. Click en **Run**. Esto crea las tablas `clientes`, `comunicaciones`,
   `productos`, `ventas`, `compras`, `proyecciones_ventas`, `postventa`, y
   carga el catálogo inicial de productos (Kioshi Stone, Legacy Rural, Böhm)
   con precios y stock en 0 para que los completes vos.
5. Verificá en **Table Editor** que las tablas aparezcan con datos.

## Paso 2 — Obtener las credenciales de conexión

1. En Supabase, andá a **Project Settings** (ícono de engranaje) → **API**.
2. Copiá:
   - **Project URL** (es `https://bwmeqifblrabsayiybkk.supabase.co`)
   - **service_role key** (está en la sección "Project API keys" — es la
     clave secreta, no la `anon public`). Esta clave se queda únicamente en
     el servidor de la app, nunca la compartas ni la subas a GitHub.

## Paso 3 — Subir el código a GitHub

1. Creá un repositorio nuevo en GitHub (puede ser privado), por ejemplo
   `las-amalias-crm`.
2. Subí estos archivos: `app.py`, `requirements.txt`, `supabase_schema.sql`,
   `migrar_excel.py`.
3. **No subas** `.streamlit/secrets_example.toml` con datos reales — usalo
   solo como referencia. Las credenciales reales se cargan directamente en
   Streamlit Cloud (paso siguiente), nunca en el repositorio.

## Paso 4 — Publicar la app en Streamlit Community Cloud

1. Entrá a `https://share.streamlit.io` (donde ya tenés tu cuenta `claudio391`).
2. Click en **Create app** → **From existing repo**.
3. Elegí tu repositorio `las-amalias-crm`, la rama `main` y el archivo
   principal `app.py`.
4. Antes de darle a Deploy (o después, desde **⋮ → Settings → Secrets**),
   pegá esto en la caja de "Secrets", reemplazando los valores:

   ```toml
   SUPABASE_URL = "https://bwmeqifblrabsayiybkk.supabase.co"
   SUPABASE_KEY = "tu_service_role_key_real"

   [APP_USERS]
   maria = "una-contraseña-segura"
   admin = "otra-contraseña-segura"
   ```

5. Click en **Deploy**. En un par de minutos vas a tener una URL pública
   (algo como `https://las-amalias-crm.streamlit.app`) accesible desde
   cualquier computadora o celular con internet.

## Paso 5 — (Opcional) Migrar lo que ya tenías en el Excel

El Excel que compartiste todavía tiene solo el ejemplo. Cuando tengas datos
reales cargados ahí y quieras subirlos de una sola vez:

```bash
pip install pandas openpyxl supabase
export SUPABASE_URL="https://bwmeqifblrabsayiybkk.supabase.co"
export SUPABASE_KEY="tu_service_role_key"
python migrar_excel.py LasAmalias_CRM.xlsx
```

Esto carga clientes, comunicaciones y postventa. Las proyecciones de venta
conviene cargarlas directamente desde la pestaña **Proyecciones** de la app,
porque ahí se asocian a un producto del catálogo.

## Paso 6 — Uso diario

- Entrá a la URL de tu app, iniciá sesión con el usuario/contraseña que
  definiste en `[APP_USERS]`.
- Navegá por el menú lateral: Dashboard, Clientes, Comunicaciones,
  Productos, Ventas, Compras, Proyecciones, Postventa.
- Cada sección tiene una pestaña **Listado** (para ver y filtrar) y otra
  para **Agregar / Editar** registros.
- El Dashboard se actualiza solo con los datos que vayas cargando (KPIs,
  ventas por mes, proyectado vs. real, alertas de postventa pendiente).

## Notas sobre seguridad y costos

- **Plan gratuito de Supabase**: alcanza sobradamente para este uso (CRM de
  una pyme). Si el proyecto queda inactivo 1 semana se "pausa" solo, y se
  reactiva automáticamente al entrar de nuevo — puede tardar unos segundos
  la primera carga.
- **Streamlit Community Cloud**: gratis para apps públicas o privadas de
  este tamaño.
- El login de la app es simple (usuario/contraseña definidos por vos en los
  Secrets). Si en el futuro necesitás roles distintos por usuario (ej. un
  vendedor que solo vea sus propios clientes) o SSO, se puede evolucionar
  usando **Supabase Auth**; avisame cuando llegues a ese punto y lo armamos.

## Próximos pasos posibles (cuando quieras)

- Completar precios y stock reales en la tabla `productos` (o pedirme los
  PDFs de catálogo de Kioshi Stone / Legacy / Böhm para cargarlos con
  precios reales).
- Exportar reportes a Excel/PDF directamente desde la app.
- Alertas automáticas por email/WhatsApp para seguimientos vencidos.
- Un rol de "solo lectura" para dueños/gerencia vs. "edición" para ventas.
