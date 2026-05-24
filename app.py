import customtkinter as ctk
from tkinter import messagebox, filedialog
import tkinter as tk
from tkinter import ttk
import os, sys, json
from datetime import datetime

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)

from db.database import *
from modules.exportar import *

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

CONFIG_FILE = os.path.join(BASE_DIR, "stockpro_config.json")

C_PRIMARY   = "#1B4F72"
C_SECONDARY = "#2E86C1"
C_ACCENT    = "#27AE60"
C_WARNING   = "#E67E22"
C_DANGER    = "#E74C3C"
C_BG        = "#F0F3F4"
C_CARD      = "#FFFFFF"
C_TEXT      = "#2C3E50"
C_MUTED     = "#7F8C8D"


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"empresas": [], "ultimo": None}


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


# ══════════════════════════════════════════════════════
#  DIALOGO: NUEVA EMPRESA
# ══════════════════════════════════════════════════════
class NuevaEmpresaDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Nueva Empresa")
        self.geometry("440x240")
        self.resizable(False, False)
        self.result = None
        self.grab_set()
        self.configure(fg_color=C_BG)

        ctk.CTkLabel(self, text="Nombre de la empresa",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=C_TEXT).pack(pady=(25,5))
        self.nombre_entry = ctk.CTkEntry(self, width=340,
                                          placeholder_text="Ej: Ferretería El Tornillo")
        self.nombre_entry.pack(pady=5)

        ctk.CTkLabel(self, text="Ubicación del archivo .spdb",
                     font=ctk.CTkFont(size=11), text_color=C_MUTED).pack(pady=(10,3))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack()
        self.path_entry = ctk.CTkEntry(row, width=260,
                                        placeholder_text="Carpeta donde guardar...")
        self.path_entry.pack(side="left", padx=(0,5))
        ctk.CTkButton(row, text="...", width=40, command=self._pick_folder,
                       fg_color=C_SECONDARY, hover_color=C_PRIMARY).pack(side="left")

        ctk.CTkButton(self, text="Crear empresa", fg_color=C_ACCENT,
                       hover_color="#1E8449", command=self._confirmar).pack(pady=20)

    def _pick_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, folder)

    def _confirmar(self):
        nombre = self.nombre_entry.get().strip()
        folder = self.path_entry.get().strip()
        if not nombre:
            messagebox.showwarning("", "Ingresá el nombre", parent=self)
            return
        if not folder:
            folder = BASE_DIR
        safe = "".join(c for c in nombre if c.isalnum() or c in " _-").strip()
        path = os.path.join(folder, f"{safe}.spdb")
        self.result = (nombre, path)
        self.destroy()


# ══════════════════════════════════════════════════════
#  PANTALLA: SELECTOR DE EMPRESA
# ══════════════════════════════════════════════════════
class EmpresaSelector(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("StockPro — Empresas")
        self.geometry("600x540")
        self.resizable(False, False)
        self.configure(fg_color=C_BG)
        self.selected_db = None
        self._build()
        self._load()

    def _build(self):
        # Header
        h = ctk.CTkFrame(self, fg_color=C_PRIMARY, corner_radius=0, height=90)
        h.pack(fill="x")
        h.pack_propagate(False)
        ctk.CTkLabel(h, text="📦  StockPro",
                     font=ctk.CTkFont(size=28, weight="bold"),
                     text_color="white").pack(pady=(12,2))
        ctk.CTkLabel(h, text="Sistema de Control de Stock",
                     font=ctk.CTkFont(size=11),
                     text_color="#AED6F1").pack()

        card = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=14)
        card.pack(fill="both", expand=True, padx=30, pady=22)

        ctk.CTkLabel(card, text="Bases de datos recientes",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=C_TEXT).pack(pady=(16,6))

        lf = ctk.CTkFrame(card, fg_color="#F4F6F7", corner_radius=8)
        lf.pack(fill="both", expand=True, padx=16, pady=4)

        self.lb = tk.Listbox(lf, font=("Segoe UI", 11),
                              selectbackground=C_SECONDARY, selectforeground="white",
                              bg="#F4F6F7", relief="flat", bd=0,
                              activestyle="none", highlightthickness=0)
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.lb.yview)
        self.lb.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.lb.pack(fill="both", expand=True, padx=6, pady=6)
        self.lb.bind("<Double-Button-1>", lambda e: self._abrir())

        bf = ctk.CTkFrame(card, fg_color="transparent")
        bf.pack(fill="x", padx=16, pady=(6,16))

        ctk.CTkButton(bf, text="✚ Nueva",    width=110,
                       fg_color=C_ACCENT,   hover_color="#1E8449",
                       command=self._nueva).pack(side="left", padx=4)
        ctk.CTkButton(bf, text="📂 Abrir...", width=120,
                       fg_color=C_SECONDARY, hover_color=C_PRIMARY,
                       command=self._abrir_archivo).pack(side="left", padx=4)
        ctk.CTkButton(bf, text="🗑 Quitar",  width=90,
                       fg_color=C_DANGER,   hover_color="#C0392B",
                       command=self._quitar).pack(side="left", padx=4)
        ctk.CTkButton(bf, text="▶  Abrir",   width=100,
                       fg_color=C_PRIMARY,  hover_color=C_SECONDARY,
                       command=self._abrir).pack(side="right", padx=4)

    def _load(self):
        self.cfg = load_config()
        self.lb.delete(0, "end")
        for e in self.cfg["empresas"]:
            ico = "✓" if os.path.exists(e["path"]) else "✗"
            self.lb.insert("end", f"  {ico}  {e['nombre']}   —   {e['path']}")
        # Preseleccionar último
        for i, e in enumerate(self.cfg["empresas"]):
            if e["path"] == self.cfg.get("ultimo"):
                self.lb.selection_set(i)
                break

    def _nueva(self):
        dlg = NuevaEmpresaDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            nombre, path = dlg.result
            init_db(path)
            set_empresa(path, nombre)
            self.cfg["empresas"] = [e for e in self.cfg["empresas"] if e["path"] != path]
            self.cfg["empresas"].insert(0, {"nombre": nombre, "path": path})
            self.cfg["ultimo"] = path
            save_config(self.cfg)
            self._load()
            self._open(path)

    def _abrir_archivo(self):
        path = filedialog.askopenfilename(
            filetypes=[("StockPro DB", "*.spdb"), ("Todos", "*.*")])
        if not path:
            return
        init_db(path)
        emp    = get_empresa(path)
        nombre = emp["nombre"] if emp else os.path.splitext(os.path.basename(path))[0]
        self.cfg["empresas"] = [e for e in self.cfg["empresas"] if e["path"] != path]
        self.cfg["empresas"].insert(0, {"nombre": nombre, "path": path})
        self.cfg["ultimo"] = path
        save_config(self.cfg)
        self._load()
        self._open(path)

    def _abrir(self):
        sel = self.lb.curselection()
        if not sel:
            messagebox.showwarning("", "Seleccioná una empresa primero")
            return
        path = self.cfg["empresas"][sel[0]]["path"]
        if not os.path.exists(path):
            messagebox.showerror("Error", f"Archivo no encontrado:\n{path}")
            return
        self.cfg["ultimo"] = path
        save_config(self.cfg)
        self._open(path)

    def _quitar(self):
        sel = self.lb.curselection()
        if not sel:
            return
        self.cfg["empresas"].pop(sel[0])
        save_config(self.cfg)
        self._load()

    def _open(self, path):
        self.selected_db = path
        self.destroy()

