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
        splitter.setSizes([600, 100])
        
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
        """Ajoute un message complet à la zone de chat avec style de bulle"""
        html_content = self.markdown_to_html(message)
        self._insert_bubble(sender, html_content)
        
    def _insert_bubble(self, sender, content):
        """Méthode interne pour insérer le HTML de la bulle"""
        is_user = sender == "Vous"
        
        # Couleurs et alignement
        align = "right" if is_user else "left"
        bg_color = "#2B5278" if is_user else "#2D2D2D" # Bleu pour user, Gris pour assistant
        text_color = "#FFFFFF"
        
        # Structure HTML pour la bulle
        html = f"""
        <div align="{align}">
            <table style="background-color: {bg_color}; color: {text_color}; border-radius: 50px; margin: 5px;">
                <tr>
                    <td style="padding: 10px;">
                        {content}
                    </td>
                </tr>
            </table>
        </div>
        <br>
        """
        
        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertHtml(html)
        
        # Scroll vers le bas
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def append_streaming_message(self, sender, message, color):
        """Initialise le streaming"""
        # On marque la position actuelle
        self.last_msg_start_pos = self.chat_display.document().characterCount()
        # On insère un vide pour commencer
        self.update_streaming_message("...")

    def update_streaming_message(self, message):
        """Met à jour le dernier message en streaming"""
        html_content = self.markdown_to_html(message)
        
        # Construire le HTML de la bulle (Assistant)
        html = f"""
        <div align="left">
            <table style="background-color: #383838; color: #FFFFFF; border-radius: 10px; margin: 5px;">
                <tr>
                    <td style="padding: 10px;">
                        {html_content}
                    </td>
                </tr>
            </table>
        </div>
        <br>
        """
        
        if not hasattr(self, 'last_msg_start_pos'):
            self.last_msg_start_pos = self.chat_display.document().characterCount()
            
        cursor = self.chat_display.textCursor()
        cursor.setPosition(self.last_msg_start_pos - 1)
        cursor.movePosition(cursor.MoveOperation.End, cursor.MoveMode.KeepAnchor)
        cursor.insertHtml(html)
        
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def markdown_to_html(self, text):
        """Convertit le markdown en HTML avec support des blocs de code"""
        import re
        import html as html_lib
        
        # Échapper les caractères HTML de base d'abord
        text_safe = html_lib.escape(text)
        
        # Dictionnaire pour stocker les blocs de code temporairement
        code_blocks = {}
        
        def save_code_block(match):
            key = f"__CODE_BLOCK_{len(code_blocks)}__"
            code = match.group(1)
            # On préserve les retours à la ligne dans le bloc de code
            html_block = f'<pre style="background-color:#121212; color:#d4d4d4; padding:10px; border-radius:5px;"><code>{code}</code></pre>'
            code_blocks[key] = html_block
            return key
            
        # Extraire et protéger les blocs de code ```...```
        text_safe = re.sub(r'```(?:\w+)?\n?(.*?)```', save_code_block, text_safe, flags=re.DOTALL)
        
        # Code inline avec `
        html = re.sub(r'`([^`]+)`', r'<code style="background-color:#121212; color:#f3f6f4; padding:2px 5px; border-radius:20px;">\1</code>', text_safe)
        
        # Gras **texte**
        html = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', html)
        
        # Italique *texte*
        html = re.sub(r'\*(.+?)\*', r'<i>\1</i>', html)
        
        # Ligne horizontale ---
        html = re.sub(r'^\s*---\s*$', r'<hr style="border: 0; border-top: 1px solid #555; margin: 10px 0;">', html, flags=re.MULTILINE)
        
        # Titres
        html = re.sub(r'^#### (.+)$', r'<h4 style="color:#4CAF50; margin-top:5px; margin-bottom:5px;">\1</h4>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3 style="color:#4CAF50; margin-top:10px; margin-bottom:5px;">\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2 style="color:#4CAF50; margin-top:15px; margin-bottom:10px;">\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1 style="color:#4CAF50; margin-top:20px; margin-bottom:10px;">\1</h1>', html, flags=re.MULTILINE)
        
        # Listes
        html = re.sub(r'^\- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        
        # Retours à la ligne (remplacer \n par <br>)
        html = html.replace('\n', '<br>')
        
        # Nettoyage : supprimer les <br> superflus après les balises de bloc
        # Cela évite les doubles sauts de ligne après les titres, les listes, etc.
        html = re.sub(r'(</h[1-6]>|</li>|<hr[^>]*>)\s*<br>', r'\1', html)
        
        # Restaurer les blocs de code
        for key, block in code_blocks.items():
            html = html.replace(key, block)
        
        return html

    def clear_conversation(self):
        """Efface la conversation"""
        self.chat_display.clear()
        self.conversation_history.clear()
    
    def apply_modern_style(self):
        """Applique un style moderne à l'interface"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1E1E1E;
            }
            
            QWidget {
                color: #FFFFFF;
                font-family: 'Segoe UI', sans-serif;
            }

            /* Zone de chat principale */
            QTextEdit#chatDisplay {
                background-color: #1E1E1E;
                border: none;
                padding: 10px;
            }
            
            /* Zone de saisie */
            QTextEdit {
                background-color: #2D2D2D;
                border: 1px solid #3E3E3E;
                border-radius: 15px;
                padding: 10px;
                color: white;
                font-size: 14px;
            }
            
            QTextEdit:focus {
                border: 1px solid #4CAF50;
            }
            
            /* Boutons */
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #45a049;
            }
            
            QPushButton:disabled {
                background-color: #2D2D2D;
                color: #757575;
            }
            
            /* ComboBox (Liste des modèles) */
            QComboBox {
                background-color: #2D2D2D;
                border: 1px solid #3E3E3E;
                border-radius: 8px;
                padding: 5px 10px;
                color: white;
            }
            
            QComboBox::drop-down {
                border: none;
            }
            
            /* Scrollbar */
            QScrollBar:vertical {
                border: none;
                background: #1E1E1E;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #424242;
                min-height: 20px;
                border-radius: 5px;
            }
        """)
