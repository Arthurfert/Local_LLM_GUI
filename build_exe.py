"""
Script pour créer un exécutable Windows avec PyInstaller
"""
import PyInstaller.__main__
import os

# Chemin vers l'icône
icon_path = os.path.join('assets', 'icon.ico')

# Arguments pour PyInstaller
PyInstaller.__main__.run([
    'main.py',                      # Script principal
    '--name=Chatbot',               # Nom de l'exécutable
    '--windowed',                   # Pas de console (interface graphique uniquement)
    '--onefile',                    # Un seul fichier exécutable
    f'--icon={icon_path}',          # Icône de l'application
    '--add-data=assets;assets',     # Inclure le dossier assets
    '--clean',                      # Nettoyer les fichiers temporaires
])
