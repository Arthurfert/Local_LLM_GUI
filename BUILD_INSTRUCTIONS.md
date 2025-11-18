# Instructions pour créer un exécutable

## Prérequis

1. **Convertir l'icône PNG en ICO** (obligatoire pour Windows)
   - Utilisez un convertisseur en ligne : https://convertio.co/fr/png-ico/
   - Ou avec Pillow :
   ```powershell
   pip install Pillow
   python -c "from PIL import Image; img = Image.open('assets/icon.png'); img.save('assets/icon.ico', format='ICO', sizes=[(256,256)])"
   ```

2. **Installer PyInstaller**
   ```powershell
   pip install pyinstaller
   ```

## Créer l'exécutable

### Méthode 1 : Avec le script automatique (recommandé)
```powershell
python build_exe.py
```

### Méthode 2 : Manuellement avec PyInstaller
```powershell
pyinstaller --name=LocalLLM_GUI --windowed --onefile --icon=assets/icon.ico --add-data="assets;assets" --clean main.py
```

## Résultat

L'exécutable sera créé dans le dossier `dist/` :
- **dist/LocalLLM_GUI.exe** - Votre application avec l'icône intégrée

## Créer un raccourci sur le bureau

1. Copiez `dist/LocalLLM_GUI.exe` où vous voulez
2. Clic droit sur le fichier → "Créer un raccourci"
3. Déplacez le raccourci sur le bureau

L'icône sera automatiquement appliquée au raccourci et visible dans la barre des tâches !

## Notes importantes

- **Format .ico requis** : Windows nécessite un fichier .ico (pas .png) pour l'exécutable
- **Taille recommandée** : 256x256 pixels minimum
- **Ollama requis** : L'exécutable nécessite qu'Ollama soit installé et en cours d'exécution
- **Première compilation** : Peut prendre 1-2 minutes

## Dépannage

**Erreur "icon file not found"**
→ Assurez-vous que `assets/icon.ico` existe

**L'icône n'apparaît pas**
→ Videz le cache d'icônes Windows :
```powershell
ie4uinit.exe -show
```
