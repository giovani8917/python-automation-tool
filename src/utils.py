import logging
import socket
from datetime import datetime

import psutil

logger = logging.getLogger("main.utils")


def parse_fecha(fecha_str):
    """Parses a date string into a datetime object trying multiple formats."""
    formatos = (
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y",
    )
    for fmt in formatos:
        try:
            return datetime.strptime(fecha_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Formato de fecha inválido: {fecha_str}")


def check_internet_connection(host="8.8.8.8", port=53, timeout=2):
    """Devuelve True si hay conexión a internet"""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception:
        return False


def check_battery_level(threshold=20):
    """Devuelve True si hay batería suficiente o está enchufado, False si está baja."""
    batt = psutil.sensors_battery()
    if not batt:
        # Si no hay batería (PC de escritorio), considera suficiente
        return True
    # Si está enchufado o supera el umbral, OK
    return batt.power_plugged or batt.percent >= threshold


def setup_logging(log_file="automatizacion.log"):
    """Configura el sistema de logging"""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
    )