# ══════════════════════════════════════════════════════
#  VENTANA PRINCIPAL
# ══════════════════════════════════════════════════════
class MainWindow(ctk.CTk):
    def __init__(self, db_path):
        super().__init__()
        self.db = db_path
        emp = get_empresa(db_path)
        self.empresa_nombre = emp["nombre"] if emp else "Mi Empresa"

        self.title(f"StockPro — {self.empresa_nombre}")
        self.geometry("1180x720")
        self.minsize(900, 600)
        self.configure(fg_color=C_BG)

        self._build_sidebar()
        self._build_content()
        self._show("dashboard")

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, fg_color=C_PRIMARY,
                                     corner_radius=0, width=200)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo
        logo_f = ctk.CTkFrame(self.sidebar, fg_color=C_SECONDARY,
                                corner_radius=0, height=80)
        logo_f.pack(fill="x")
        logo_f.pack_propagate(False)
        ctk.CTkLabel(logo_f, text="📦 StockPro",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color="white").pack(pady=(18,2))
        ctk.CTkLabel(logo_f, text=self.empresa_nombre[:22],
                     font=ctk.CTkFont(size=10),
                     text_color="#AED6F1").pack()

        self.nav_buttons = {}
        nav_items = [
            ("dashboard",   "🏠  Dashboard"),
            ("inventario",  "📦  Inventario"),
            ("movimientos", "🔄  Movimientos"),
            ("alertas",     "🔔  Alertas"),
            ("estadisticas","📊  Estadísticas"),
            ("categorias",  "🏷  Categorías"),
        ]
        ctk.CTkLabel(self.sidebar, text="MENÚ",
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color="#5D8AA8").pack(pady=(20,4), padx=16, anchor="w")

        for key, label in nav_items:
            btn = ctk.CTkButton(
                self.sidebar, text=label, anchor="w",
                font=ctk.CTkFont(size=13),
                fg_color="transparent", hover_color="#154360",
                text_color="white", height=38, corner_radius=8,
                command=lambda k=key: self._show(k)
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[key] = btn

        # Botón exportar al fondo
        ctk.CTkFrame(self.sidebar, fg_color="#154360",
                      height=1).pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(
            self.sidebar, text="📤  Exportar", anchor="w",
            font=ctk.CTkFont(size=13), height=38,
            fg_color="transparent", hover_color="#154360",
            text_color="#AED6F1", corner_radius=8,
            command=self._exportar_menu
        ).pack(fill="x", padx=10, pady=2)
        ctk.CTkButton(
            self.sidebar, text="📥  Importar Excel", anchor="w",
            font=ctk.CTkFont(size=13), height=38,
            fg_color="transparent", hover_color="#154360",
            text_color="#AED6F1", corner_radius=8,
            command=self._importar_excel
        ).pack(fill="x", padx=10, pady=2)

        ctk.CTkButton(
            self.sidebar, text="❓  Ayuda", anchor="w",
            font=ctk.CTkFont(size=13), height=38,
            fg_color="transparent", hover_color="#154360",
            text_color="#AED6F1", corner_radius=8,
            command=lambda: AyudaWindow(self)
        ).pack(fill="x", padx=10, pady=2)

    def _build_content(self):
        self.content = ctk.CTkFrame(self, fg_color=C_BG, corner_radius=0)
        self.content.pack(side="right", fill="both", expand=True)

    def _show(self, key):
        for k, b in self.nav_buttons.items():
            b.configure(fg_color="#154360" if k == key else "transparent")
        for w in self.content.winfo_children():
            w.destroy()
        frames = {
            "dashboard":    DashboardFrame,
            "inventario":   InventarioFrame,
            "movimientos":  MovimientosFrame,
            "alertas":      AlertasFrame,
            "estadisticas": EstadisticasFrame,
            "categorias":   CategoriasFrame,
        }
        frames[key](self.content, self.db, self.empresa_nombre).pack(
            fill="both", expand=True)

    def _exportar_menu(self):
        win = ctk.CTkToplevel(self)
        win.title("Exportar")
        win.geometry("320x220")
        win.resizable(False, False)
        win.configure(fg_color=C_BG)
        win.grab_set()

        ctk.CTkLabel(win, text="¿Qué querés exportar?",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=C_TEXT).pack(pady=20)

        def exp_inv_excel():
            path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel","*.xlsx")],
                initialfile=f"inventario_{self.empresa_nombre}")
            if path:
                prods = get_productos(self.db)
                export_inventario_excel(prods, self.empresa_nombre, path)
                messagebox.showinfo("✓", f"Exportado:\n{path}")
            win.destroy()

        def exp_inv_pdf():
            path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF","*.pdf")],
                initialfile=f"inventario_{self.empresa_nombre}")
            if path:
                prods = get_productos(self.db)
                export_inventario_pdf(prods, self.empresa_nombre, path)
                messagebox.showinfo("✓", f"Exportado:\n{path}")
            win.destroy()

        def exp_mov_excel():
            path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel","*.xlsx")],
                initialfile=f"movimientos_{self.empresa_nombre}")
            if path:
                movs = get_movimientos(self.db)
                export_movimientos_excel(movs, self.empresa_nombre, path)
                messagebox.showinfo("✓", f"Exportado:\n{path}")
            win.destroy()

        ctk.CTkButton(win, text="📦 Inventario → Excel",
                       fg_color=C_ACCENT, hover_color="#1E8449",
                       command=exp_inv_excel).pack(pady=5)
        ctk.CTkButton(win, text="📦 Inventario → PDF",
                       fg_color=C_SECONDARY, hover_color=C_PRIMARY,
                       command=exp_inv_pdf).pack(pady=5)
        ctk.CTkButton(win, text="🔄 Movimientos → Excel",
                       fg_color=C_WARNING, hover_color="#CA6F1E",
                       command=exp_mov_excel).pack(pady=5)

    def _importar_excel(self):
        path = filedialog.askopenfilename(
            filetypes=[("Excel","*.xlsx *.xls")])
        if not path:
            return
        ok, msg = import_productos_excel(self.db, path)
        (messagebox.showinfo if ok else messagebox.showerror)("Importar", msg)
        self._show("inventario")

