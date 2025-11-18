"""
Fenêtre principale de l'application Local LLM GUI
"""
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QTextEdit, QLineEdit, QPushButton, QComboBox, 
                               QLabel, QSplitter, QMessageBox)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QIcon
from core.ollama_client import OllamaClient, OllamaWorker
import os


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ollama_client = OllamaClient()
        self.conversation_history = []
        self.current_response = ""  # Pour accumuler la réponse en streaming
        self.streaming_cursor_position = 0  # Position du curseur pour le streaming
        self.init_ui()
        self.load_models()
        
    def init_ui(self):
        """Initialise l'interface utilisateur"""
        self.setWindowTitle("Local Chatbot")
        self.setGeometry(100, 100, 1000, 700)
        
        # Définir l'icône de la fenêtre
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Appliquer le style moderne
        self.apply_modern_style()
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Barre de sélection du modèle
        model_layout = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(200)
        self.refresh_button = QPushButton("Rafraîchir")
        self.refresh_button.setObjectName("refreshButton")
        self.refresh_button.clicked.connect(self.load_models)
        
        model_layout.addWidget(self.model_combo)
        model_layout.addWidget(self.refresh_button)
        model_layout.addStretch()
        
        main_layout.addLayout(model_layout)
        
        # Zone de chat
        splitter = QSplitter(Qt.Vertical)
        
        # Zone d'affichage de la conversation
        self.chat_display = QTextEdit()
        self.chat_display.setObjectName("chatDisplay")
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Segoe UI", 10))
        self.chat_display.setMarkdown("")  # Activer le support Markdown
        splitter.addWidget(self.chat_display)
        
        # Zone de saisie
        input_widget = QWidget()
        input_layout = QVBoxLayout()
        input_widget.setLayout(input_layout)
        
        # Layout horizontal pour l'input et le bouton envoyer
        input_row_layout = QHBoxLayout()
        
        self.input_field = QTextEdit()
        self.input_field.setMaximumHeight(50)
        self.input_field.setPlaceholderText("Tapez votre message ici...")
        self.input_field.setFont(QFont("Segoe UI", 14))
        
        self.send_button = QPushButton("Envoyer")
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setMinimumHeight(50)
        self.send_button.setMinimumWidth(120)
        
        input_row_layout.addWidget(self.input_field)
        input_row_layout.addWidget(self.send_button)
        
        input_layout.addLayout(input_row_layout)
        
        splitter.addWidget(input_widget)
        splitter.setSizes([500, 200])
        
        main_layout.addWidget(splitter)
        
    def load_models(self):
        """Charge la liste des modèles disponibles"""
        models = self.ollama_client.get_available_models()
        
        self.model_combo.clear()
        if models:
            self.model_combo.addItems(models)
        else:
            QMessageBox.warning(self, "Attention", 
                              "Aucun modèle disponible.\n\n"
                              "Assurez-vous qu'Ollama est installé et en cours d'exécution,\n"
                              "puis téléchargez un modèle avec : ollama pull llama2")
    
    def send_message(self):
        """Envoie un message au LLM"""
        user_message = self.input_field.toPlainText().strip()
        if not user_message:
            return
        
        selected_model = self.model_combo.currentText()
        if not selected_model:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un modèle.")
            return
        
        # Afficher le message de l'utilisateur
        self.append_message("Vous", user_message, "#2196F3")
        
        # Préparer l'affichage de la réponse en streaming
        self.current_response = ""
        self.current_user_message = user_message
        self.append_streaming_message("Assistant", "", "#4CAF50")
        
        self.input_field.clear()
        self.send_button.setEnabled(False)
        
        # Créer un worker thread pour ne pas bloquer l'UI
        self.worker = OllamaWorker(self.ollama_client, selected_model, 
                                   user_message, self.conversation_history, stream=True)
        self.worker.response_chunk.connect(self.handle_response_chunk)
        self.worker.response_ready.connect(self.handle_response)
        self.worker.error_occurred.connect(self.handle_error)
        self.worker.start()
    
    def handle_response_chunk(self, chunk):
        """Gère un chunk de réponse en streaming"""
        self.current_response += chunk
        self.update_streaming_message(self.current_response)
    
    def handle_response(self, response):
        """Gère la réponse complète du LLM"""
        self.send_button.setEnabled(True)
        
        # Ajouter à l'historique
        self.conversation_history.append({
            "role": "user", 
            "content": self.current_user_message
        })
        self.conversation_history.append({
            "role": "assistant", 
            "content": response
        })
    
    def handle_error(self, error_message):
        """Gère les erreurs"""
        self.append_message("Erreur", error_message, "#F44336")
        self.send_button.setEnabled(True)
        QMessageBox.critical(self, "Erreur", error_message)
    
    def append_message(self, sender, message, color):
        """Ajoute un message à la zone de chat"""
        self.chat_display.append(
            f'<p style="margin:10px 0;"><b style="color:{color};">{sender}:</b><br>'
            f'<span style="margin-left:20px;">{message.replace(chr(10), "<br>")}</span></p>'
        )
        # Faire défiler vers le bas
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def append_streaming_message(self, sender, message, color):
        """Ajoute un message initial pour le streaming"""
        self.chat_display.append(
            f'<p style="margin:10px 0;"><b style="color:{color};">{sender}:</b><br>'
            f'<span style="margin-left:20px;"></span></p>'
        )
        
        # Sauvegarder la position actuelle pour les mises à jour
        self.streaming_cursor_position = len(self.chat_display.toPlainText())
        
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def update_streaming_message(self, message):
        """Met à jour le dernier message en streaming"""
        # Nouvelle approche : utiliser directement le curseur pour modifier le texte
        cursor = self.chat_display.textCursor()
        
        # Se positionner à la fin
        cursor.movePosition(cursor.MoveOperation.End)
        
        # Revenir en arrière pour trouver le dernier "Assistant:"
        # et insérer le texte après
        text = self.chat_display.toPlainText()
        last_assistant_pos = text.rfind("Assistant:")
        
        if last_assistant_pos != -1:
            # Calculer combien de caractères après "Assistant:\n"
            content_start = last_assistant_pos + len("Assistant:") + 1
            
            # Sauvegarder le texte avant et après
            before_text = text[:content_start]
            
            # Trouver le prochain "Vous:" ou la fin
            next_user_pos = text.find("Vous:", content_start)
            if next_user_pos == -1:
                next_user_pos = len(text)
            
            after_text = text[next_user_pos:]
            
            # Reconstruire le texte complet
            new_text = before_text + message + "\n\n" + after_text if after_text else before_text + message
            
            # Mettre à jour tout le contenu (pas optimal mais simple)
            self.chat_display.setPlainText(new_text)
            
            # Réappliquer le formatage avec du HTML
            self.reformat_chat()
            
            # Faire défiler vers le bas
            scrollbar = self.chat_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def reformat_chat(self):
        """Reformate tout le chat avec le style HTML et support Markdown"""
        plain_text = self.chat_display.toPlainText()
        
        # Diviser par les messages
        lines = plain_text.split('\n')
        html_output = ""
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith("Vous:"):
                content = line[5:].strip()
                # Récupérer les lignes suivantes jusqu'au prochain label
                i += 1
                while i < len(lines) and not lines[i].strip().startswith(("Vous:", "Assistant:", "Erreur:")):
                    content += "\n" + lines[i]
                    i += 1
                # Convertir markdown en HTML pour le message utilisateur
                html_content = self.markdown_to_html(content)
                html_output += f'<p style="margin:10px 0;"><b style="color:#2196F3;">Vous:</b><br><div style="margin-left:20px;">{html_content}</div></p>'
                continue
                
            elif line.startswith("Assistant:"):
                content = line[10:].strip()
                i += 1
                while i < len(lines) and not lines[i].strip().startswith(("Vous:", "Assistant:", "Erreur:")):
                    content += "\n" + lines[i]
                    i += 1
                # Convertir markdown en HTML pour la réponse de l'assistant
                html_content = self.markdown_to_html(content)
                html_output += f'<p style="margin:10px 0;"><b style="color:#4CAF50;">Assistant:</b><br><div style="margin-left:20px;">{html_content}</div></p>'
                continue
                
            elif line.startswith("Erreur:"):
                content = line[7:].strip()
                i += 1
                while i < len(lines) and not lines[i].strip().startswith(("Vous:", "Assistant:", "Erreur:")):
                    content += "\n" + lines[i]
                    i += 1
                html_content = self.markdown_to_html(content)
                html_output += f'<p style="margin:10px 0;"><b style="color:#F44336;">Erreur:</b><br><div style="margin-left:20px;">{html_content}</div></p>'
                continue
            
            i += 1
        
        self.chat_display.setHtml(html_output)
    
    def markdown_to_html(self, text):
        """Convertit le markdown en HTML avec support des blocs de code"""
        import re
        
        # Échapper les caractères HTML de base d'abord
        html = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Bloc de code avec ``` (multilignes)
        def replace_code_block(match):
            lang = match.group(1) if match.group(1) else ''
            code = match.group(2)
            return f'<pre style="background-color:#1e1e1e; color:#d4d4d4; padding:10px; border-radius:5px; overflow-x:auto;"><code>{code}</code></pre>'
        
        html = re.sub(r'```(\w+)?\n(.*?)```', replace_code_block, html, flags=re.DOTALL)
        
        # Code inline avec `
        html = re.sub(r'`([^`]+)`', r'<code style="background-color:#1e1e1e; color:#d4d4d4; padding:2px 5px; border-radius:3px;">\1</code>', html)
        
        # Gras **texte** ou __texte__
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'__(.+?)__', r'<strong>\1</strong>', html)
        
        # Italique *texte* ou _texte_
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        html = re.sub(r'_(.+?)_', r'<em>\1</em>', html)
        
        # Liens [texte](url)
        html = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2" style="color:#2196F3;">\1</a>', html)
        
        # Titres
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        
        # Listes non ordonnées
        html = re.sub(r'^\- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'^\* (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        
        # Listes ordonnées
        html = re.sub(r'^\d+\. (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        
        # Entourer les listes de <ul> ou <ol>
        html = re.sub(r'(<li>.*?</li>(?:\n<li>.*?</li>)*)', r'<ul>\1</ul>', html, flags=re.DOTALL)
        
        # Retours à la ligne
        html = html.replace('\n', '<br>')
        
        return html
    
    def clear_conversation(self):
        """Efface la conversation"""
        self.chat_display.clear()
        self.conversation_history.clear()
    
    def apply_modern_style(self):
        """Applique un style moderne à l'interface"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #02010A;
            }
            
            QPushButton {
                background-color: #04052E;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 11px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #22007C;
            }
            
            QPushButton:pressed {
                background-color: #04052E;
            }
            
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #757575;
            }
            
            QPushButton#refreshButton {
                background-color: #04052E;
                border-radius: 6px;
                padding: 8px 16px;
            }
            
            QPushButton#refreshButton:hover {
                background-color: #22007C;
            }
            
            QPushButton#refreshButton:pressed {
                background-color: #04052E;
            }
            
            QComboBox {
                border: 1px solid #140152;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: #04052E;
                font-size: 15px;
            }
            
            QComboBox:hover {
                border: 2px solid #2196F3;
            }
            
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
            
            QTextEdit {
                border: 2px solid #0D00A4;
                border-radius: 35px;
                padding: 12px;
                background-color: #04052E;
                font-size: 14px;
            }
            
            QTextEdit:focus {
                border: 2px solid #0D00A4;
            }
            
            QTextEdit#chatDisplay {
                padding: 12px;
                background-color: #02010A;
                font-size: 14px;
                color: #E0E0E0;
            }
            
            QTextEdit#chatDisplay code {
                background-color: #1e1e1e;
                color: #d4d4d4;
                padding: 2px 5px;
                border-radius: 3px;
                font-family: 'Consolas', 'Courier New', monospace;
            }
            
            QTextEdit#chatDisplay pre {
                background-color: #1e1e1e;
                color: #d4d4d4;
                padding: 10px;
                border-radius: 5px;
                overflow-x: auto;
                font-family: 'Consolas', 'Courier New', monospace;
            }
            
            QLabel {
                color: #424242;
                font-size: 11px;
                font-weight: bold;
            }
        """)
