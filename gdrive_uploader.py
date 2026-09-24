"""
Google Drive Uploader
Sube resultados LIVE organizados por licencia a Google Drive
"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict

try:
    from pydrive2.auth import GoogleAuth
    from pydrive2.drive import GoogleDrive
    GDRIVE_AVAILABLE = True
except ImportError:
    GDRIVE_AVAILABLE = False


class GDriveUploader:
    """Gestor de subida de resultados a Google Drive"""
    
    def __init__(self, license_key: str):
        self.license_key = license_key
        self.drive = None
        self.root_folder_id = None
        self.license_folder_id = None
        
    def authenticate(self) -> bool:
        """
        Autentica con Google Drive.
        Retorna True si la autenticación fue exitosa.
        """
        if not GDRIVE_AVAILABLE:
            return False
            
        try:
            # Configuración de autenticación
            gauth = GoogleAuth()
            
            # Intentar cargar credenciales guardadas
            credentials_file = Path.home() / ".cardchecker_gdrive_credentials.txt"
            
            if credentials_file.exists():
                gauth.LoadCredentialsFile(str(credentials_file))
            
            if gauth.credentials is None:
                # Primera autenticación - abre navegador
                gauth.LocalWebserverAuth()
            elif gauth.access_token_expired:
                # Token expirado - refrescar
                gauth.Refresh()
            else:
                # Token válido
                gauth.Authorize()
            
            # Guardar credenciales para próxima vez
            gauth.SaveCredentialsFile(str(credentials_file))
            
            self.drive = GoogleDrive(gauth)
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
        query = f"title='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        
        file_list = self.drive.ListFile({'q': query}).GetList()
        
        if file_list:
            return file_list[0]['id']
        
        # Crear carpeta si no existe
        folder_metadata = {
            'title': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        if parent_id:
            folder_metadata['parents'] = [{'id': parent_id}]
        
        folder = self.drive.CreateFile(folder_metadata)
        folder.Upload()
        
        return folder['id']
    
    def setup_folders(self) -> bool:
        """
        Crea estructura de carpetas:
        CardChecker/
          ├─ CCR-XXXX-XXXX/
          │   ├─ live_cards.txt
          │   └─ live_cvv_invalid.txt
        
        Returns:
            True si se crearon las carpetas correctamente
        """
        if not self.drive:
            return False
        
        try:
            # Carpeta raíz "CardChecker"
            self.root_folder_id = self._get_or_create_folder("CardChecker")
            
            # Carpeta de la licencia
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
        if not self.drive or not self.license_folder_id:
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
            'title': filename,
            'parents': [{'id': folder_id}]
        }
        
        file = self.drive.CreateFile(file_metadata)
        file.SetContentString(content)
        file.Upload()


def is_gdrive_available() -> bool:
    """Verifica si PyDrive2 está instalado"""
    return GDRIVE_AVAILABLE
