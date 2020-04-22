"""Views for the squarelet auth app"""

# Django
from django.http.response import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt

# Standard Library
import hashlib
import hmac
import logging
import time

# SquareletAuth
from squarelet_auth import settings
from squarelet_auth.tasks import pull_data

logger = logging.getLogger(__name__)


@csrf_exempt
def webhook(request):
    """Receive a cache invalidation webhook from squarelet"""

    type_ = request.POST.get("type", "")
    uuids = request.POST.getlist("uuids", "")
    timestamp = request.POST.get("timestamp", "")
    signature = request.POST.get("signature", "")

    # verify signature
    hmac_digest = hmac.new(
        key=settings.SOCIAL_AUTH_SQUARELET_SECRET.encode("utf8"),
        msg="{}{}{}".format(timestamp, type_, "".join(uuids)).encode("utf8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    match = hmac.compare_digest(signature, hmac_digest)
    try:
        timestamp_current = int(timestamp) + 300 > time.time()
    except ValueError:
        return HttpResponseForbidden()
    if not match or not timestamp_current:
        return HttpResponseForbidden()

    # pull the new data asynchrnously
    for uuid in uuids:
        pull_data.delay(type_, uuid)
    return HttpResponse("OK")