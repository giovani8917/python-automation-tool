import tkinter as tk
from tkinter import ttk

class RecordingFrame(tk.LabelFrame):
    """
    UI Component for controlling automation recording.
    """
    def __init__(self, parent, on_toggle_recording):
        super().__init__(parent, text="Grabación", padx=5, pady=5)
        self.on_toggle_recording = on_toggle_recording
        
        tk.Label(self, text="Nombre:").grid(row=0, column=0, sticky="w")
        self.var_name = tk.StringVar()
        self.entry_name = tk.Entry(self, textvariable=self.var_name, width=30)
        self.entry_name.grid(row=0, column=1)
        
        tk.Label(self, text="Eliminar últimos (s):").grid(row=1, column=0, sticky="w")
        self.var_remove_seconds = tk.IntVar(value=3)
        tk.Spinbox(self, from_=0, to=30, textvariable=self.var_remove_seconds, width=5).grid(row=1, column=1, sticky="w")

        self.btn_record = tk.Button(self, text="Iniciar Grabación", command=self.on_toggle_recording)
        self.btn_record.grid(row=0, column=2, rowspan=2, padx=10)

class SequenceListFrame(tk.LabelFrame):
    """
    UI Component for displaying and managing the automation item sequence.
    Supports Drag and Drop reordering.
    """
    def __init__(self, parent, on_drag_start, on_drag_over, on_drop):
        super().__init__(parent, text="Secuencia", padx=5, pady=5)
        
        self.listbox = tk.Listbox(self, height=15, selectmode=tk.SINGLE)
        self.listbox.pack(fill="both", expand=True)
        
        self.listbox.bind("<ButtonPress-1>", on_drag_start)
        self.listbox.bind("<B1-Motion>", on_drag_over)
        self.listbox.bind("<ButtonRelease-1>", on_drop)

class PlaybackFrame(tk.LabelFrame):
    """
    UI Component for controlling automation playback and loop settings.
    """
    def __init__(self, parent, on_play, on_pause, on_stop, on_toggle_infinite):
        super().__init__(parent, text="Controles", padx=5, pady=5)
        
        # Speed
        self.var_speed = tk.DoubleVar(value=1.0)
        tk.Scale(self, from_=0.1, to=2.0, resolution=0.1, orient="horizontal", 
                label="Velocidad", variable=self.var_speed, length=200).pack(fill="x", padx=5)
                
        # Repeat controls
        repeat_frame = tk.Frame(self)
        repeat_frame.pack(fill="x", padx=5, pady=5)
        
        tk.Label(repeat_frame, text="Reproducir:").pack(side="left")
        self.var_repeat_mode = tk.IntVar(value=1) # 1=All, 0=Selected
        tk.Radiobutton(repeat_frame, text="Todo", variable=self.var_repeat_mode, value=1).pack(side="left")
        tk.Radiobutton(repeat_frame, text="Seleccionado", variable=self.var_repeat_mode, value=0).pack(side="left", padx=(0,10))

        tk.Label(repeat_frame, text="Repetir:").pack(side="left")
        self.var_infinite = tk.BooleanVar(value=False)
        tk.Checkbutton(repeat_frame, text="Infinito", variable=self.var_infinite, command=on_toggle_infinite).pack(side="left", padx=5)
        
        tk.Label(repeat_frame, text="Veces:").pack(side="left")
        self.var_repeat_times = tk.IntVar(value=1)
        self.spin_repeat = tk.Spinbox(repeat_frame, from_=1, to=999, textvariable=self.var_repeat_times, width=5)
        self.spin_repeat.pack(side="left")
        
        # Action Buttons
        btn_box = tk.Frame(self)
        btn_box.pack(fill="x", pady=5)
        
        self.btn_play = tk.Button(btn_box, text="Reproducir", command=on_play)
        self.btn_play.pack(side="left", padx=5)
        
        self.btn_pause = tk.Button(btn_box, text="Pausar", command=on_pause)
        self.btn_pause.pack(side="left", padx=5)
        
        self.btn_stop = tk.Button(btn_box, text="Detener", command=on_stop)
        self.btn_stop.pack(side="left", padx=5)
