import sqlite3
import os
from datetime import datetime


def get_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path):
    conn = get_connection(db_path)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS empresa (
            id INTEGER PRIMARY KEY,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            creado_en TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            categoria_id INTEGER,
            precio_costo REAL DEFAULT 0,
            precio_venta REAL DEFAULT 0,
            stock_actual INTEGER DEFAULT 0,
            stock_minimo INTEGER DEFAULT 0,
            unidad TEXT DEFAULT 'unidad',
            activo INTEGER DEFAULT 1,
            creado_en TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (categoria_id) REFERENCES categorias(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('entrada','salida','ajuste')),
            cantidad INTEGER NOT NULL,
            stock_antes INTEGER,
            stock_despues INTEGER,
            motivo TEXT,
            referencia TEXT,
            fecha TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (producto_id) REFERENCES productos(id)
        )
    """)

    for cat in ["General", "Electrónica", "Ropa", "Alimentos", "Herramientas", "Insumos", "Otros"]:
        c.execute("INSERT OR IGNORE INTO categorias (nombre) VALUES (?)", (cat,))

    conn.commit()
    conn.close()


def get_empresa(db_path):
    conn = get_connection(db_path)
    row = conn.execute("SELECT * FROM empresa WHERE id=1").fetchone()
    conn.close()
    return dict(row) if row else None


def set_empresa(db_path, nombre, descripcion=""):
    conn = get_connection(db_path)
    existing = conn.execute("SELECT id FROM empresa WHERE id=1").fetchone()
    if existing:
        conn.execute("UPDATE empresa SET nombre=?, descripcion=? WHERE id=1", (nombre, descripcion))
    else:
        conn.execute("INSERT INTO empresa (id, nombre, descripcion) VALUES (1,?,?)", (nombre, descripcion))
    conn.commit()
    conn.close()


def get_categorias(db_path):
    conn = get_connection(db_path)
    rows = conn.execute("SELECT * FROM categorias ORDER BY nombre").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_categoria(db_path, nombre):
    conn = get_connection(db_path)
    try:
        conn.execute("INSERT INTO categorias (nombre) VALUES (?)", (nombre,))
        conn.commit()
        return True, "Categoría creada"
    except sqlite3.IntegrityError:
        return False, "Ya existe esa categoría"
    finally:
        conn.close()


def delete_categoria(db_path, cat_id):
    conn = get_connection(db_path)
    count = conn.execute("SELECT COUNT(*) FROM productos WHERE categoria_id=?", (cat_id,)).fetchone()[0]
    if count > 0:
        conn.close()
        return False, f"Hay {count} productos en esta categoría"
    conn.execute("DELETE FROM categorias WHERE id=?", (cat_id,))
    conn.commit()
    conn.close()
    return True, "Categoría eliminada"


def get_productos(db_path, filtro_nombre="", filtro_categoria=None, solo_bajo_stock=False, solo_activos=True):
    conn = get_connection(db_path)
    query = """
        SELECT p.*, c.nombre as categoria_nombre
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        WHERE 1=1
    """
    params = []
    if solo_activos:
        query += " AND p.activo = 1"
    if filtro_nombre:
        query += " AND (p.nombre LIKE ? OR p.codigo LIKE ?)"
        params += [f"%{filtro_nombre}%", f"%{filtro_nombre}%"]
    if filtro_categoria:
        query += " AND p.categoria_id = ?"
        params.append(filtro_categoria)
    if solo_bajo_stock:
        query += " AND p.stock_actual <= p.stock_minimo"
    query += " ORDER BY p.nombre"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_producto_by_id(db_path, prod_id):
    conn = get_connection(db_path)
    row = conn.execute("""
        SELECT p.*, c.nombre as categoria_nombre
        FROM productos p LEFT JOIN categorias c ON p.categoria_id=c.id
        WHERE p.id=?
    """, (prod_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_producto(db_path, codigo, nombre, descripcion, categoria_id,
                 precio_costo, precio_venta, stock_inicial, stock_minimo, unidad):
    conn = get_connection(db_path)
    try:
        conn.execute("""
            INSERT INTO productos
              (codigo, nombre, descripcion, categoria_id,
               precio_costo, precio_venta, stock_actual, stock_minimo, unidad)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (codigo, nombre, descripcion, categoria_id,
              precio_costo, precio_venta, stock_inicial, stock_minimo, unidad))
        prod_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        if stock_inicial > 0:
            conn.execute("""
                INSERT INTO movimientos
                  (producto_id, tipo, cantidad, stock_antes, stock_despues, motivo)
                VALUES (?, 'entrada', ?, 0, ?, 'Stock inicial')
            """, (prod_id, stock_inicial, stock_inicial))
        conn.commit()
        return True, "Producto creado correctamente"
    except sqlite3.IntegrityError:
        return False, "El código ya existe"
    finally:
        conn.close()