# ══════════════════════════════════════════════════════
#  HELPERS UI
# ══════════════════════════════════════════════════════
def stat_card(parent, titulo, valor, color, ancho=160):
    f = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=12, width=ancho)
    f.pack_propagate(False)
    ctk.CTkLabel(f, text=titulo, font=ctk.CTkFont(size=10),
                 text_color=C_MUTED).pack(pady=(14,2))
    ctk.CTkLabel(f, text=str(valor), font=ctk.CTkFont(size=26, weight="bold"),
                 text_color=color).pack()
    ctk.CTkFrame(f, fg_color=color, height=4, corner_radius=2).pack(
        fill="x", padx=0, pady=(8,0), side="bottom")
    return f


# ══════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════
class DashboardFrame(ctk.CTkFrame):
    def __init__(self, parent, db, empresa):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self.db = db

        stats = get_stats_generales(db)

        # Título
        th = ctk.CTkFrame(self, fg_color="transparent")
        th.pack(fill="x", padx=24, pady=(20,10))
        ctk.CTkLabel(th, text="Dashboard",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=C_TEXT).pack(side="left")
        ctk.CTkLabel(th, text=datetime.now().strftime("%d/%m/%Y  %H:%M"),
                     font=ctk.CTkFont(size=11), text_color=C_MUTED).pack(side="right")

        # Tarjetas
        cards_f = ctk.CTkFrame(self, fg_color="transparent")
        cards_f.pack(fill="x", padx=24, pady=6)

        stat_card(cards_f, "Total Productos",
                  stats["total_productos"], C_PRIMARY).pack(side="left", padx=6)
        stat_card(cards_f, "Bajo Stock",
                  stats["bajo_stock"], C_DANGER).pack(side="left", padx=6)
        stat_card(cards_f, "Entradas (total)",
                  stats["total_entradas"], C_ACCENT).pack(side="left", padx=6)
        stat_card(cards_f, "Salidas (total)",
                  stats["total_salidas"], C_WARNING).pack(side="left", padx=6)
        stat_card(cards_f, "Valor Inventario",
                  f"${stats['valor_inventario']:,.2f}", C_SECONDARY, ancho=190).pack(side="left", padx=6)

        # Últimos movimientos
        ctk.CTkLabel(self, text="Últimos movimientos",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=C_TEXT).pack(anchor="w", padx=24, pady=(18,6))

        table_f = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=10)
        table_f.pack(fill="both", expand=True, padx=24, pady=(0,20))

        cols = ("Fecha", "Producto", "Tipo", "Cantidad", "Stock después", "Motivo")
        tree = ttk.Treeview(table_f, columns=cols, show="headings", height=14)
        _style_tree(tree)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=120 if c not in ("Producto","Motivo") else 200)
        scroll_y = ttk.Scrollbar(table_f, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True, padx=4, pady=4)

        movs = get_movimientos(db, limit=100)
        tipo_tag = {"entrada": "entrada", "salida": "salida", "ajuste": "ajuste"}
        tree.tag_configure("entrada", foreground="#27AE60")
        tree.tag_configure("salida",  foreground="#E74C3C")
        tree.tag_configure("ajuste",  foreground="#F39C12")

        for m in movs:
            tree.insert("", "end", values=(
                m["fecha"][:16], m["producto_nombre"],
                m["tipo"].upper(), m["cantidad"],
                m["stock_despues"], m.get("motivo","")
            ), tags=(tipo_tag.get(m["tipo"],""),))


def _style_tree(tree):
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview",
                    background=C_CARD, fieldbackground=C_CARD,
                    foreground=C_TEXT, rowheight=26,
                    font=("Segoe UI", 10))
    style.configure("Treeview.Heading",
                    background=C_PRIMARY, foreground="white",
                    font=("Segoe UI", 10, "bold"), relief="flat")
    style.map("Treeview", background=[("selected", C_SECONDARY)])
    tree.tag_configure("oddrow",  background="#F8FBFD")
    tree.tag_configure("evenrow", background=C_CARD)


