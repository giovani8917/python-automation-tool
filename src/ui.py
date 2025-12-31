import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import queue
import logging
import time
import pyautogui
from .models import Project, DemoItem, WildcardItem
from .engine import AutomationEngine

logger = logging.getLogger("main.ui")


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Asistente de Tutoriales (Modular)")
        self.root.geometry("800x600")
        
        # Initialize Engine and Project
        self.project = Project()
        self.queue = queue.Queue()
        self.engine = AutomationEngine(callback_queue=self.queue)
        
        # Setup UI
        self._setup_menus()
        self._setup_layout()
        self._setup_keybinds()
        
        # Start queue processing
        self.root.after(100, self._process_queue)
        
        # Start global listener
        self.engine.start_global_listener()

        # Drag state
        self.drag_source_index = None
        self.drag_start_pos = None
        
        # Shutdown protocol
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _on_closing(self):
        """Handle application shutdown"""
        if messagebox.askokcancel("Salir", "¿Desea cerrar la aplicación?"):
            logger.info("Cerrando aplicación...")
            self.engine.stop_recording()
            self.engine.stop_replay()
            self.engine.stop_global_listener()
            self.root.destroy()
            import sys
            sys.exit(0)

    def _setup_layout(self):
        # Main Canvas with Scrollbar
        self.main_canvas = tk.Canvas(self.root)
        self.scrollbar = tk.Scrollbar(self.root, orient="vertical", command=self.main_canvas.yview)
        self.scrollable_frame = tk.Frame(self.main_canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        )
        
        self.main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.main_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.main_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # --- Recording Area ---
        record_frame = tk.LabelFrame(self.scrollable_frame, text="Grabación", padx=5, pady=5)
        record_frame.pack(fill="x",padx=10, pady=5)
        
        tk.Label(record_frame, text="Nombre:").grid(row=0, column=0, sticky="w")
        self.var_name = tk.StringVar()
        self.var_name.trace_add("write", lambda *args: self._update_ui_state("idle"))
        tk.Entry(record_frame, textvariable=self.var_name, width=30).grid(row=0, column=1)
        
        tk.Label(record_frame, text="Eliminar últimos (s):").grid(row=1, column=0, sticky="w")
        self.var_remove_seconds = tk.IntVar(value=3)
        tk.Spinbox(record_frame, from_=0, to=30, textvariable=self.var_remove_seconds, width=5).grid(row=1, column=1, sticky="w")

        self.btn_record = tk.Button(record_frame, text="Iniciar Grabación", command=self._toggle_recording)
        self.btn_record.grid(row=0, column=2, rowspan=2, padx=10)
        
        # --- List Area ---
        list_frame = tk.LabelFrame(self.scrollable_frame, text="Secuencia", padx=5, pady=5)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.listbox = tk.Listbox(list_frame, height=15, selectmode=tk.SINGLE)
        self.listbox.pack(fill="both", expand=True)
        
        # Drag and Drop bindings
        self.listbox.bind("<ButtonPress-1>", self._on_drag_start)
        self.listbox.bind("<B1-Motion>", self._on_drag_over)
        self.listbox.bind("<ButtonRelease-1>", self._on_drop)
        
        # --- Controls Area ---
        control_frame = tk.LabelFrame(self.scrollable_frame, text="Controles", padx=5, pady=5)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # Speed
        self.var_speed = tk.DoubleVar(value=1.0)
        tk.Scale(control_frame, from_=0.1, to=2.0, resolution=0.1, orient="horizontal", 
                label="Velocidad", variable=self.var_speed, length=200).pack(fill="x", padx=5)
                
        # Repeat
        repeat_frame = tk.Frame(control_frame)
        repeat_frame.pack(fill="x", padx=5, pady=5)
        
        # Play Mode (Sequence vs Selected)
        tk.Label(repeat_frame, text="Reproducir:").pack(side="left")
        self.var_repeat_mode = tk.IntVar(value=1) # Default 1=All
        tk.Radiobutton(repeat_frame, text="Todo", variable=self.var_repeat_mode, value=1).pack(side="left")
        tk.Radiobutton(repeat_frame, text="Seleccionado", variable=self.var_repeat_mode, value=0).pack(side="left", padx=(0,10))

        # Repetitions
        tk.Label(repeat_frame, text="Repetir:").pack(side="left")
        self.var_infinite = tk.BooleanVar(value=False)
        tk.Checkbutton(repeat_frame, text="Infinito", variable=self.var_infinite, command=self._toggle_repeat_spin).pack(side="left", padx=5)
        
        tk.Label(repeat_frame, text="Veces:").pack(side="left")
        self.var_repeat_times = tk.IntVar(value=1)
        self.spin_repeat = tk.Spinbox(repeat_frame, from_=1, to=999, textvariable=self.var_repeat_times, width=5)
        self.spin_repeat.pack(side="left")
        
        # Buttons
        btn_box = tk.Frame(control_frame)
        btn_box.pack(fill="x", pady=5)
        
        self.btn_play = tk.Button(btn_box, text="Reproducir", command=self._play_all)
        self.btn_play.pack(side="left", padx=5)
        
        self.btn_pause = tk.Button(btn_box, text="Pausar", command=self._toggle_pause)
        self.btn_pause.pack(side="left", padx=5)
        
        self.btn_stop = tk.Button(btn_box, text="Detener", command=self.engine.stop_replay)
        self.btn_stop.pack(side="left", padx=5)
        
        # Initial state
        self._update_ui_state("idle")

    def _update_ui_state(self, state):
        if state == "idle":
            self.btn_record.config(state="normal" if self.var_name.get() else "disabled")
            self.btn_play.config(state="normal")
            self.btn_pause.config(state="disabled", text="Pausar")
            self.btn_stop.config(state="disabled")
            
        elif state == "recording":
            self.btn_play.config(state="disabled")
            self.btn_pause.config(state="disabled")
            self.btn_stop.config(state="disabled")
            
        elif state == "playing":
            self.btn_record.config(state="disabled")
            self.btn_play.config(state="disabled")
            self.btn_pause.config(state="normal")
            self.btn_stop.config(state="normal")
        
        # --- Status Bar ---
        self.status = tk.Label(self.root, text="Listo", relief=tk.SUNKEN, anchor="w")
        self.status.pack(side="bottom", fill="x")

    def _setup_menus(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Archivo", menu=file_menu)
        file_menu.add_command(label="Nuevo", command=self._new_project)
        file_menu.add_command(label="Abrir...", command=self._load_project)
        file_menu.add_separator()
        file_menu.add_command(label="Guardar", command=self._save_project)
        file_menu.add_command(label="Guardar Como...", command=self._save_project_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exportar Configuración", command=self._export_config)
        file_menu.add_command(label="Importar Configuración", command=self._import_config)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self._on_closing)
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edición", menu=edit_menu)
        
        wc_menu = tk.Menu(edit_menu, tearoff=0)
        edit_menu.add_cascade(label="Agregar Comodín...", menu=wc_menu)
        wc_menu.add_command(label="Tiempo (Aleatorio)", command=self._add_wildcard_dialog)
        wc_menu.add_command(label="Esperar Internet", command=self._add_internet_wait)
        wc_menu.add_command(label="Esperar Batería", command=self._add_battery_wait)
        wc_menu.add_command(label="Esperar Fecha", command=self._add_date_wait)
        wc_menu.add_command(label="Finalizar en Fecha", command=self._add_date_end)
        
        edit_menu.add_separator()
        edit_menu.add_command(label="Editar Seleccionado", command=self._edit_selected)
        edit_menu.add_command(label="Duplicar", command=self._duplicate_selected)
        edit_menu.add_command(label="Mover Arriba", command=self._move_up)
        edit_menu.add_command(label="Mover Abajo", command=self._move_down)
        edit_menu.add_separator()
        edit_menu.add_command(label="Eliminar", command=self._delete_selected)
        edit_menu.add_command(label="Eliminar Todo", command=self._delete_all)

        # Recent Projects Logic in Menu
        def build_recent_menu():
            import json
            import os
            recent_menu = tk.Menu(file_menu, tearoff=0)
            file_menu.add_cascade(label="Recientes", menu=recent_menu)
            
            if os.path.exists("recent_projects.json"):
                try:
                    with open("recent_projects.json", 'r') as f:
                        recents = json.load(f)
                    for path in recents:
                        recent_menu.add_command(label=path, command=lambda p=path: self._open_recent(p))
                except: pass
                
        build_recent_menu()
        
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Herramientas", menu=tools_menu)
        tools_menu.add_command(label="Ver Logs", command=self._show_log_window)
        tools_menu.add_command(label="Limpiar Logs", command=self._clear_logs)
        tools_menu.add_command(label="Minimizar a Bandeja", command=self._minimize_to_tray)

    def _setup_keybinds(self):
        self.root.bind("<Control-s>", lambda e: self._save_project())

    # Combined UI Loop
    def _process_queue(self):
        try:
            while True:
                record = self.queue.get_nowait()
                action = record[0]
                
                if action == "status":
                    self.status.config(text=record[1])
                elif action == "log":
                    level, msg = record[1], record[2]
                    logger_lvl = getattr(logging, level.upper(), logging.INFO)
                    logger.log(logger_lvl, msg)
                elif action == "recording_finished":
                    self._handle_recording_finished(record[1])
                elif action == "finished":
                    self.status.config(text="Listo")
                    self._restore_from_tray()
                    self._update_ui_state("idle")
                
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._process_queue)

    def _handle_recording_finished(self, data):
        # Restore UI
        self.btn_record.config(text="Iniciar Grabación", bg="SystemButtonFace")
        self._update_ui_state("idle")
        
        if hasattr(self, '_restore_from_tray'):
            self._restore_from_tray()
        else:
            self.root.deiconify()
            
        # Save demo logic
        if data:
            demo = DemoItem(name=self.var_name.get(), data=data)
            self.project.sequence.append(demo)
            self._update_listbox()
            self.var_name.set("") # Clear name
            messagebox.showinfo("Éxito", f"Grabación '{demo.name}' guardada.")
        else:
             messagebox.showwarning("Aviso", "Grabación vacía o muy corta")

    def _toggle_repeat_spin(self):
        if self.var_infinite.get():
            self.spin_repeat.config(state="disabled")
        else:
            self.spin_repeat.config(state="normal")
            
    def _toggle_recording(self):
        if not self.engine.recording:
            if not self.var_name.get():
                messagebox.showerror("Error", "Ingrese un nombre")
                return
            self.engine.start_recording()
            self.btn_record.config(text="Detener Grabación", bg="red")
            
            # Minimize to tray/iconify
            logger.info("🔽 Minimizando ventana automáticamente al iniciar grabación...")
            self.root.iconify()
            self._update_ui_state("recording")
        else:
            # Pass remove_seconds
            rem_sec = self.var_remove_seconds.get()
            self.engine.stop_recording(remove_last_seconds=rem_sec)
            
            # Restore window logic is handled in _handle_recording_finished callback
            # But we can forcefully ensure it pops up:
            logger.info("🔼 Restaurando ventana al terminar grabación...")
            self.root.deiconify()

    def _play_all(self):
        if not self.project.sequence:
            return
        
        # Determine sequence to play based on repeat mode
        speed = self.var_speed.get()
        infinite = self.var_infinite.get()
        repeats = self.var_repeat_times.get()
        mode = self.var_repeat_mode.get() 
        
        items_to_play = []
        if mode == 0: # Selected
             sel = self.listbox.curselection()
             if not sel:
                 messagebox.showwarning("Aviso", "Seleccione un elemento para reproducir")
                 return
             items_to_play = [self.project.sequence[sel[0]]]
        else: # All
             items_to_play = self.project.sequence
             
        if not items_to_play:
            return

        # Minimal V9 delay logic
        # V9: minimize -> sleep 0.5 -> start
        self._minimize_to_tray()
        self._update_ui_state("playing")
        time.sleep(0.5)
        
        self.engine.start_replay(items_to_play, speed_factor=speed, infinite=infinite, repeat_times=repeats)

    def _toggle_pause(self):
        self.engine.toggle_pause()
        # Toggle text
        current_text = self.btn_pause.cget("text")
        new_text = "Reanudar" if current_text == "Pausar" else "Pausar"
        self.btn_pause.config(text=new_text)

    def _update_listbox(self):
        self.listbox.delete(0, tk.END)
        for i, item in enumerate(self.project.sequence):
            # Display nicer name
            disp = f"{i+1}. {item.name}"
            if item.type == 'wildcard':
                 disp += f" (Espera {item.min_time}-{item.max_time}s)"
            elif item.type == 'internet_wait':
                 disp += " (Internet)"
            elif item.type == 'battery_wait':
                 disp += f" (Batería > {item.threshold}%)"
            elif 'date' in item.type:
                 prefix = "Inicio: " if item.type == "date_start" else "Fin: "
                 disp += f" ({prefix}{item.datetime_target})"
                 
            self.listbox.insert(tk.END, disp)
            


    def _delete_selected(self):
        sel = self.listbox.curselection()
        if sel:
            del self.project.sequence[sel[0]]
            self._update_listbox()

    def _delete_all(self):
        if not self.project.sequence: return
        if messagebox.askyesno("Confirmar", "¿Eliminar TODOS los elementos de la secuencia?"):
            self.project.sequence.clear()
            self._update_listbox()

    def _add_wildcard_dialog(self):
        # Time Wildcard
        win = tk.Toplevel(self.root)
        win.title("Agregar Comodín de Tiempo")
        
        tk.Label(win, text="Min (s):").grid(row=0, column=0)
        v_min = tk.DoubleVar(value=1.0)
        tk.Entry(win, textvariable=v_min).grid(row=0, column=1)
        
        tk.Label(win, text="Max (s):").grid(row=1, column=0)
        v_max = tk.DoubleVar(value=2.0)
        tk.Entry(win, textvariable=v_max).grid(row=1, column=1)
        
        def add():
            self.project.sequence.append(WildcardItem(
                name="Wildcard Tiempo",
                type="wildcard",
                min_time=v_min.get(),
                max_time=v_max.get()
            ))
            self._update_listbox()
            win.destroy()
            
        tk.Button(win, text="Agregar", command=add).grid(row=2, column=0, columnspan=2)

    def _add_internet_wait(self):
        self.project.sequence.append(WildcardItem(
            name="Esperar Internet",
            type="internet_wait"
        ))
        self._update_listbox()

    def _add_battery_wait(self):
        threshold = tk.simpledialog.askinteger("Batería", "Esperar hasta nivel %:", minvalue=1, maxvalue=100, initialvalue=20)
        if threshold:
            self.project.sequence.append(WildcardItem(
                name="Esperar Batería",
                type="battery_wait",
                threshold=threshold
            ))
            self._update_listbox()

    def _add_date_wait(self):
        date_str = self._ask_datetime()
        if date_str:
            self.project.sequence.append(WildcardItem(
                name="Esperar Fecha",
                type="date_start",
                datetime_target=date_str
            ))
            self._update_listbox()

    def _duplicate_selected(self):
        sel = self.listbox.curselection()
        if sel:
            import copy
            item = copy.deepcopy(self.project.sequence[sel[0]])
            item.name += " (Copia)"
            self.project.sequence.insert(sel[0]+1, item)
            self._update_listbox()

    def _move_up(self):
        sel = self.listbox.curselection()
        if sel and sel[0] > 0:
            idx = sel[0]
            self.project.sequence[idx], self.project.sequence[idx-1] = \
                self.project.sequence[idx-1], self.project.sequence[idx]
            self._update_listbox()
            self.listbox.selection_set(idx-1)

    def _move_down(self):
        sel = self.listbox.curselection()
        if sel and sel[0] < len(self.project.sequence) - 1:
            idx = sel[0]
            self.project.sequence[idx], self.project.sequence[idx+1] = \
                self.project.sequence[idx+1], self.project.sequence[idx]
            self._update_listbox()
            self.listbox.selection_set(idx+1)

    def _edit_selected(self):
        sel = self.listbox.curselection()
        if not sel: return
        
        item = self.project.sequence[sel[0]]
        
        # Create Unified Edit Window
        win = tk.Toplevel(self.root)
        win.title(f"Editar: {item.name}")
        win.geometry("400x300")
        win.transient(self.root)
        win.grab_set()
        
        # Grid layout helper
        r = 0
        def add_row(label, widget):
            nonlocal r
            tk.Label(win, text=label).grid(row=r, column=0, padx=10, pady=5, sticky="e")
            widget.grid(row=r, column=1, padx=10, pady=5, sticky="ew")
            r += 1

        # 1. Common: Name
        var_name = tk.StringVar(value=item.name)
        add_row("Nombre:", tk.Entry(win, textvariable=var_name, width=30))
        
        # 2. Type Specific
        vars_specific = {}
        
        if item.type == 'wildcard':
            vars_specific['min'] = tk.DoubleVar(value=item.min_time)
            vars_specific['max'] = tk.DoubleVar(value=item.max_time)
            add_row("Mínimo (s):", tk.Entry(win, textvariable=vars_specific['min']))
            add_row("Máximo (s):", tk.Entry(win, textvariable=vars_specific['max']))
            
        elif item.type == 'battery_wait':
            vars_specific['threshold'] = tk.IntVar(value=item.threshold)
            add_row("Nivel Batería (%):", tk.Spinbox(win, from_=0, to=100, textvariable=vars_specific['threshold']))
            
        elif item.type in ['date_start', 'date_end']:
            vars_specific['date'] = tk.StringVar(value=item.datetime_target)
            
            # Container to hold entry + button
            f_date = tk.Frame(win)
            f_date.grid(row=r, column=1, padx=10, pady=5, sticky="ew")
            
            tk.Label(win, text="Fecha (YYYY-MM-DD ...):").grid(row=r, column=0, padx=10, pady=5, sticky="e")
            
            e_date = tk.Entry(f_date, textvariable=vars_specific['date'])
            e_date.pack(side="left", fill="x", expand=True)
            
            def pick_dt():
                val = self._ask_datetime(initial=vars_specific['date'].get())
                if val: vars_specific['date'].set(val)
                
            tk.Button(f_date, text="📅", command=pick_dt, width=3).pack(side="left", padx=2)
            
            r+=1
            tk.Label(win, text="Formato: 2024-12-31 23:59:59", font=("Arial", 8), fg="gray").grid(row=r, column=1, sticky="w", padx=10)
            r+=1
        
        elif item.type == 'demo':
             # Maybe show stats?
             stats = f"Eventos: {len(item.data)}"
             tk.Label(win, text=stats, fg="gray").grid(row=r, column=1, sticky="w", padx=10)
             r+=1

        # 3. Actions
        btn_frame = tk.Frame(win)
        btn_frame.grid(row=r, column=0, columnspan=2, pady=20)
        
        def save():
            # Update Common
            item.name = var_name.get()
            
            # Update Specific
            if item.type == 'wildcard':
                item.min_time = vars_specific['min'].get()
                item.max_time = vars_specific['max'].get()
            elif item.type == 'battery_wait':
                item.threshold = vars_specific['threshold'].get()
            elif item.type in ['date_start', 'date_end']:
                item.datetime_target = vars_specific['date'].get()
                
            self._update_listbox()
            win.destroy()
            
        tk.Button(btn_frame, text="Guardar", command=save, bg="#DDFFDD").pack(side="left", padx=10)
        tk.Button(btn_frame, text="Cancelar", command=win.destroy).pack(side="left", padx=10)
        
        self._update_listbox()

    def _add_date_end(self):
        date_str = self._ask_datetime()
        if date_str:
            self.project.sequence.append(WildcardItem(
                name="Finalizar en Fecha",
                type="date_end",
                datetime_target=date_str
            ))
            self._update_listbox()

    def _save_project(self):
        fname = filedialog.asksaveasfilename(defaultextension=".json")
        if fname:
            self.project.save(fname)
            self.status.config(text=f"Guardado: {fname}")
            self._add_to_recent(fname)
            
    def _new_project(self):
        # V9 Strict Parity: Check unsaved changes with Yes/No/Cancel
        if self.project.sequence:
            response = messagebox.askyesnocancel(
                "Proyecto sin guardar",
                "El proyecto actual tiene cambios sin guardar.\n\n¿Desea guardar antes de crear un nuevo proyecto?"
            )
            
            if response is True:  # Yes
                # Try to save
                if self.project.file_path:
                     self.project.save(self.project.file_path)
                     self.status.config(text=f"Guardado: {self.project.file_path}")
                else:
                     fname = filedialog.asksaveasfilename(defaultextension=".atp", filetypes=[("Archivos de Proyecto", "*.atp"), ("JSON", "*.json")])
                     if fname:
                         self.project.save(fname)
                         self._add_to_recent(fname)
                         self.status.config(text=f"Guardado: {fname}")
                     else:
                         # User cancelled save dialog, so we cancel New Project
                         return
            elif response is None: # Cancel
                return
            # False (No) falls through to reset
            
        self.project = Project() # Reset to default "Proyecto Sin Nombre"
        self._update_listbox()
        self.status.config(text="Nuevo proyecto creado")

    def _minimize_to_tray(self):
        # V9 Parity: Use withdraw() to hide from taskbar completely
        self.root.withdraw()
        
        if not hasattr(self, 'tray_icon'):
            from PIL import Image, ImageDraw
            import pystray
            
            # Create a simple icon
            image = Image.new('RGB', (64, 64), color = (0, 0, 0))
            d = ImageDraw.Draw(image)
            d.rectangle((16,16,48,48), fill=(200,200,200)) # Simple square
            
            menu = pystray.Menu(
                pystray.MenuItem('Abrir', self._restore_from_tray),
                pystray.MenuItem('Salir', self._quit_app)
            )
            
            self.tray_icon = pystray.Icon("name", image, "Asistente Automatización", menu)
            
        # Run tray icon in separate thread so it doesn't block
        import threading
        if not self.tray_icon.visible:
             threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _restore_from_tray(self, icon=None, item=None):
        self.root.after(0, self._restore_window_thread_safe)
        
    def _restore_window_thread_safe(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        if hasattr(self, 'tray_icon'):
             self.tray_icon.stop()
             del self.tray_icon

    def _quit_app(self, icon=None, item=None):
        if hasattr(self, 'tray_icon'):
             self.tray_icon.stop()
        self.root.after(0, self.root.destroy)
        import sys
        sys.exit(0)

    def _show_log_window(self):
        win = tk.Toplevel(self.root)
        win.title("Visor de Logs")
        win.geometry("600x400")
        
        text = tk.Text(win)
        text.pack(fill="both", expand=True)
        
        try:
            with open("automatizacion.log", "r", encoding="utf-8") as f:
                content = f.read()
                text.insert("1.0", content)
        except Exception:
            text.insert("1.0", "No se pudo leer el archivo de log.")
            
        text.see("end")

    def _clear_logs(self):
        try:
            with open("automatizacion.log", "w", encoding="utf-8") as f:
                f.write("")
            messagebox.showinfo("Logs", "Logs limpiados correctamente")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron limpiar los logs: {e}")
        
    def _add_to_recent(self, filepath):
        # Load existing
        import json
        import os
        recent_file = "recent_projects.json"
        recents = []
        if os.path.exists(recent_file):
            try:
                with open(recent_file, 'r') as f:
                    recents = json.load(f)
            except: pass
            
        if filepath in recents:
            recents.remove(filepath)
        recents.insert(0, filepath)
        recents = recents[:10] # Keep last 10
        
        with open(recent_file, 'w') as f:
            json.dump(recents, f)
        
        # Update menu? (MVP: requires restart or dynamic update method)
    
    def _open_recent(self, filepath):
        if self.project.sequence:
             if not messagebox.askyesno("Confirmar", "¿Abrir proyecto? Cambios actuales se perderán."):
                 return
        self.project = Project.load(filepath)
        self._update_listbox()
        self.status.config(text=f"Cargado: {filepath}")

    # Override save/load to use recents
    def _save_project(self):
        # Save Current (if path exists)
        if self.project.file_path:
            self.project.save(self.project.file_path)
            self.status.config(text=f"Guardado: {self.project.file_path}")
            self._add_to_recent(self.project.file_path)
        else:
            self._save_project_as()

    def _save_project_as(self):
        fname = filedialog.asksaveasfilename(defaultextension=".atp", 
                                            filetypes=[("Archivos de Proyecto", "*.atp"), ("Archivos JSON", "*.json"), ("Todos", "*.*")])
        if fname:
            self.project.save(fname)
            self.status.config(text=f"Guardado como: {fname}")
            self._add_to_recent(fname)
            
    def _load_project(self):
        fname = filedialog.askopenfilename(filetypes=[("Archivos de Proyecto", "*.atp"), ("Archivos JSON", "*.json"), ("Todos", "*.*")])
        if fname:
            self._open_recent(fname)

    def _export_config(self):
        # Export just raw data for legacy compatibility
        fname = filedialog.asksaveasfilename(defaultextension=".json", title="Exportar Legacy Config")
        if fname:
            data = {
                "sequence": [item.to_dict() for item in self.project.sequence]
            }
            import json
            with open(fname, 'w') as f:
                json.dump(data, f, indent=2)
            self.status.config(text="Configuración exportada (Legacy)")

    def _import_config(self):
        # Import generic JSON data
        fname = filedialog.askopenfilename(title="Importar Configuración")
        if fname:
            if not messagebox.askyesno("Confirmar", "¿Reemplazar proyecto actual con datos importados?"):
                return
            
            try:
                import json
                with open(fname, 'r') as f:
                    data = json.load(f)
                
                # Try to find sequence data in various keys
                seq = data.get('sequence') or data.get('demonstrations') or []
                
                new_proj = Project() 
                # Reconstruct (reuse Project.from_dict logic somewhat or manual)
                # Quick manual reconstruction for robustness
                for item_data in seq:
                     # Check type
                     itype = item_data.get("type", "demo")
                     if itype == "demo":
                         new_proj.sequence.append(DemoItem(
                             name=item_data.get("name", ""),
                             data=item_data.get("data", [])
                         ))
                     else:
                         new_proj.sequence.append(WildcardItem(
                             name=item_data.get("name", ""),
                             type=itype,
                             min_time=item_data.get("min_time", 0.0),
                             max_time=item_data.get("max_time", 0.0),
                             datetime_target=item_data.get("datetime_target"),
                             threshold=item_data.get("threshold")
                         ))
                
                self.project = new_proj
                self._update_listbox()
                self.status.config(text=f"Importado: {fname}")
                
            except Exception as e:
                messagebox.showerror("Error Import", str(e))

    # --- Drag and Drop Logic ---
    def _on_drag_start(self, event):
        clicked_index = self.listbox.nearest(event.y)
        if 0 <= clicked_index < self.listbox.size():
            self.drag_source_index = clicked_index
            self.drag_start_pos = (event.x, event.y)
        else:
            self.drag_source_index = None
            self.drag_start_pos = None

    def _on_drag_over(self, event):
        if self.drag_source_index is not None and self.drag_start_pos:
             distance = ((event.x - self.drag_start_pos[0])**2 + (event.y - self.drag_start_pos[1])**2)**0.5
             if distance > 5:
                 self.listbox.configure(cursor="exchange")
                 target_index = self.listbox.nearest(event.y)
                 
                 if 0 <= target_index < self.listbox.size():
                     self.listbox.selection_clear(0, tk.END)
                     self.listbox.selection_set(target_index)
                     if self.drag_source_index < self.listbox.size():
                         self.listbox.selection_set(self.drag_source_index)

    def _on_drop(self, event):
        if self.drag_source_index is None: return
        
        # Calculate distance to avoid accidental drops
        if self.drag_start_pos:
            dist = ((event.x - self.drag_start_pos[0])**2 + (event.y - self.drag_start_pos[1])**2)**0.5
            if dist <= 5:
                # Just clicking, clear selection mess
                self.listbox.selection_clear(0, tk.END)
                self.listbox.selection_set(self.drag_source_index)
                self.drag_source_index = None
                self.listbox.configure(cursor="")
                return

        target_index = self.listbox.nearest(event.y)
        
        # Original Logic: Zones
        listbox_height = self.listbox.winfo_height()
        item_height = listbox_height / max(self.listbox.size(), 1) if self.listbox.size() > 0 else 20
        top_zone = item_height * 0.3
        bottom_zone = listbox_height - (item_height * 0.5)
        
        final_index = target_index
        
        # Zone modification
        if event.y <= top_zone and target_index == 0:
            final_index = 0
        elif (event.y >= bottom_zone and target_index == self.listbox.size() - 1) or \
             (target_index == self.listbox.size() - 1 and event.y > listbox_height - item_height):
            final_index = len(self.project.sequence)
        else:
            # Standard insert
            if self.drag_source_index < target_index:
                final_index = target_index + 1
            else:
                 final_index = target_index + 1 # Consistent with original code logic "insert AFTER target" generally
                 if self.drag_source_index > target_index:
                     final_index = target_index # Wait, if dragging UP, we want to be ABOVE target?
                     # Original says: "Arrastrando hacia arriba: insertar después del target" -> target_index + 1
                     # But then pop/insert math.
                     # Let's stick strictly to original's final_index calc:
                     # "if drag_source_index < target_index: final_index = target_index + 1"
                     # "else: final_index = target_index + 1" 
                     # Wait, both are +1 in original snippet I read?
                     # Let's re-read snippet lines 2261-2266
                     # 2261: if drag_source_index < target_index:
                     # 2263:    final_index = target_index + 1
                     # 2264: else:
                     # 2266:    final_index = target_index + 1
                     # So it always inserts AFTER?
                     pass
            
        # Move
        if 0 <= self.drag_source_index < len(self.project.sequence):
             item = self.project.sequence.pop(self.drag_source_index)
             if self.drag_source_index < final_index:
                 final_index -= 1
             
             if final_index > len(self.project.sequence): final_index = len(self.project.sequence)
             if final_index < 0: final_index = 0
             
             self.project.sequence.insert(final_index, item)
             self._update_listbox()
             self.listbox.selection_set(final_index)
             
        self.drag_source_index = None
        self.listbox.configure(cursor="")

    def _ask_datetime(self, initial=None):
        from datetime import datetime
        dt_window = tk.Toplevel(self.root)
        dt_window.title("Seleccionar Fecha y Hora")
        dt_window.geometry("350x230")
        dt_window.transient(self.root)
        dt_window.grab_set()
        
        result = [None]
        
        # Parse initial
        now = datetime.now()
        if initial:
            try:
                current = datetime.strptime(initial, "%Y-%m-%d %H:%M:%S")
            except:
                current = now
        else:
             current = now
             
        # Frames
        frame_date = tk.LabelFrame(dt_window, text="Fecha")
        frame_date.pack(fill="x", padx=10, pady=5)
        
        frame_time = tk.LabelFrame(dt_window, text="Hora")
        frame_time.pack(fill="x", padx=10, pady=5)
        
        # Date Widgets
        tk.Label(frame_date, text="Día").pack(side="left")
        sp_day = tk.Spinbox(frame_date, from_=1, to=31, width=3)
        sp_day.delete(0,"end"); sp_day.insert(0, current.day)
        sp_day.pack(side="left", padx=2)
        
        tk.Label(frame_date, text="Mes").pack(side="left")
        sp_month = tk.Spinbox(frame_date, from_=1, to=12, width=3)
        sp_month.delete(0,"end"); sp_month.insert(0, current.month)
        sp_month.pack(side="left", padx=2)
         
        tk.Label(frame_date, text="Año").pack(side="left")
        sp_year = tk.Spinbox(frame_date, from_=current.year, to=current.year+10, width=5)
        sp_year.delete(0,"end"); sp_year.insert(0, current.year)
        sp_year.pack(side="left", padx=2)
        
        # Time Widgets
        tk.Label(frame_time, text="H").pack(side="left")
        sp_h = tk.Spinbox(frame_time, from_=0, to=23, width=3, format="%02.0f")
        sp_h.delete(0,"end"); sp_h.insert(0, current.hour)
        sp_h.pack(side="left", padx=2)
        
        tk.Label(frame_time, text="M").pack(side="left")
        sp_m = tk.Spinbox(frame_time, from_=0, to=59, width=3, format="%02.0f")
        sp_m.delete(0,"end"); sp_m.insert(0, current.minute)
        sp_m.pack(side="left", padx=2)
        
        tk.Label(frame_time, text="S").pack(side="left")
        sp_s = tk.Spinbox(frame_time, from_=0, to=59, width=3, format="%02.0f")
        sp_s.delete(0,"end"); sp_s.insert(0, current.second)
        sp_s.pack(side="left", padx=2)
        
        def confirm():
            try:
                d = datetime(
                    int(sp_year.get()), int(sp_month.get()), int(sp_day.get()),
                    int(sp_h.get()), int(sp_m.get()), int(sp_s.get())
                )
                result[0] = d.strftime("%Y-%m-%d %H:%M:%S")
                dt_window.destroy()
            except ValueError:
                messagebox.showerror("Error", "Fecha inválida")
                
        tk.Button(dt_window, text="Aceptar", command=confirm, bg="#DDFFDD").pack(pady=10)
        
        self.root.wait_window(dt_window)
        return result[0]
