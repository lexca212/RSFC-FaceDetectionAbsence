import firebase_admin
from firebase_admin import credentials
from django.conf import settings
import os

cred_path = os.path.join(settings.BASE_DIR, 'credential_fcm.json')

cred = credentials.Certificate(cred_path)

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