def update_producto(db_path, prod_id, codigo, nombre, descripcion, categoria_id,
                    precio_costo, precio_venta, stock_minimo, unidad):
    conn = get_connection(db_path)
    try:
        conn.execute("""
            UPDATE productos SET codigo=?, nombre=?, descripcion=?, categoria_id=?,
            precio_costo=?, precio_venta=?, stock_minimo=?, unidad=?
            WHERE id=?
        """, (codigo, nombre, descripcion, categoria_id,
              precio_costo, precio_venta, stock_minimo, unidad, prod_id))
        conn.commit()
        return True, "Producto actualizado"
    except sqlite3.IntegrityError:
        return False, "El código ya está en uso"
    finally:
        conn.close()


def delete_producto(db_path, prod_id):
    conn = get_connection(db_path)
    conn.execute("UPDATE productos SET activo=0 WHERE id=?", (prod_id,))
    conn.commit()
    conn.close()
    return True, "Producto desactivado"


def registrar_movimiento(db_path, producto_id, tipo, cantidad, motivo="", referencia=""):
    conn = get_connection(db_path)
    prod = conn.execute("SELECT stock_actual FROM productos WHERE id=?", (producto_id,)).fetchone()
    if not prod:
        conn.close()
        return False, "Producto no encontrado"
    stock_antes = prod["stock_actual"]
    if tipo == "entrada":
        stock_despues = stock_antes + cantidad
    elif tipo == "salida":
        if cantidad > stock_antes:
            conn.close()
            return False, f"Stock insuficiente (disponible: {stock_antes})"
        stock_despues = stock_antes - cantidad
    elif tipo == "ajuste":
        stock_despues = cantidad
        cantidad = abs(stock_despues - stock_antes)
    else:
        conn.close()
        return False, "Tipo inválido"

    conn.execute("""
        INSERT INTO movimientos
          (producto_id, tipo, cantidad, stock_antes, stock_despues, motivo, referencia)
        VALUES (?,?,?,?,?,?,?)
    """, (producto_id, tipo, cantidad, stock_antes, stock_despues, motivo, referencia))
    conn.execute("UPDATE productos SET stock_actual=? WHERE id=?", (stock_despues, producto_id))
    conn.commit()
    conn.close()
    return True, f"Movimiento registrado. Stock: {stock_antes} → {stock_despues}"


def get_movimientos(db_path, producto_id=None, tipo=None,
                    fecha_desde=None, fecha_hasta=None, limit=500):
    conn = get_connection(db_path)
    query = """
        SELECT m.*, p.nombre as producto_nombre, p.codigo as producto_codigo
        FROM movimientos m JOIN productos p ON m.producto_id=p.id
        WHERE 1=1
    """
    params = []
    if producto_id:
        query += " AND m.producto_id=?"
        params.append(producto_id)
    if tipo:
        query += " AND m.tipo=?"
        params.append(tipo)
    if fecha_desde:
        query += " AND m.fecha >= ?"
        params.append(fecha_desde)
    if fecha_hasta:
        query += " AND m.fecha <= ?"
        params.append(fecha_hasta + " 23:59:59")
    query += f" ORDER BY m.fecha DESC LIMIT {limit}"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats_generales(db_path):
    conn = get_connection(db_path)
    total_productos  = conn.execute("SELECT COUNT(*) FROM productos WHERE activo=1").fetchone()[0]
    bajo_stock       = conn.execute("SELECT COUNT(*) FROM productos WHERE activo=1 AND stock_actual <= stock_minimo").fetchone()[0]
    total_entradas   = conn.execute("SELECT COALESCE(SUM(cantidad),0) FROM movimientos WHERE tipo='entrada'").fetchone()[0]
    total_salidas    = conn.execute("SELECT COALESCE(SUM(cantidad),0) FROM movimientos WHERE tipo='salida'").fetchone()[0]
    valor_inventario = conn.execute("SELECT COALESCE(SUM(stock_actual * precio_costo),0) FROM productos WHERE activo=1").fetchone()[0]
    conn.close()
    return {
        "total_productos": total_productos,
        "bajo_stock": bajo_stock,
        "total_entradas": total_entradas,
        "total_salidas": total_salidas,
        "valor_inventario": valor_inventario,
    }


def get_movimientos_por_dia(db_path, dias=30):
    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT DATE(fecha) as dia, tipo, SUM(cantidad) as total
        FROM movimientos
        WHERE fecha >= datetime('now', ?)
        GROUP BY dia, tipo ORDER BY dia
    """, (f"-{dias} days",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_top_productos(db_path, limit=10):
    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT p.nombre, SUM(m.cantidad) as total_movido
        FROM movimientos m JOIN productos p ON m.producto_id=p.id
        WHERE m.tipo IN ('entrada','salida')
        GROUP BY m.producto_id ORDER BY total_movido DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stock_por_categoria(db_path):
    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT c.nombre, COUNT(p.id) as cantidad, SUM(p.stock_actual) as stock_total
        FROM productos p LEFT JOIN categorias c ON p.categoria_id=c.id
        WHERE p.activo=1
        GROUP BY p.categoria_id ORDER BY stock_total DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]