# ══════════════════════════════════════════════════════
#  INVENTARIO
# ══════════════════════════════════════════════════════
class InventarioFrame(ctk.CTkFrame):
    def __init__(self, parent, db, empresa):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self.db       = db
        self.empresa  = empresa
        self.sel_id   = None
        self._build()
        self._cargar()

    def _build(self):
        # Encabezado
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(16,8))
        ctk.CTkLabel(top, text="📦  Inventario",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=C_TEXT).pack(side="left")

        # Filtros
        filtros = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=10)
        filtros.pack(fill="x", padx=20, pady=4)

        ctk.CTkLabel(filtros, text="Buscar:",
                     text_color=C_MUTED).pack(side="left", padx=(12,4), pady=10)
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._cargar())
        ctk.CTkEntry(filtros, textvariable=self.search_var,
                     width=220, placeholder_text="Nombre o código...").pack(
                     side="left", padx=4)

        ctk.CTkLabel(filtros, text="Categoría:",
                     text_color=C_MUTED).pack(side="left", padx=(16,4))
        self.cats      = get_categorias(self.db)
        cat_nombres    = ["Todas"] + [c["nombre"] for c in self.cats]
        self.cat_combo = ctk.CTkComboBox(filtros, values=cat_nombres,
                                          width=140, command=lambda v: self._cargar())
        self.cat_combo.set("Todas")
        self.cat_combo.pack(side="left", padx=4)

        self.bajo_stock_var = ctk.BooleanVar()
        ctk.CTkCheckBox(filtros, text="Solo bajo stock",
                         variable=self.bajo_stock_var,
                         command=self._cargar,
                         text_color=C_TEXT).pack(side="left", padx=16)

        # Botones acción
        ctk.CTkButton(filtros, text="✚ Nuevo", width=90,
                       fg_color=C_ACCENT,   hover_color="#1E8449",
                       command=self._nuevo).pack(side="right", padx=6, pady=8)
        ctk.CTkButton(filtros, text="✎ Editar", width=90,
                       fg_color=C_SECONDARY, hover_color=C_PRIMARY,
                       command=self._editar).pack(side="right", padx=4)
        ctk.CTkButton(filtros, text="🗑 Eliminar", width=100,
                       fg_color=C_DANGER,   hover_color="#C0392B",
                       command=self._eliminar).pack(side="right", padx=4)
        ctk.CTkButton(filtros, text="🔄 Movimiento", width=120,
                       fg_color=C_WARNING, hover_color="#CA6F1E",
                       command=self._movimiento).pack(side="right", padx=4)

        # Tabla
        tf = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=10)
        tf.pack(fill="both", expand=True, padx=20, pady=(4,16))

        cols = ("ID","Código","Nombre","Categoría","Stock","Mínimo","Estado",
                "P.Costo","P.Venta","Unidad")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings")
        _style_tree(self.tree)

        widths = {"ID":40,"Código":90,"Nombre":220,"Categoría":110,
                  "Stock":70,"Mínimo":70,"Estado":80,
                  "P.Costo":90,"P.Venta":90,"Unidad":70}
        for c in cols:
            self.tree.heading(c, text=c,
                               command=lambda _c=c: self._sort(_c))
            self.tree.column(c, width=widths.get(c,80),
                              anchor="center" if c not in ("Nombre","Categoría") else "w")

        sy = ttk.Scrollbar(tf, orient="vertical",   command=self.tree.yview)
        sx = ttk.Scrollbar(tf, orient="horizontal",  command=self.tree.xview)
        self.tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side="right",  fill="y")
        sx.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True, padx=4, pady=4)

        self.tree.tag_configure("bajo",  background="#FDEDEC", foreground=C_DANGER)
        self.tree.tag_configure("ok",    background=C_CARD)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-Button-1>", self._doble_clic)

        # Statusbar
        self.status_var = tk.StringVar(value="")
        ctk.CTkLabel(self, textvariable=self.status_var,
                     font=ctk.CTkFont(size=10), text_color=C_MUTED).pack(
                     anchor="e", padx=24, pady=(0,4))

    def _cargar(self, *_):
        for row in self.tree.get_children():
            self.tree.delete(row)
        nombre   = self.search_var.get()
        cat_sel  = self.cat_combo.get()
        cat_id   = next((c["id"] for c in self.cats if c["nombre"] == cat_sel), None)
        bajo     = self.bajo_stock_var.get()
        prods    = get_productos(self.db, nombre, cat_id, bajo)

        for p in prods:
            estado = "⚠ BAJO" if p["stock_actual"] <= p["stock_minimo"] else "✓ OK"
            tag    = "bajo"  if p["stock_actual"] <= p["stock_minimo"] else "ok"
            self.tree.insert("", "end", iid=str(p["id"]), tags=(tag,), values=(
                p["id"], p["codigo"], p["nombre"],
                p.get("categoria_nombre",""), p["stock_actual"],
                p["stock_minimo"], estado,
                f"${p['precio_costo']:.2f}", f"${p['precio_venta']:.2f}",
                p["unidad"]
            ))
        self.status_var.set(f"{len(prods)} productos encontrados")

    def _sort(self, col):
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        try:
            data.sort(key=lambda t: float(t[0].replace("$","").replace(",","")))
        except ValueError:
            data.sort()
        for i, (_, k) in enumerate(data):
            self.tree.move(k, "", i)

    def _on_select(self, _):
        sel = self.tree.selection()
        self.sel_id = int(sel[0]) if sel else None

    def _nuevo(self):
        dlg = ProductoDialog(self, self.db)
        self.wait_window(dlg)
        self._cargar()
        self.cats = get_categorias(self.db)

    def _editar(self):
        if not self.sel_id:
            messagebox.showwarning("", "Seleccioná un producto")
            return
        prod = get_producto_by_id(self.db, self.sel_id)
        dlg  = ProductoDialog(self, self.db, prod)
        self.wait_window(dlg)
        self._cargar()

    def _eliminar(self):
        if not self.sel_id:
            messagebox.showwarning("", "Seleccioná un producto")
            return
        prod = get_producto_by_id(self.db, self.sel_id)
        if messagebox.askyesno("Confirmar",
                                f"¿Desactivar '{prod['nombre']}'?"):
            delete_producto(self.db, self.sel_id)
            self._cargar()

    def _movimiento(self):
        if not self.sel_id:
            messagebox.showwarning("", "Seleccioná un producto")
            return
        prod = get_producto_by_id(self.db, self.sel_id)
        dlg  = MovimientoDialog(self, self.db, prod)
        self.wait_window(dlg)
        self._cargar()

