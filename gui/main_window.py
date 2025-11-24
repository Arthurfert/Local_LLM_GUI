"""
Fenêtre principale de l'application Local LLM GUI
"""
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QTextEdit, QLineEdit, QPushButton, QComboBox, 
                               QLabel, QSplitter, QMessageBox, QListWidget, 
                               QListWidgetItem, QSizePolicy, QMenu, QApplication)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QFont, QIcon, QTextDocument
from core.ollama_client import OllamaClient, OllamaWorker
import os


class ChatBubble(QWidget):
    """Widget personnalisé pour afficher une bulle de chat"""
    def __init__(self, text, sender, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(self.layout)
        
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.message_label.setText(text)
        self.message_label.setFont(QFont("Segoe UI", 10))
        self.message_label.setOpenExternalLinks(True)
        
        is_user = sender == "Vous"
        
        # Style
        bg_color = "#2B5278" if is_user else "#383838"
        text_color = "#FFFFFF"
        border_radius = "15px"
        
        # On applique le style directement au label
        self.message_label.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: {border_radius};
                border: 1px solid {bg_color};
                padding: 6px 12px;
            }}
        """)
        
        # Gestion de la largeur max (augmenté pour les grands écrans)
        self.message_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
        # Menu contextuel
        self.message_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self.message_label.customContextMenuRequested.connect(self.show_context_menu)
        
        if is_user:
            self.layout.addStretch()
            self.layout.addWidget(self.message_label)
        else:
            self.layout.addWidget(self.message_label)
            self.layout.addStretch()
            
        self.resize_label()

    def show_context_menu(self, pos):
        menu = QMenu(self)
        
        # Styles pour le menu
        menu.setStyleSheet("""
            QMenu {
                background-color: #2D2D2D;
                color: #FFFFFF;
                border: 1px solid #3E3E3E;
                border-radius: 10px;
            }
            QMenu::item {
                padding: 5px 20px;
                border-radius: 10px;
            }
            QMenu::item:selected {
                background-color: #4CAF50;
                border-radius: 10px;
            }
        """)
        
        # Action: Copier tout
        copy_all_action = menu.addAction("Copier le message")
        
        # Action: Copier la sélection
        copy_selection_action = None
        if self.message_label.hasSelectedText():
            copy_selection_action = menu.addAction("Copier la sélection")
            
        # Action: Copier le code
        html_content = self.message_label.text()
        code_blocks = self.extract_code_blocks(html_content)
        
        copy_code_actions = {}
        if code_blocks:
            menu.addSeparator()
            if len(code_blocks) == 1:
                action = menu.addAction("Copier le code")
                copy_code_actions[action] = code_blocks[0]
            else:
                for i, code in enumerate(code_blocks):
                    preview = code.strip().split('\n')[0][:30]
                    if len(preview) < len(code.strip().split('\n')[0]):
                        preview += "..."
                    action = menu.addAction(f"Copier le code {i+1} ({preview})")
                    copy_code_actions[action] = code

        # Afficher le menu
        action = menu.exec(self.message_label.mapToGlobal(pos))
        
        clipboard = QApplication.clipboard()
        
        if action == copy_all_action:
            # Convertir HTML en texte brut
            doc = QTextDocument()
            doc.setHtml(html_content)
            clipboard.setText(doc.toPlainText())
            
        elif copy_selection_action and action == copy_selection_action:
            clipboard.setText(self.message_label.selectedText())
            
        elif action in copy_code_actions:
            clipboard.setText(copy_code_actions[action])

    def extract_code_blocks(self, html):
        import re
        import html as html_lib
        
        blocks = []
        # Regex pour trouver les blocs de code dans le HTML généré
        matches = re.finditer(r'<pre[^>]*><code>(.*?)</code></pre>', html, re.DOTALL)
        
        for match in matches:
            code = html_lib.unescape(match.group(1))
            blocks.append(code)
            
        return blocks

    def resize_label(self):
        """Ajuste la largeur max du label en fonction du contenu"""
        doc = QTextDocument()
        doc.setDefaultFont(self.message_label.font())
        doc.setDocumentMargin(0)
        doc.setHtml(self.message_label.text())
        
        # On calcule la largeur idéale avec une limite haute de 1800px
        doc.setTextWidth(1800)
        
        # On ajoute une marge pour le padding (12px * 2) + marge de sécurité
        new_width = int(doc.idealWidth()) + 40
        self.message_label.setMaximumWidth(min(1800, new_width))

    def update_text(self, text):
        self.message_label.setText(text)
        self.resize_label()


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
        
        # Zone d'affichage de la conversation
        self.chat_display = QListWidget()
        self.chat_display.setObjectName("chatDisplay")
        self.chat_display.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.chat_display.setSelectionMode(QListWidget.NoSelection)
        main_layout.addWidget(self.chat_display, 1)
        
        # Zone de saisie
        input_widget = QWidget()
        input_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        input_layout = QVBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_widget.setLayout(input_layout)
        
        # Layout horizontal pour l'input et le bouton envoyer
        input_row_layout = QHBoxLayout()
        input_row_layout.setContentsMargins(0, 0, 0, 0)
        
        self.input_field = QTextEdit()
        self.input_field.setMaximumHeight(50)
        self.input_field.setPlaceholderText("Tapez votre message ici...")
        self.input_field.setFont(QFont("Segoe UI", 14))
        
        self.send_button = QPushButton("Envoyer")
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setMaximumHeight(50)
        self.send_button.setMinimumWidth(120)
        
        input_row_layout.addWidget(self.input_field)
        input_row_layout.addWidget(self.send_button)
        
        input_layout.addLayout(input_row_layout)
        
        main_layout.addWidget(input_widget, 0)
        
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
                              "puis téléchargez un modèle avec : ollama pull (llama2)")
    
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
        """Méthode interne pour insérer le widget de la bulle"""
        # Créer le widget personnalisé
        bubble_widget = ChatBubble(content, sender)
        
        # Créer l'item de liste
        item = QListWidgetItem(self.chat_display)
        item.setSizeHint(bubble_widget.sizeHint())
        
        # Ajouter l'item et définir le widget
        self.chat_display.addItem(item)
        self.chat_display.setItemWidget(item, bubble_widget)
        
        # Scroll vers le bas
        self.chat_display.scrollToBottom()

    def append_streaming_message(self, sender, message, color):
        """Initialise le streaming"""
        self._insert_bubble(sender, "...")

    def update_streaming_message(self, message):
        """Met à jour le dernier message en streaming"""
        html_content = self.markdown_to_html(message)
        
        # Récupérer le dernier item
        count = self.chat_display.count()
        if count > 0:
            item = self.chat_display.item(count - 1)
            widget = self.chat_display.itemWidget(item)
            if isinstance(widget, ChatBubble):
                widget.update_text(html_content)
                # Ajuster la taille de l'item si nécessaire
                item.setSizeHint(widget.sizeHint())
                self.chat_display.scrollToBottom()

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
        
        # Envelopper dans un span pour forcer l'interprétation HTML par Qt
        return f"<span>{html}</span>"

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
            QListWidget#chatDisplay {
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
