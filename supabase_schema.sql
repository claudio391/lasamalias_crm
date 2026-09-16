-- =====================================================================
-- LAS AMALIAS — Esquema de Base de Datos CRM
-- Ejecutar completo en: Supabase Dashboard > SQL Editor > New query
-- =====================================================================

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------
-- 1. CLIENTES
-- ---------------------------------------------------------------------
create table if not exists clientes (
    id uuid primary key default gen_random_uuid(),
    empresa text not null,
    contacto_principal text,
    telefono text,
    email text,
    ciudad text,
    provincia text,
    producto_interes text,
    estado text not null default 'Prospecto'
        check (estado in ('Prospecto','Activo','Inactivo')),
    fecha_alta date not null default current_date,
    responsable_comercial text,
    notas text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- 2. PRODUCTOS (catálogo: Kioshi Stone / Legacy Rural / Böhm)
-- ---------------------------------------------------------------------
create table if not exists productos (
    id uuid primary key default gen_random_uuid(),
    categoria text not null
        check (categoria in ('Fertilización','Indumentaria','Calzado')),
    marca text not null,               -- Kioshi Stone / Legacy Rural / Böhm
    linea text,                        -- ej: 'MIST Líquida', 'Pantalones', 'Botines Composite'
    nombre text not null,
    descripcion text,
    unidad_medida text not null default 'unidad',
    precio_unitario numeric(12,2) not null default 0,
    costo_unitario numeric(12,2) not null default 0,
    stock_actual numeric(12,2) not null default 0,
    stock_minimo numeric(12,2) not null default 0,
    activo boolean not null default true,
    created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- 3. COMUNICACIONES (seguimiento de contactos con clientes)
-- ---------------------------------------------------------------------
create table if not exists comunicaciones (
    id uuid primary key default gen_random_uuid(),
    cliente_id uuid references clientes(id) on delete cascade,
    fecha date not null default current_date,
    canal text,                        -- Llamada / Email / WhatsApp / Visita
    resumen text,
    proxima_accion text,
    fecha_proximo_seguimiento date,
    responsable text,
    estado text not null default 'Pendiente'
        check (estado in ('Pendiente','Realizado','Cancelado')),
    created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- 4. VENTAS
-- ---------------------------------------------------------------------
create table if not exists ventas (
    id uuid primary key default gen_random_uuid(),
    cliente_id uuid references clientes(id),
    producto_id uuid references productos(id),
    fecha_venta date not null default current_date,
    cantidad numeric(12,2) not null default 1,
    precio_unitario numeric(12,2) not null default 0,
    monto_total numeric(12,2) generated always as (cantidad * precio_unitario) stored,
    estado text not null default 'Confirmado'
        check (estado in ('Cotizado','Confirmado','Facturado','Cancelado')),
    responsable text,
    notas text,
    created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- 5. COMPRAS (reposición de stock a proveedores)
-- ---------------------------------------------------------------------
create table if not exists compras (
    id uuid primary key default gen_random_uuid(),
    proveedor text not null,
    producto_id uuid references productos(id),
    fecha_compra date not null default current_date,
    cantidad numeric(12,2) not null default 1,
    costo_unitario numeric(12,2) not null default 0,
    monto_total numeric(12,2) generated always as (cantidad * costo_unitario) stored,
    estado text not null default 'Pendiente'
        check (estado in ('Pendiente','Recibido','Cancelado')),
    notas text,
    created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- 6. PROYECCIÓN DE VENTAS
-- ---------------------------------------------------------------------
create table if not exists proyecciones_ventas (
    id uuid primary key default gen_random_uuid(),
    cliente_id uuid references clientes(id),
    producto_id uuid references productos(id),
    mes date not null,                 -- guardar como primer día del mes, ej '2026-09-01'
    monto_proyectado numeric(12,2) not null default 0,
    monto_real numeric(12,2) not null default 0,
    diferencia numeric(12,2) generated always as (monto_real - monto_proyectado) stored,
    estado text not null default 'Abierto'
        check (estado in ('Abierto','Cerrado','Perdido')),
    created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- 7. POSTVENTA
-- ---------------------------------------------------------------------
create table if not exists postventa (
    id uuid primary key default gen_random_uuid(),
    venta_id uuid references ventas(id),
    cliente_id uuid references clientes(id),
    producto_id uuid references productos(id),
    fecha_venta date,
    llamada_control_fecha date,
    llamada_control_estado text not null default 'Pendiente'
        check (llamada_control_estado in ('Pendiente','Realizada')),
    encuesta_satisfaccion text,
    fecha_estimada_recompra date,
    estado text not null default 'En seguimiento'
        check (estado in ('En seguimiento','Completado','Sin respuesta')),
    notas text,
    created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Índices útiles
-- ---------------------------------------------------------------------
create index if not exists idx_comunicaciones_cliente on comunicaciones(cliente_id);
create index if not exists idx_ventas_cliente on ventas(cliente_id);
create index if not exists idx_ventas_producto on ventas(producto_id);
create index if not exists idx_ventas_fecha on ventas(fecha_venta);
create index if not exists idx_compras_producto on compras(producto_id);
create index if not exists idx_proyecciones_mes on proyecciones_ventas(mes);
create index if not exists idx_postventa_cliente on postventa(cliente_id);

-- ---------------------------------------------------------------------
-- Trigger: actualizar updated_at en clientes automáticamente
-- ---------------------------------------------------------------------
create or replace function set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_clientes_updated_at on clientes;
create trigger trg_clientes_updated_at
    before update on clientes
    for each row execute function set_updated_at();

-- =====================================================================
-- CATÁLOGO INICIAL DE PRODUCTOS (según líneas publicadas en la web)
-- Editá precios, stock y agregá/quitá renglones según tu catálogo real.
-- =====================================================================
insert into productos (categoria, marca, linea, nombre, descripcion, unidad_medida, precio_unitario, costo_unitario, stock_actual)
values
-- Kioshi Stone — Fertilización
('Fertilización','Kioshi Stone','Línea Líquida (MIST)','MIST Yerba Mate','Nanopartículas minerales para aplicación foliar en yerba mate','litro',0,0,0),
('Fertilización','Kioshi Stone','Línea Líquida (MIST)','MIST Cítricos','Nanopartículas minerales para aplicación foliar en cítricos','litro',0,0,0),
('Fertilización','Kioshi Stone','Línea Líquida (MIST)','MIST Soja','Nanopartículas minerales para aplicación foliar en soja','litro',0,0,0),
('Fertilización','Kioshi Stone','Microgranulados','Microgranulado Corrección de Suelos','Corrección nanotecnológica y enmienda de suelos localizada','kg',0,0,0),
-- Legacy Rural — Indumentaria
('Indumentaria','Legacy Rural','Pantalones y Bombachas','Pantalón Cargo','Pantalón de trabajo cargo','unidad',0,0,0),
('Indumentaria','Legacy Rural','Pantalones y Bombachas','Pantalón Cazador','Pantalón de trabajo cazador','unidad',0,0,0),
('Indumentaria','Legacy Rural','Pantalones y Bombachas','Pantalón Rip Stop Antidesgarro','Pantalón resistente al desgarro','unidad',0,0,0),
('Indumentaria','Legacy Rural','Pantalones y Bombachas','Bombacha de Campo','Bombacha de campo tradicional','unidad',0,0,0),
('Indumentaria','Legacy Rural','Camisas y Remeras','Camisa de Trabajo Manga Larga','Camisa técnica de trabajo','unidad',0,0,0),
('Indumentaria','Legacy Rural','Camisas y Remeras','Remera Algodón Peinado','Remera de algodón peinado','unidad',0,0,0),
('Indumentaria','Legacy Rural','Abrigos Técnicos','Buzo Polar con Cierre','Buzo polar técnico','unidad',0,0,0),
('Indumentaria','Legacy Rural','Abrigos Técnicos','Campera Polar Antipilling','Campera polar antipilling','unidad',0,0,0),
('Indumentaria','Legacy Rural','Abrigos Técnicos','Campera Trucker con Capucha','Campera trucker con capucha','unidad',0,0,0),
-- Böhm — Calzados de Seguridad
('Calzado','Böhm','Botines Composite y Acero','Botín Composite','Botín de seguridad inyección PU bidensidad, dieléctrico','par',0,0,0),
('Calzado','Böhm','Botines Composite y Acero','Botín de Acero','Botín de seguridad con puntera de acero','par',0,0,0),
('Calzado','Böhm','Línea Zapatillas Feder','Zapatilla Feder','Capellada tejida Knight, intersuela EVA/Caucho liviana','par',0,0,0),
('Calzado','Böhm','Especiales y Tácticos','Bota Petrolera','Bota de seguridad resistente a hidrocarburos','par',0,0,0),
('Calzado','Böhm','Especiales y Tácticos','Borceguí Táctico','Borceguí táctico de seguridad','par',0,0,0),
('Calzado','Böhm','Especiales y Tácticos','Calzado Sanitario','Calzado de uso sanitario','par',0,0,0),
('Calzado','Böhm','Especiales y Tácticos','Bota Metatarsal','Bota con protección metatarsal','par',0,0,0)
on conflict do nothing;

-- =====================================================================
-- Nota sobre seguridad de acceso (RLS)
-- =====================================================================
-- Este esquema deja Row Level Security (RLS) desactivado por simplicidad:
-- la app de Streamlit se conecta desde el servidor usando la clave
-- "service_role" (nunca expuesta al navegador), y el control de acceso
-- de usuarios se maneja con un login simple dentro de la propia app.
-- Si en el futuro vas a exponer estas tablas directamente al navegador
-- (ej. con la clave "anon"), hay que activar RLS y crear políticas:
--   alter table clientes enable row level security;
--   create policy "allow all for authenticated" on clientes
--     for all using (auth.role() = 'authenticated');
-- (repetir para cada tabla, ajustando la política a tu esquema de auth)
