import pytest

def test_imports():
    """
    Verifies that all core dependencies are installed.
    This prevents 'ModuleNotFoundError' when running the application.
    """
    try:
        import pyautogui
        import pynput
        import keyboard
        import PIL
        import pystray
        import psutil
        from src.engine import AutomationEngine
        from src.ui import MainWindow
    except ImportError as e:
        pytest.fail(f"Falta una dependencia crítica: {e}")

def test_engine_init():
    """Checks if the engine can be initialized without errors."""
    from src.engine import AutomationEngine
    engine = AutomationEngine()
    assert engine is not None
    assert engine.recording is False

def test_models_logic():
    """
    Restores the verification of data models.
    """
    from src.models import Project, DemoItem
    proj = Project(name="Test Project")
    item = DemoItem(name="Click Hello", data=[(0, "move", 100, 100, None, False)])
    proj.sequence.append(item)
    
    assert len(proj.sequence) == 1
    data = proj.to_dict()
    assert data["metadata"]["name"] == "Test Project"
    
    # Verify reconstruction
    proj2 = Project.from_dict(data)
    assert proj2.name == "Test Project"
    assert len(proj2.sequence) == 1