# ── Doble clic
    def _doble_clic(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        sel = self.tree.selection()
        if not sel:
            return
        self.sel_id = int(sel[0])
        prod = get_producto_by_id(self.db, self.sel_id)
        dlg  = MovimientoDialog(self, self.db, prod)
        self.wait_window(dlg)
        self._cargar()

# ══════════════════════════════════════════════════════
#  DIALOGO: PRODUCTO (ALTA / EDICIÓN)
# ══════════════════════════════════════════════════════
class ProductoDialog(ctk.CTkToplevel):
    def __init__(self, parent, db, producto=None):
        super().__init__(parent)
        self.db   = db
        self.prod = producto
        self.title("Nuevo Producto" if not producto else "Editar Producto")
        self.geometry("520x580")
        self.resizable(False, False)
        self.configure(fg_color=C_BG)
        self.grab_set()
        self._build()
        if producto:
            self._fill()

    def _build(self):
        ctk.CTkLabel(self,
                     text="Nuevo Producto" if not self.prod else "Editar Producto",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=C_TEXT).pack(pady=(18,10))

        # Scroll por si la pantalla es chica
        scroll = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=10)
        scroll.pack(fill="both", expand=True, padx=20)

        def campo(label, placeholder="", obligatorio=False):
            f = ctk.CTkFrame(scroll, fg_color="transparent")
            f.pack(fill="x", padx=16, pady=6)
            txt = label + (" *" if obligatorio else "")
            ctk.CTkLabel(f, text=txt, font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=C_TEXT, width=130, anchor="w").pack(side="left")
            e = ctk.CTkEntry(f, placeholder_text=placeholder, height=36)
            e.pack(side="left", fill="x", expand=True)
            return e

        self.e_codigo  = campo("Código",        "Ej: P001",   obligatorio=True)
        self.e_nombre  = campo("Nombre",         "Nombre del producto", obligatorio=True)
        self.e_desc    = campo("Descripción",    "Opcional")

        # Categoría
        f_cat = ctk.CTkFrame(scroll, fg_color="transparent")
        f_cat.pack(fill="x", padx=16, pady=6)
        ctk.CTkLabel(f_cat, text="Categoría", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C_TEXT, width=130, anchor="w").pack(side="left")
        self.cats = get_categorias(self.db)
        self.cat_combo = ctk.CTkComboBox(
            f_cat, values=[c["nombre"] for c in self.cats],
            height=36, font=ctk.CTkFont(size=12))
        self.cat_combo.set(self.cats[0]["nombre"] if self.cats else "")
        self.cat_combo.pack(side="left", fill="x", expand=True)

        self.e_pcosto  = campo("Precio costo",   "0.00")
        self.e_pventa  = campo("Precio venta",   "0.00")
        self.e_minimo  = campo("Stock mínimo",   "0  (avisa cuando baje de este número)")
        self.e_unidad  = campo("Unidad",         "unidad / kg / lt / caja...")

        if not self.prod:
            self.e_stock = campo("Stock inicial", "0  (cuánto hay ahora)")
        else:
            self.e_stock = None

        # Nota campos obligatorios
        ctk.CTkLabel(scroll, text="* Campos obligatorios",
                     font=ctk.CTkFont(size=10), text_color=C_MUTED).pack(
                     anchor="e", padx=16, pady=(0,8))

        ctk.CTkButton(self, text="💾  Guardar producto",
                       fg_color=C_ACCENT, hover_color="#1E8449",
                       height=42, font=ctk.CTkFont(size=13, weight="bold"),
                       command=self._guardar).pack(pady=16, padx=20, fill="x")

    def _fill(self):
        p = self.prod
        self.e_codigo.insert(0, p["codigo"])
        self.e_nombre.insert(0, p["nombre"])
        self.e_desc.insert(0,   p.get("descripcion",""))
        cat = next((c["nombre"] for c in self.cats if c["id"] == p["categoria_id"]), "")
        self.cat_combo.set(cat)
        self.e_pcosto.insert(0, str(p["precio_costo"]))
        self.e_pventa.insert(0, str(p["precio_venta"]))
        self.e_minimo.insert(0, str(p["stock_minimo"]))
        self.e_unidad.insert(0, p["unidad"])

    def _guardar(self):
        codigo = self.e_codigo.get().strip()
        nombre = self.e_nombre.get().strip()
        if not codigo or not nombre:
            messagebox.showwarning("Falta información",
                                    "El Código y el Nombre son obligatorios", parent=self)
            return
        cat_nombre = self.cat_combo.get()
        cat_id = next((c["id"] for c in self.cats if c["nombre"] == cat_nombre), None)
        try:
            pc     = float(self.e_pcosto.get() or 0)
            pv     = float(self.e_pventa.get() or 0)
            minimo = int(self.e_minimo.get()   or 0)
            unidad = self.e_unidad.get().strip() or "unidad"
        except ValueError:
            messagebox.showwarning("Error", "Los precios y stock deben ser números", parent=self)
            return
        if self.prod:
            ok, msg = update_producto(self.db, self.prod["id"], codigo, nombre,
                                       self.e_desc.get(), cat_id, pc, pv, minimo, unidad)
        else:
            try:
                stock = int(self.e_stock.get() or 0)
            except ValueError:
                stock = 0
            ok, msg = add_producto(self.db, codigo, nombre,
                                    self.e_desc.get(), cat_id, pc, pv, stock, minimo, unidad)
        if ok:
            self.destroy()
        else:
            messagebox.showerror("Error", msg, parent=self)


