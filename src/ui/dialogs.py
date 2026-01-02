import tkinter as tk
from tkinter import messagebox
from datetime import datetime

class LogViewer(tk.Toplevel):
    """
    A window for viewing application logs.
    """
    def __init__(self, parent, log_file="automatizacion.log"):
        super().__init__(parent)
        self.title("Visor de Logs")
        self.geometry("600x400")
        
        self.text = tk.Text(self)
        self.text.pack(fill="both", expand=True)
        
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.text.insert("1.0", content)
        except Exception:
            self.text.insert("1.0", f"No se pudo leer {log_file}")
            
        self.text.see("end")

class ItemEditor(tk.Toplevel):
    """
    A dialog for editing automation items (Demos or Wildcards).
    """
    def __init__(self, parent, item, on_save, ask_datetime_callback):
        super().__init__(parent)
        self.item = item
        self.on_save = on_save
        self.ask_datetime_callback = ask_datetime_callback
        
        self.title(f"Editar: {item.name}")
        self.geometry("400x400")
        self.transient(parent)
        self.grab_set()
        
        self._setup_ui()

    def _setup_ui(self):
        r = 0
        def add_row(label, widget):
            nonlocal r
            tk.Label(self, text=label).grid(row=r, column=0, padx=10, pady=5, sticky="e")
            widget.grid(row=r, column=1, padx=10, pady=5, sticky="ew")
            r += 1

        self.var_name = tk.StringVar(value=self.item.name)
        add_row("Nombre:", tk.Entry(self, textvariable=self.var_name, width=30))
        
        self.vars_specific = {}
        if self.item.type == 'wildcard':
            self.vars_specific['min'] = tk.DoubleVar(value=self.item.min_time)
            self.vars_specific['max'] = tk.DoubleVar(value=self.item.max_time)
            add_row("Mínimo (s):", tk.Entry(self, textvariable=self.vars_specific['min']))
            add_row("Máximo (s):", tk.Entry(self, textvariable=self.vars_specific['max']))
            
        elif self.item.type == 'battery_wait':
            self.vars_specific['threshold'] = tk.IntVar(value=self.item.threshold)
            add_row("Nivel Batería (%):", tk.Spinbox(self, from_=0, to=100, textvariable=self.vars_specific['threshold']))
            
        elif self.item.type in ['date_start', 'date_end']:
            self.vars_specific['date'] = tk.StringVar(value=self.item.datetime_target)
            f_date = tk.Frame(self)
            f_date.grid(row=r, column=1, padx=10, pady=5, sticky="ew")
            
            tk.Label(self, text="Fecha:").grid(row=r, column=0, padx=10, pady=5, sticky="e")
            tk.Entry(f_date, textvariable=self.vars_specific['date']).pack(side="left", fill="x", expand=True)
            
            def pick_dt():
                val = self.ask_datetime_callback(initial=self.vars_specific['date'].get())
                if val: self.vars_specific['date'].set(val)
            tk.Button(f_date, text="📅", command=pick_dt, width=3).pack(side="left", padx=2)
            r += 1

        btn_frame = tk.Frame(self)
        btn_frame.grid(row=r, column=0, columnspan=2, pady=20)
        tk.Button(btn_frame, text="Guardar", command=self._save, bg="#DDFFDD").pack(side="left", padx=10)
        tk.Button(btn_frame, text="Cancelar", command=self.destroy).pack(side="left", padx=10)

    def _save(self):
        self.item.name = self.var_name.get()
        if self.item.type == 'wildcard':
            self.item.min_time = self.vars_specific['min'].get()
            self.item.max_time = self.vars_specific['max'].get()
        elif self.item.type == 'battery_wait':
            self.item.threshold = self.vars_specific['threshold'].get()
        elif self.item.type in ['date_start', 'date_end']:
            self.item.datetime_target = self.vars_specific['date'].get()
        
        self.on_save()
        self.destroy()

class DateTimePicker(tk.Toplevel):
    """
    A complex date-time selector window.
    """
    def __init__(self, parent, initial=None):
        super().__init__(parent)
        self.title("Seleccionar Fecha y Hora")
        self.geometry("350x230")
        self.transient(parent)
        self.grab_set()
        
        self.result = None
        
        # Parse initial
        now = datetime.now()
        current = now
        if initial:
            try:
                current = datetime.strptime(initial, "%Y-%m-%d %H:%M:%S")
            except: pass
            
        self._setup_widgets(current)

    def _setup_widgets(self, current):
        # Date
        f_date = tk.LabelFrame(self, text="Fecha")
        f_date.pack(fill="x", padx=10, pady=5)
        
        self.sp_day = tk.Spinbox(f_date, from_=1, to=31, width=3)
        self.sp_day.delete(0, tk.END); self.sp_day.insert(0, current.day)
        self.sp_day.pack(side="left", padx=5)
        
        self.sp_month = tk.Spinbox(f_date, from_=1, to=12, width=3)
        self.sp_month.delete(0, tk.END); self.sp_month.insert(0, current.month)
        self.sp_month.pack(side="left", padx=5)
        
        self.sp_year = tk.Spinbox(f_date, from_=current.year, to=current.year+10, width=5)
        self.sp_year.delete(0, tk.END); self.sp_year.insert(0, current.year)
        self.sp_year.pack(side="left", padx=5)

        # Time
        f_time = tk.LabelFrame(self, text="Hora")
        f_time.pack(fill="x", padx=10, pady=5)
        
        self.sp_h = tk.Spinbox(f_time, from_=0, to=23, width=3, format="%02.0f")
        self.sp_h.delete(0, tk.END); self.sp_h.insert(0, current.hour)
        self.sp_h.pack(side="left", padx=5)
        
        self.sp_m = tk.Spinbox(f_time, from_=0, to=59, width=3, format="%02.0f")
        self.sp_m.delete(0, tk.END); self.sp_m.insert(0, current.minute)
        self.sp_m.pack(side="left", padx=5)
        
        self.sp_s = tk.Spinbox(f_time, from_=0, to=59, width=3, format="%02.0f")
        self.sp_s.delete(0, tk.END); self.sp_s.insert(0, current.second)
        self.sp_s.pack(side="left", padx=5)

        tk.Button(self, text="Confirmar", command=self._confirm, bg="#DDFFDD").pack(pady=10)

    def _confirm(self):
        try:
            d = datetime(int(self.sp_year.get()), int(self.sp_month.get()), int(self.sp_day.get()),
                         int(self.sp_h.get()), int(self.sp_m.get()), int(self.sp_s.get()))
            self.result = d.strftime("%Y-%m-%d %H:%M:%S")
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Fecha inválida")

