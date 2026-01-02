# Guía de Contribución

¡Gracias por tu interés en contribuir a este proyecto! Queremos que colaborar sea lo más fácil y transparente posible.

## Cómo Contribuir

1.  **Reportar Errores**: Si encuentras un bug, por favor abre un 'Issue' describiendo el problema, pasos para reproducirlo y el comportamiento esperado.
2.  **Sugerir Mejoras**: Si tienes ideas para nuevas funcionalidades, abre un 'Issue' con la etiqueta "enhancement" o "feature request".
3.  **Pull Requests**:
    *   Haz un *Fork* del repositorio.
    *   Crea una rama descriptiva para tus cambios (`git checkout -b fix/error-carga`).
    *   Asegúrate de que tu código sigue el estilo existente.
    *   Envía el *Pull Request* explicando tus cambios claramente.

## Estilo de Código

*   Sigue [PEP 8](https://www.python.org/dev/peps/pep-0008/) para el código Python.
*   Usa nombres de variables y funciones descriptivos en inglés o español (mantén la consistencia con el código existente).
*   Usa nombres de variables y funciones descriptivos en inglés o español (mantén la consistencia con el código existente).

## Comandos de Desarrollo

Para mantener la calidad del código, este proyecto utiliza herramientas modernas:

### 1. Formato y Estilo (Linting)
Antes de subir cambios, asegúrate de que tu código cumpla con las reglas de estilo:

```bash
# Correr chequeo de errores
ruff check .

# Correr formateo automático (arregla el código por ti)
ruff format .
```

### 2. Pruebas (Testing)
Asegúrate de no romper funcionalidades existentes corriendo los tests:

```bash
pytest
```


Al contribuir, aceptas que tu código sea distribuido bajo la misma licencia que este proyecto.
