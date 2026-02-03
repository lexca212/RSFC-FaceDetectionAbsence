# notifications/utils.py
from firebase_admin import messaging
from cms.models import FCMToken

def send_fcm_to_user(user, title, body, data=None):
    tokens = list(
        FCMToken.objects
        .filter(nik=user)
        .exclude(token__isnull=True)
        .exclude(token="")
        .values_list('token', flat=True)
    )

    if not tokens:
        return False

    payload = {
        "title": title,
        "body": body,
        **{k: str(v) for k, v in (data or {}).items()}
    }

    message = messaging.MulticastMessage(
        data=payload,
        tokens=tokens,
    )

    response = messaging.send_each_for_multicast(message)

    # cleanup token mati
    for idx, resp in enumerate(response.responses):
        if not resp.success:
            FCMToken.objects.filter(token=tokens[idx]).delete()

    return response
