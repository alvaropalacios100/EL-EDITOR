"""Punto de entrada de la version 1.7.1."""
import sys
from pathlib import Path
from recopilador_v170 import main
if __name__=='__main__':
    main()
    root=Path(__file__).resolve().parent
    if (root/'PORTADA_DEMO_v170.html').exists():
        (root/'PORTADA_DEMO_v171.html').write_bytes((root/'PORTADA_DEMO_v170.html').read_bytes())