# ══════════════════════════════════════════════════════
#  DIALOGO: MOVIMIENTO
# ══════════════════════════════════════════════════════
class MovimientoDialog(ctk.CTkToplevel):
    def __init__(self, parent, db, producto):
        super().__init__(parent)
        self.db   = db
        self.prod = producto
        self.title(f"Movimiento — {producto['nombre']}")
        self.geometry("420x500")
        self.minsize(420, 380)
        self.resizable(True, False)
        self.configure(fg_color=C_BG)
        self.grab_set()
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text=self.prod["nombre"],
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=C_TEXT).pack(pady=(20,2))
        ctk.CTkLabel(self,
                     text=f"Stock actual: {self.prod['stock_actual']} {self.prod['unidad']}",
                     font=ctk.CTkFont(size=12), text_color=C_MUTED).pack()

        form = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=10)
        form.pack(fill="x", padx=24, pady=16)

        ctk.CTkLabel(form, text="Tipo de movimiento",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C_TEXT).pack(pady=(16,8))

        self.tipo_var = ctk.StringVar(value="entrada")
        row = ctk.CTkFrame(form, fg_color="transparent")
        row.pack(pady=(0,12))
        for t, lbl, col in [("entrada","📥 Entrada", C_ACCENT),
                              ("salida", "📤 Salida",  C_DANGER),
                              ("ajuste", "⚙ Ajuste",  C_WARNING)]:
            ctk.CTkRadioButton(row, text=lbl, variable=self.tipo_var,
                                value=t, text_color=col,
                                font=ctk.CTkFont(size=12)).pack(
                                side="left", padx=14)

        ctk.CTkLabel(form, text="Cantidad",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C_TEXT).pack(pady=(4,4))
        self.e_cant = ctk.CTkEntry(form, width=200, height=38,
                                    font=ctk.CTkFont(size=14),
                                    placeholder_text="Ingresá un número")
        self.e_cant.pack(pady=4)
        self.e_cant.focus()

        ctk.CTkLabel(form, text="En 'Ajuste' ingresá el stock REAL que hay ahora",
                     font=ctk.CTkFont(size=10), text_color=C_MUTED).pack()

        ctk.CTkLabel(form, text="Motivo (opcional)",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C_TEXT).pack(pady=(12,4))
        self.e_motivo = ctk.CTkEntry(form, width=320, height=36,
                                      placeholder_text="Ej: Compra proveedor, venta, etc.")
        self.e_motivo.pack(pady=(0,16))

        ctk.CTkButton(self, text="✔  Registrar movimiento",
                       fg_color=C_PRIMARY, hover_color=C_SECONDARY,
                       height=44, font=ctk.CTkFont(size=13, weight="bold"),
                       command=self._registrar).pack(pady=12, padx=24, fill="x")

    def _registrar(self):
        try:
            cant = int(self.e_cant.get())
            if cant < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Error", "Ingresá un número válido (sin letras ni negativos)", parent=self)
            return
        ok, msg = registrar_movimiento(
            self.db, self.prod["id"],
            self.tipo_var.get(), cant,
            self.e_motivo.get())
        if ok:
            messagebox.showinfo("✓ Listo", msg, parent=self)
            self.destroy()
        else:
            messagebox.showerror("Error", msg, parent=self)


# ══════════════════════════════════════════════════════
#  MOVIMIENTOS
# ══════════════════════════════════════════════════════
class MovimientosFrame(ctk.CTkFrame):
    def __init__(self, parent, db, empresa):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self.db = db
        self._build()
        self._cargar()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(16,8))
        ctk.CTkLabel(top, text="🔄  Movimientos",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=C_TEXT).pack(side="left")

        filtros = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=10)
        filtros.pack(fill="x", padx=20, pady=4)

        ctk.CTkLabel(filtros, text="Tipo:", text_color=C_MUTED).pack(
            side="left", padx=(12,4), pady=10)
        self.tipo_combo = ctk.CTkComboBox(
            filtros,
            values=["Todos","entrada","salida","ajuste"],
            width=120, command=lambda v: self._cargar())
        self.tipo_combo.set("Todos")
        self.tipo_combo.pack(side="left", padx=4)

        ctk.CTkLabel(filtros, text="Desde:", text_color=C_MUTED).pack(
            side="left", padx=(16,4))
        self.e_desde = ctk.CTkEntry(filtros, width=110,
                                     placeholder_text="AAAA-MM-DD")
        self.e_desde.pack(side="left", padx=4)

        ctk.CTkLabel(filtros, text="Hasta:", text_color=C_MUTED).pack(
            side="left", padx=(8,4))
        self.e_hasta = ctk.CTkEntry(filtros, width=110,
                                     placeholder_text="AAAA-MM-DD")
        self.e_hasta.pack(side="left", padx=4)

        ctk.CTkButton(filtros, text="🔍 Filtrar", width=90,
                       fg_color=C_PRIMARY, hover_color=C_SECONDARY,
                       command=self._cargar).pack(side="left", padx=12)
        ctk.CTkButton(filtros, text="↺ Limpiar", width=90,
                       fg_color=C_MUTED, hover_color="#616A6B",
                       command=self._limpiar).pack(side="left")

        tf = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=10)
        tf.pack(fill="both", expand=True, padx=20, pady=(4,16))

        cols = ("Fecha","Código","Producto","Tipo","Cantidad",
                "Stock antes","Stock después","Motivo")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings")
        _style_tree(self.tree)
        widths = {"Fecha":140,"Código":80,"Producto":200,"Tipo":80,
                  "Cantidad":80,"Stock antes":90,"Stock después":100,"Motivo":180}
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=widths.get(c,100),
                              anchor="center" if c not in ("Producto","Motivo") else "w")

        self.tree.tag_configure("entrada", foreground="#27AE60")
        self.tree.tag_configure("salida",  foreground="#E74C3C")
        self.tree.tag_configure("ajuste",  foreground="#F39C12")

        sy = ttk.Scrollbar(tf, orient="vertical",  command=self.tree.yview)
        sx = ttk.Scrollbar(tf, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side="right",  fill="y")
        sx.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True, padx=4, pady=4)

    def _cargar(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        tipo  = self.tipo_combo.get()
        tipo  = None if tipo == "Todos" else tipo
        desde = self.e_desde.get().strip() or None
        hasta = self.e_hasta.get().strip() or None
        movs  = get_movimientos(self.db, tipo=tipo,
                                 fecha_desde=desde, fecha_hasta=hasta)
        for m in movs:
            self.tree.insert("", "end", values=(
                m["fecha"][:16], m["producto_codigo"],
                m["producto_nombre"], m["tipo"].upper(),
                m["cantidad"], m["stock_antes"],
                m["stock_despues"], m.get("motivo","")
            ), tags=(m["tipo"],))

    def _limpiar(self):
        self.tipo_combo.set("Todos")
        self.e_desde.delete(0, "end")
        self.e_hasta.delete(0, "end")
        self._cargar()


# ══════════════════════════════════════════════════════
#  ALERTAS
# ══════════════════════════════════════════════════════
class AlertasFrame(ctk.CTkFrame):
    def __init__(self, parent, db, empresa):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self.db = db
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="🔔  Alertas de Stock Mínimo",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=C_TEXT).pack(anchor="w", padx=24, pady=(20,4))

        prods = get_productos(self.db, solo_bajo_stock=True)

        if not prods:
            ctk.CTkLabel(self,
                         text="✅  ¡Todo el stock está por encima del mínimo!",
                         font=ctk.CTkFont(size=14),
                         text_color=C_ACCENT).pack(pady=60)
            return

        ctk.CTkLabel(self,
                     text=f"⚠  {len(prods)} producto(s) por debajo del stock mínimo",
                     font=ctk.CTkFont(size=12), text_color=C_DANGER).pack(
                     anchor="w", padx=24, pady=(0,8))

        tf = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=10)
        tf.pack(fill="both", expand=True, padx=20, pady=(0,20))

        cols = ("Código","Nombre","Categoría","Stock actual",
                "Stock mínimo","Diferencia","Unidad")
        tree = ttk.Treeview(tf, columns=cols, show="headings")
        _style_tree(tree)
        tree.tag_configure("alerta", background="#FDEDEC", foreground=C_DANGER)

        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=120 if c not in ("Nombre","Categoría") else 180,
                         anchor="center" if c not in ("Nombre","Categoría") else "w")

        for p in prods:
            diff = p["stock_actual"] - p["stock_minimo"]
            tree.insert("", "end", tags=("alerta",), values=(
                p["codigo"], p["nombre"],
                p.get("categoria_nombre",""),
                p["stock_actual"], p["stock_minimo"],
                diff, p["unidad"]
            ))

        sy = ttk.Scrollbar(tf, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sy.set)
        sy.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True, padx=4, pady=4)


