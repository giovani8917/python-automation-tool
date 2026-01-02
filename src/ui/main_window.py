import logging
import queue
import time
import tkinter as tk
from tkinter import filedialog, messagebox

from .components import PlaybackFrame, RecordingFrame, SequenceListFrame
from .dialogs import DateTimePicker, ItemEditor, LogViewer
from .tray_manager import TrayManager
from ..engine import AutomationEngine
from ..models import DemoItem, Project, WildcardItem

logger = logging.getLogger("main.ui")

class MainWindow:
    """
    Main controller for the Automation Assistant UI.
    Initializes engine, project state, and coordinates modular components.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Asistente de Tutoriales (Modular)")
        self.root.geometry("800x600")
        
        # Initialize Engine and Project
        self.project = Project()
        self.queue = queue.Queue()
        self.engine = AutomationEngine(callback_queue=self.queue)
        self.tray = TrayManager(self.root, on_open=self._restore_from_tray, on_quit=self._quit_app)
        
        # Setup UI Components
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
        
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _setup_layout(self):
        # Main Scrollable Canvas
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
        
        # Components
        self.rec_comp = RecordingFrame(self.scrollable_frame, self._toggle_recording)
        self.rec_comp.pack(fill="x", padx=10, pady=5)
        
        self.list_comp = SequenceListFrame(self.scrollable_frame, self._on_drag_start, self._on_drag_over, self._on_drop)
        self.list_comp.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.play_comp = PlaybackFrame(self.scrollable_frame, self._play_all, self._toggle_pause, self.engine.stop_replay, self._toggle_repeat_spin)
        self.play_comp.pack(fill="x", padx=10, pady=5)
        
        self.status = tk.Label(self.root, text="Listo", relief=tk.SUNKEN, anchor="w")
        self.status.pack(side="bottom", fill="x")

        self._update_ui_state("idle")

    def _update_ui_state(self, state):
        # Delegate button state updates
        if state == "idle":
            # Some buttons depend on var_name in rec_comp
            # We add a trace in __init__? Let's just update here manually for now or use trace
            self.rec_comp.btn_record.config(state="normal" if self.rec_comp.var_name.get() else "disabled")
            self.play_comp.btn_play.config(state="normal")
            self.play_comp.btn_pause.config(state="disabled", text="Pausar")
            self.play_comp.btn_stop.config(state="disabled")
        elif state == "recording":
            self.play_comp.btn_play.config(state="disabled")
            self.play_comp.btn_pause.config(state="disabled")
            self.play_comp.btn_stop.config(state="disabled")
        elif state == "playing":
            self.rec_comp.btn_record.config(state="disabled")
            self.play_comp.btn_play.config(state="disabled")
            self.play_comp.btn_pause.config(state="normal")
            self.play_comp.btn_stop.config(state="normal")

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
        self._build_recent_menu(file_menu)
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

        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Herramientas", menu=tools_menu)
        tools_menu.add_command(label="Ver Logs", command=lambda: LogViewer(self.root))
        tools_menu.add_command(label="Limpiar Logs", command=self._clear_logs)
        tools_menu.add_command(label="Minimizar a Bandeja", command=lambda: self.tray.minimize_to_tray())

    def _setup_keybinds(self):
        self.root.bind("<Control-s>", lambda e: self._save_project())
        # Track name entry to enable/disable record button
        self.rec_comp.var_name.trace_add("write", lambda *args: self._update_ui_state("idle"))

    def _process_queue(self):
        try:
            while True:
                record = self.queue.get_nowait()
                action = record[0]
                if action == "status":
                    self.status.config(text=record[1])
                elif action == "log":
                    level, msg = record[1], record[2]
                    logger.log(getattr(logging, level.upper(), logging.INFO), msg)
                elif action == "recording_finished":
                    self._handle_recording_finished(record[1])
                elif action == "finished":
                    self.status.config(text="Listo")
                    self._restore_from_tray()
                    self._update_ui_state("idle")
        except queue.Empty: pass
        finally: self.root.after(100, self._process_queue)

    def _handle_recording_finished(self, data):
        self.rec_comp.btn_record.config(text="Iniciar Grabación", bg="SystemButtonFace")
        self._update_ui_state("idle")
        self._restore_from_tray()
        
        if data:
            demo = DemoItem(name=self.rec_comp.var_name.get(), data=data)
            self.project.sequence.append(demo)
            self._update_listbox()
            self.rec_comp.var_name.set("")
            messagebox.showinfo("Éxito", f"Grabación '{demo.name}' guardada.")
        else:
            messagebox.showwarning("Aviso", "Grabación vacía")

    def _toggle_recording(self):
        if not self.engine.recording:
            if not self.rec_comp.var_name.get():
                messagebox.showerror("Error", "Ingrese un nombre")
                return
            self.engine.start_recording()
            self.rec_comp.btn_record.config(text="Detener", bg="red")
            self.root.iconify()
            self._update_ui_state("recording")
        else:
            self.engine.stop_recording(remove_last_seconds=self.rec_comp.var_remove_seconds.get())
            self.root.deiconify()

    def _play_all(self):
        if not self.project.sequence: return
        items = self.project.sequence if self.play_comp.var_repeat_mode.get() == 1 else [self.project.sequence[i] for i in self.list_comp.listbox.curselection()]
        if not items: return
        
        self.tray.minimize_to_tray()
        self._update_ui_state("playing")
        time.sleep(0.5)
        self.engine.start_replay(items, speed_factor=self.play_comp.var_speed.get(), 
                                 infinite=self.play_comp.var_infinite.get(), 
                                 repeat_times=self.play_comp.var_repeat_times.get())

    def _toggle_pause(self):
        self.engine.toggle_pause()
        txt = "Reanudar" if self.play_comp.btn_pause.cget("text") == "Pausar" else "Pausar"
        self.play_comp.btn_pause.config(text=txt)

    def _update_listbox(self):
        self.list_comp.listbox.delete(0, tk.END)
        for i, item in enumerate(self.project.sequence):
            disp = f"{i+1}. {item.name} ({item.type})"
            self.list_comp.listbox.insert(tk.END, disp)

    def _toggle_repeat_spin(self):
        state = "disabled" if self.play_comp.var_infinite.get() else "normal"
        self.play_comp.spin_repeat.config(state=state)

    # File Operations
    def _new_project(self):
        if self.project.sequence and messagebox.askyesno("Confirmar", "¿Nuevo proyecto? Cambios sin guardar se perderán."):
            self.project = Project()
            self._update_listbox()

    def _load_project(self):
        fname = filedialog.askopenfilename(
            filetypes=[
                ("Archivos de Proyecto", "*.atp"),
                ("Archivos JSON", "*.json"),
                ("Todos", "*.*"),
            ]
        )
        if fname:
            self._open_recent(fname)

    def _save_project(self):
        if self.project.file_path: self.project.save(self.project.file_path)
        else: self._save_project_as()

    def _save_project_as(self):
        fname = filedialog.asksaveasfilename(
            defaultextension=".atp",
            filetypes=[
                ("Archivos de Proyecto", "*.atp"),
                ("Archivos JSON", "*.json"),
                ("Todos", "*.*"),
            ]
        )
        if fname:
            self.project.save(fname)
            self.status.config(text=f"Guardado como: {fname}")
            self._add_to_recent(fname)

    # Items Management
    def _add_wildcard_dialog(self):
        from tkinter import simpledialog
        min_t = simpledialog.askfloat("Espera", "Min segundos:", initialvalue=1.0)
        max_t = simpledialog.askfloat("Espera", "Max segundos:", initialvalue=2.0)
        if min_t is not None and max_t is not None:
            self.project.sequence.append(WildcardItem(name="Espera Aleatoria", type="wildcard", min_time=min_t, max_time=max_t))
            self._update_listbox()

    def _add_internet_wait(self):
        self.project.sequence.append(WildcardItem(name="Esperar Internet", type="internet_wait"))
        self._update_listbox()

    def _add_battery_wait(self):
        self.project.sequence.append(WildcardItem(name="Esperar Batería", type="battery_wait", threshold=20))
        self._update_listbox()

    def _add_date_wait(self):
        dt = self._ask_datetime()
        if dt:
            self.project.sequence.append(WildcardItem(name="Esperar Fecha", type="date_start", datetime_target=dt))
            self._update_listbox()

    def _add_date_end(self):
        dt = self._ask_datetime()
        if dt:
            self.project.sequence.append(WildcardItem(name="Finalizar en Fecha", type="date_end", datetime_target=dt))
            self._update_listbox()

    def _edit_selected(self):
        sel = self.list_comp.listbox.curselection()
        if sel:
            ItemEditor(self.root, self.project.sequence[sel[0]], self._update_listbox, self._ask_datetime)

    def _duplicate_selected(self):
        sel = self.list_comp.listbox.curselection()
        if sel:
            import copy
            item = copy.deepcopy(self.project.sequence[sel[0]])
            item.name += " (Copia)"
            self.project.sequence.insert(sel[0]+1, item)
            self._update_listbox()

    def _delete_selected(self):
        sel = self.list_comp.listbox.curselection()
        if sel:
            del self.project.sequence[sel[0]]
            self._update_listbox()

    def _delete_all(self):
        if messagebox.askyesno("Eliminar Todo", "¿Seguro?"):
            self.project.sequence.clear()
            self._update_listbox()

    # Drag and Drop
    def _on_drag_start(self, event):
        idx = self.list_comp.listbox.nearest(event.y)
        if 0 <= idx < self.list_comp.listbox.size():
            self.drag_source_index = idx
            self.drag_start_pos = (event.x, event.y)

    def _on_drag_over(self, event):
        if self.drag_source_index is not None:
            self.list_comp.listbox.configure(cursor="exchange")

    def _on_drop(self, event):
        if self.drag_source_index is None: return
        
        # Calculate distance to avoid accidental drops and allow selection
        dist = ((event.x - self.drag_start_pos[0])**2 + (event.y - self.drag_start_pos[1])**2)**0.5
        if dist <= 5:
            # Just a click, ensure item is selected and don't reorder
            self.list_comp.listbox.selection_clear(0, tk.END)
            self.list_comp.listbox.selection_set(self.drag_source_index)
            self.drag_source_index = None
            self.list_comp.listbox.configure(cursor="")
            return

        target = self.list_comp.listbox.nearest(event.y)
        if 0 <= target < len(self.project.sequence) and target != self.drag_source_index:
            item = self.project.sequence.pop(self.drag_source_index)
            self.project.sequence.insert(target, item)
            self._update_listbox()
            self.list_comp.listbox.selection_set(target)
            
        self.drag_source_index = None
        self.list_comp.listbox.configure(cursor="")

    def _move_up(self):
        sel = self.list_comp.listbox.curselection()
        if sel and sel[0] > 0:
            idx = sel[0]
            self.project.sequence[idx], self.project.sequence[idx - 1] = (
                self.project.sequence[idx - 1],
                self.project.sequence[idx],
            )
            self._update_listbox()
            self.list_comp.listbox.selection_set(idx - 1)

    def _move_down(self):
        sel = self.list_comp.listbox.curselection()
        if sel and sel[0] < len(self.project.sequence) - 1:
            idx = sel[0]
            self.project.sequence[idx], self.project.sequence[idx + 1] = (
                self.project.sequence[idx + 1],
                self.project.sequence[idx],
            )
            self._update_listbox()
            self.list_comp.listbox.selection_set(idx + 1)

    def _export_config(self):
        fname = filedialog.asksaveasfilename(defaultextension=".json", title="Exportar Legacy Config")
        if fname:
            data = {"sequence": [item.to_dict() for item in self.project.sequence]}
            import json
            with open(fname, "w") as f:
                json.dump(data, f, indent=2)
            self.status.config(text="Configuración exportada (Legacy)")

    def _import_config(self):
        fname = filedialog.askopenfilename(title="Importar Configuración")
        if fname:
            if not messagebox.askyesno("Confirmar", "¿Reemplazar proyecto actual con importados?"):
                return
            try:
                import json
                with open(fname, "r") as f:
                    data = json.load(f)
                seq = data.get("sequence") or data.get("demonstrations") or []
                new_proj = Project()
                for item_data in seq:
                    itype = item_data.get("type", "demo")
                    if itype == "demo":
                        new_proj.sequence.append(DemoItem(name=item_data.get("name", ""), data=item_data.get("data", [])))
                    else:
                        new_proj.sequence.append(WildcardItem(name=item_data.get("name", ""), type=itype, 
                            min_time=item_data.get("min_time", 0.0), max_time=item_data.get("max_time", 0.0),
                            datetime_target=item_data.get("datetime_target"), threshold=item_data.get("threshold")))
                self.project = new_proj
                self._update_listbox()
            except Exception as e:
                messagebox.showerror("Error Import", str(e))

    def _add_to_recent(self, filepath):
        import json, os
        recent_file = "recent_projects.json"
        recents = []
        if os.path.exists(recent_file):
            try:
                with open(recent_file, "r") as f: recents = json.load(f)
            except: pass
        if filepath in recents: recents.remove(filepath)
        recents.insert(0, filepath)
        recents = recents[:10]
        with open(recent_file, "w") as f: json.dump(recents, f)

    def _build_recent_menu(self, file_menu):
        import json, os
        recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Recientes", menu=recent_menu)
        if os.path.exists("recent_projects.json"):
            try:
                with open("recent_projects.json", "r") as f:
                    recents = json.load(f)
                for path in recents:
                    recent_menu.add_command(label=path, command=lambda p=path: self._open_recent(p))
            except: pass

    def _open_recent(self, filepath):
        if self.project.sequence and not messagebox.askyesno("Confirmar", "¿Abrir? Cambios se perderán."):
            return
        self.project = Project.load(filepath)
        self._update_listbox()

    def _clear_logs(self):
        """
        Clears the application log file.
        """
        try:
            with open("automatizacion.log", "w", encoding="utf-8") as f:
                f.write("")
            messagebox.showinfo("Logs", "Logs limpiados correctamente")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron limpiar los logs: {e}")

    def _ask_datetime(self, initial=None):
        """
        Opens the complex date-time picker dialog and returns the result string.
        """
        picker = DateTimePicker(self.root, initial=initial)
        self.root.wait_window(picker)
        return picker.result

    # Tray & Lifecycle
    def _restore_from_tray(self, icon=None, item=None):
        self.root.after(0, self._restore_safe)
    def _restore_safe(self):
        self.root.deiconify()
        self.root.lift()
        self.tray.stop()

    def _on_closing(self):
        if messagebox.askokcancel("Salir", "¿Cerrar aplicación?"):
            self._quit_app()

    def _quit_app(self, icon=None, item=None):
        self.engine.stop_recording()
        self.engine.stop_replay()
        self.engine.stop_global_listener()
        self.tray.stop()
        self.root.destroy()
        import sys
        sys.exit(0)
