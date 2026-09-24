"""Verificar información del token OAuth"""
import pickle
from pathlib import Path
from datetime import datetime

token_file = Path('gdrive_token.pickle')
if token_file.exists():
    with open(token_file, 'rb') as f:
        creds = pickle.load(f)
    
    print('=' * 60)
    print('  INFORMACIÓN DEL TOKEN OAUTH')
    print('=' * 60)
    print()
    print(f'✅ Tiene refresh_token: {creds.refresh_token is not None}')
    print(f'✅ Token válido: {creds.valid}')
    
    if hasattr(creds, 'expiry') and creds.expiry:
        print(f'⏰ Expira: {creds.expiry}')
        print(f'   (Se renovará automáticamente)')
    
    print()
    
    if creds.refresh_token:
        print('🎉 PERFECTO: El token tiene refresh_token')
        print('   → Se renovará automáticamente cada hora')
        print('   → Durará indefinidamente (mientras esté activo)')
        print('   → Solo expira si:')
        print('     • Revovas acceso manualmente')
        print('     • Cambias contraseña de Gmail')
        print('     • 6 meses sin uso (apps no verificadas)')
    else:
        print('⚠️  ADVERTENCIA: No tiene refresh_token')
        print('   El token expirará en 1 hora')
        print('   Regenera con: python generate_gdrive_token.py')
    
    print()
else:
    print('❌ No se encontró el token')