# ══════════════════════════════════════════════════════
#  ESTADÍSTICAS
# ══════════════════════════════════════════════════════
class EstadisticasFrame(ctk.CTkFrame):
    def __init__(self, parent, db, empresa):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self.db = db
        self._build()

    def _build(self):
        try:
            import matplotlib
            matplotlib.use("TkAgg")
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from collections import defaultdict
        except ImportError:
            ctk.CTkLabel(self, text="Instalá matplotlib para ver gráficos:\npip install matplotlib",
                         text_color=C_DANGER).pack(pady=60)
            return

        ctk.CTkLabel(self, text="📊  Estadísticas",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=C_TEXT).pack(anchor="w", padx=24, pady=(16,8))

        fig, axes = plt.subplots(1, 3, figsize=(14, 4))
        fig.patch.set_facecolor("#F0F3F4")

        # — Gráfico 1: Movimientos por día —
        datos_dia = get_movimientos_por_dia(self.db, 30)
        entradas  = defaultdict(int)
        salidas   = defaultdict(int)
        for d in datos_dia:
            if d["tipo"] == "entrada":
                entradas[d["dia"]] += d["total"]
            elif d["tipo"] == "salida":
                salidas[d["dia"]]  += d["total"]
        dias = sorted(set(list(entradas.keys()) + list(salidas.keys())))
        ax1  = axes[0]
        ax1.set_facecolor("#FDFEFE")
        if dias:
            x = range(len(dias))
            ax1.bar(x, [entradas.get(d, 0) for d in dias],
                    color="#27AE60", alpha=0.8, label="Entradas")
            ax1.bar(x, [-salidas.get(d, 0) for d in dias],
                    color="#E74C3C", alpha=0.8, label="Salidas")
            ax1.set_xticks(list(x)[::max(1, len(dias)//5)])
            ax1.set_xticklabels([dias[i][-5:] for i in range(0, len(dias), max(1, len(dias)//5))],
                                  rotation=45, fontsize=7)
            ax1.legend(fontsize=8)
        ax1.set_title("Movimientos últimos 30 días", fontsize=10, fontweight="bold")

        # — Gráfico 2: Top productos —
        top   = get_top_productos(self.db, 8)
        ax2   = axes[1]
        ax2.set_facecolor("#FDFEFE")
        if top:
            nombres = [p["nombre"][:15] for p in top]
            totales = [p["total_movido"] for p in top]
            bars    = ax2.barh(nombres, totales, color=C_SECONDARY)
            ax2.bar_label(bars, fontsize=7, padding=2)
            ax2.invert_yaxis()
        ax2.set_title("Top productos con más movimiento", fontsize=10, fontweight="bold")
        ax2.tick_params(labelsize=8)

        # — Gráfico 3: Stock por categoría —
        cats  = get_stock_por_categoria(self.db)
        ax3   = axes[2]
        ax3.set_facecolor("#FDFEFE")
        if cats:
            nombres = [c["nombre"] or "Sin cat." for c in cats]
            totales = [c["cantidad"] for c in cats]
            colores = [C_PRIMARY, C_SECONDARY, C_ACCENT, C_WARNING,
                       C_DANGER, "#8E44AD", "#17A589"]
            ax3.pie(totales, labels=nombres, autopct="%1.0f%%",
                    colors=colores[:len(nombres)], startangle=90,
                    textprops={"fontsize": 8})
        ax3.set_title("Productos por categoría", fontsize=10, fontweight="bold")

        fig.tight_layout(pad=2)
        canvas = FigureCanvasTkAgg(fig, master=self)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=16, pady=(0,16))


# ══════════════════════════════════════════════════════
#  CATEGORÍAS
# ══════════════════════════════════════════════════════
class CategoriasFrame(ctk.CTkFrame):
    def __init__(self, parent, db, empresa):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self.db = db
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="🏷  Categorías",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=C_TEXT).pack(anchor="w", padx=24, pady=(20,8))

        card = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=10)
        card.pack(fill="both", expand=True, padx=24, pady=(0,24))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=16)
        self.e_cat = ctk.CTkEntry(row, width=260,
                                   placeholder_text="Nueva categoría...")
        self.e_cat.pack(side="left", padx=(0,10))
        ctk.CTkButton(row, text="✚ Agregar", width=100,
                       fg_color=C_ACCENT, hover_color="#1E8449",
                       command=self._agregar).pack(side="left")
        ctk.CTkButton(row, text="🗑 Eliminar sel.", width=130,
                       fg_color=C_DANGER, hover_color="#C0392B",
                       command=self._eliminar).pack(side="right")

        lf = ctk.CTkFrame(card, fg_color="#F4F6F7", corner_radius=8)
        lf.pack(fill="both", expand=True, padx=16, pady=(0,16))
        self.lb = tk.Listbox(lf, font=("Segoe UI", 12),
                              selectbackground=C_SECONDARY, selectforeground="white",
                              bg="#F4F6F7", relief="flat", bd=0,
                              activestyle="none", highlightthickness=0)
        self.lb.pack(fill="both", expand=True, padx=8, pady=8)
        self._cargar()

    def _cargar(self):
        self.lb.delete(0, "end")
        self.cats = get_categorias(self.db)
        for c in self.cats:
            self.lb.insert("end", f"  🏷  {c['nombre']}")

    def _agregar(self):
        nombre = self.e_cat.get().strip()
        if not nombre:
            return
        ok, msg = add_categoria(self.db, nombre)
        if ok:
            self.e_cat.delete(0, "end")
            self._cargar()
        else:
            messagebox.showerror("Error", msg)

    def _eliminar(self):
        sel = self.lb.curselection()
        if not sel:
            return
        cat = self.cats[sel[0]]
        ok, msg = delete_categoria(self.db, cat["id"])
        if ok:
            self._cargar()
        else:
            messagebox.showerror("No se puede eliminar", msg)

# ══════════════════════════════════════════════════════
#  AYUDA / ACERCA DE
# ══════════════════════════════════════════════════════
class AyudaWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Ayuda — StockPro")
        self.geometry("600x580")
        self.resizable(False, False)
        self.configure(fg_color=C_BG)
        self.grab_set()
        self._build()

    def _build(self):
        h = ctk.CTkFrame(self, fg_color=C_PRIMARY, corner_radius=0, height=70)
        h.pack(fill="x")
        h.pack_propagate(False)
        ctk.CTkLabel(h, text="❓  ¿Cómo uso StockPro?",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="white").pack(pady=20)

        tabs = ctk.CTkTabview(self, fg_color=C_CARD)
        tabs.pack(fill="both", expand=True, padx=16, pady=12)

        t1 = tabs.add("📋 Pasos rápidos")
        t2 = tabs.add("👤 Acerca de")

        # ── TAB 1: PASOS VISUALES ─────────────────────────
        scroll = ctk.CTkScrollableFrame(t1, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        pasos = [
            ("1️⃣", "Crear un producto",
             "Inventario → botón  ✚ Nuevo\nCompletá código, nombre, categoría y stock inicial.",
             C_ACCENT),
            ("2️⃣", "Registrar una entrada de mercadería",
             "Inventario → seleccioná el producto → botón  🔄 Movimiento\nElegí 'Entrada' e ingresá la cantidad que llegó.",
             C_SECONDARY),
            ("3️⃣", "Registrar una salida",
             "Igual que la entrada pero elegí 'Salida'.\nEl stock se descuenta automáticamente.",
             C_WARNING),
            ("4️⃣", "Ver qué necesita reponerse",
             "Hacé clic en  🔔 Alertas.\nVas a ver todos los productos con poco stock.",
             C_DANGER),
            ("5️⃣", "Corregir el stock si hubo un error",
             "Movimiento → elegí 'Ajuste' → ingresá el stock REAL que hay ahora.\nEl sistema calcula la diferencia solo.",
             C_MUTED),
            ("6️⃣", "Exportar el inventario",
             "Botón  📤 Exportar en el menú lateral.\nPodés guardar en Excel o PDF para imprimir o enviar.",
             C_PRIMARY),
        ]

        for ico, titulo, texto, color in pasos:
            card = ctk.CTkFrame(scroll, fg_color=C_CARD, corner_radius=12)
            card.pack(fill="x", pady=5, padx=4)

            # Franja de color lateral
            ctk.CTkFrame(card, fg_color=color,
                          width=6, corner_radius=6).pack(side="left", fill="y", padx=(0,0))

            body = ctk.CTkFrame(card, fg_color="transparent")
            body.pack(side="left", fill="x", expand=True, padx=12, pady=12)

            top_row = ctk.CTkFrame(body, fg_color="transparent")
            top_row.pack(fill="x")
            ctk.CTkLabel(top_row, text=ico,
                         font=ctk.CTkFont(size=22)).pack(side="left", padx=(0,8))
            ctk.CTkLabel(top_row, text=titulo,
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=color).pack(side="left")
            ctk.CTkLabel(body, text=texto,
                         font=ctk.CTkFont(size=11),
                         text_color=C_TEXT, justify="left",
                         anchor="w", wraplength=460).pack(fill="x", pady=(4,0))

        # ── TAB 2: ACERCA DE ─────────────────────────────
        sf = ctk.CTkFrame(t2, fg_color="transparent")
        sf.pack(fill="both", expand=True)

        ctk.CTkLabel(sf, text="📦",
                     font=ctk.CTkFont(size=48)).pack(pady=(30,4))
        ctk.CTkLabel(sf, text="StockPro  v1.0",
                     font=ctk.CTkFont(size=26, weight="bold"),
                     text_color=C_PRIMARY).pack()
        ctk.CTkLabel(sf, text="Sistema de Control de Stock",
                     font=ctk.CTkFont(size=12), text_color=C_MUTED).pack(pady=(2,24))

        ctk.CTkFrame(sf, fg_color="#D5D8DC", height=1).pack(fill="x", padx=50)

        ctk.CTkLabel(sf, text="Desarrollado por",
                     font=ctk.CTkFont(size=11),
                     text_color=C_MUTED).pack(pady=(20,6))
        ctk.CTkLabel(sf, text="Aparicio Leandro",         
                     font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=C_TEXT).pack()

        info = ctk.CTkFrame(sf, fg_color="#EBF5FB", corner_radius=10)
        info.pack(fill="x", padx=60, pady=16)
        ctk.CTkLabel(info, text="📧  leandroaparicio91@gmail.com",
                     font=ctk.CTkFont(size=12),
                     text_color=C_SECONDARY).pack(pady=(12,2))
        ctk.CTkLabel(info, text="📱  3834579406",
                     font=ctk.CTkFont(size=12),
                     text_color=C_SECONDARY).pack(pady=(2,12))

# ══════════════════════════════════════════════════════
#  PUNTO DE ENTRADA
# ══════════════════════════════════════════════════════
if __name__ == "__main__":
    selector = EmpresaSelector()
    selector.mainloop()
    if selector.selected_db:
        app = MainWindow(selector.selected_db)
        app.mainloop()

