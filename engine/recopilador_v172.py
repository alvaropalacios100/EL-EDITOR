"""EL EDITOR 1.7.2 — punto de entrada estable.
El generador previo crea PORTADA_DEMO.html. No se copia ninguna edición vieja.
"""
import sys
from pathlib import Path
from recopilador_v170 import main

ROOT = Path(__file__).resolve().parent
CANON = ROOT / "PORTADA_DEMO.html"
VERSION = ROOT / "PORTADA_DEMO_v172.html"
BACKUP = ROOT / "PORTADA_ULTIMA_VALIDA.html"

def ejecutar():
    previous = CANON.read_bytes() if CANON.exists() else None
    try:
        main()
        if not CANON.exists():
            raise RuntimeError("No se ha generado PORTADA_DEMO.html")
        content = CANON.read_bytes()
        if len(content) < 100_000 or b"<!doctype html" not in content[:500].lower():
            raise RuntimeError("La portada generada parece incompleta; conservamos la anterior")
        if previous is not None and previous != content:
            BACKUP.write_bytes(previous)
        VERSION.write_bytes(content)  # Única dirección: portada vigente -> alias de versión
        print("EL EDITOR v1.7.2: portada verificada; abrir PORTADA_DEMO.html")
    except Exception:
        if previous is not None:
            CANON.write_bytes(previous)
            VERSION.write_bytes(previous)
        raise

if __name__ == "__main__":
    ejecutar()
