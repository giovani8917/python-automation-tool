# Herramienta de Automatización en Python

Este es un proyecto modular en Python diseñado para automatizar tareas repetitivas mediante la grabación y reproducción de interacciones de ratón y teclado. El sistema es capaz de manejar lógica compleja, como esperas condicionales (carga de batería, conexión a internet, horarios específicos) y demostraciones interactivas.

## Características Principales

*   **Grabación Fiel**: Captura movimientos de ratón, clics y pulsaciones de teclas con alta precisión.
*   **Reproducción Inteligente**: El motor de reproducción admite factores de velocidad y repeticiones infinitas.
*   **Módulos "Comodines"**:
    *   **Internet Wait**: Pausa la ejecución hasta que haya conexión a internet.
    *   **Battery Wait**: Pausa hasta que la batería supere un cierto umbral.
    *   **Programación**: Inicia o detiene la ejecución en fechas y horas específicas.
*   **Diseño Modular**: Código organizado en motor, interfaz (UI), modelos y utilidades para facilitar el mantenimiento y la colaboración.

## Estructura del Proyecto

```text
ModularizedProject/
├── src/
│   ├── engine.py   # Lógica central de grabación y reproducción
│   ├── ui.py       # Interfaz gráfica (Tkinter)
│   ├── models.py   # Definiciones de datos (Data Classes)
│   └── utils.py    # Funciones auxiliares
├── main.py         # Punto de entrada de la aplicación
├── requirements.txt
└── README.md
```

## Instalación

1.  Clona este repositorio o descarga el código fuente.
2.  Asegúrate de tener Python instalado (se recomienda 3.8 o superior).
3.  Instala las dependencias necesarias:

    ```bash
    pip install -r requirements.txt
    ```

    > **Nota**: Este proyecto utiliza librerías como `keyboard` y `pyautogui` que pueden requerir permisos de administrador o acceso de accesibilidad en algunos sistemas operativos (especialmente macOS o Linux).

## Uso

Para iniciar la aplicación, ejecuta el archivo `main.py`:

```bash
python main.py
```

### Cómo Contribuir

¡Las contribuciones son bienvenidas! Si deseas mejorar el código:
1.  Haz un *Fork* del proyecto.
2.  Crea una rama con tu nueva funcionalidad (`git checkout -b feature/nueva-funcionalidad`).
3.  Haz *Commit* de tus cambios.
4.  Crea un *Pull Request*.

## Licencia

Este proyecto es de código abierto y está disponible para modificaciones y distribución.
