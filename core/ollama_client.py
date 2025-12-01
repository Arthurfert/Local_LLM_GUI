"""
Client pour interagir avec Ollama API
"""
import requests
from PySide6.QtCore import QThread, Signal


class OllamaClient:
    """Client pour communiquer avec l'API Ollama"""
    
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
        
    def get_available_models(self):
        """Récupère la liste des modèles disponibles"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except Exception as e:
            print(f"Erreur lors de la récupération des modèles: {e}")
            return []
    
    def chat_stream(self, model, messages, chunk_callback=None, images=None):
        """
        Utilise l'API chat d'Ollama en mode streaming
        
        Args:
            model: nom du modèle
            messages: liste de messages au format [{role: "user/assistant", content: "..."}]
            chunk_callback: signal appelé pour chaque chunk (optionnel)
            images: liste d'images encodées en base64 (optionnel)
        
        Returns:
            str: réponse complète générée
        """
        try:
            import json
            
            # Si des images sont fournies, les ajouter au dernier message utilisateur
            if images and messages:
                # Trouver le dernier message utilisateur et lui ajouter les images
                for i in range(len(messages) - 1, -1, -1):
                    if messages[i].get('role') == 'user':
                        messages[i]['images'] = images
                        break
            
            payload = {
                "model": model,
                "messages": messages,
                "stream": True
            }
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=120
            )
            
            if response.status_code == 200:
                full_response = ""
                
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            chunk = data.get('message', {}).get('content', '')
                            if chunk:
                                full_response += chunk
                                if chunk_callback:
                                    chunk_callback.emit(chunk)
                        except json.JSONDecodeError:
                            continue
                
                return full_response
            else:
                return f"Erreur: {response.status_code}"
                
        except requests.exceptions.Timeout:
            return "Erreur: La requête a expiré. Le modèle met trop de temps à répondre."
        except Exception as e:
            return f"Erreur: {str(e)}"


class OllamaWorker(QThread):
    """Worker thread pour les requêtes Ollama asynchrones avec streaming"""
    
    response_ready = Signal(str)
    response_chunk = Signal(str)  # Nouveau signal pour les chunks en streaming
    error_occurred = Signal(str)
    
    def __init__(self, client, model, prompt, conversation_history, images=None):
        super().__init__()
        self.client = client
        self.model = model
        self.prompt = prompt
        self.conversation_history = conversation_history
        self.images = images or []  # Liste d'images encodées en base64
    
    def run(self):
        """Exécute la requête dans un thread séparé"""
        try:
            # Construire les messages pour l'API chat
            messages = self.conversation_history.copy()
            messages.append({"role": "user", "content": self.prompt})
            
            # Mode streaming
            full_response = self.client.chat_stream(
                self.model, messages, self.response_chunk, 
                images=self.images if self.images else None
            )
            if full_response.startswith("Erreur:"):
                self.error_occurred.emit(full_response)
            else:
                self.response_ready.emit(full_response)
                
        except Exception as e:
            self.error_occurred.emit(f"Erreur inattendue: {str(e)}")
