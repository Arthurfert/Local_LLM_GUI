#!/usr/bin/env python3
"""
Application GUI pour utiliser des LLM en local avec Ollama
"""
import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Local LLM GUI")
    app.setOrganizationName("LocalLLM")
    
    # Définir l'icône de l'application (pour la barre des tâches)
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
