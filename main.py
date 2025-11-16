#!/usr/bin/env python3
"""
Application GUI pour utiliser des LLM en local avec Ollama
"""
import sys
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Local LLM GUI")
    app.setOrganizationName("LocalLLM")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
