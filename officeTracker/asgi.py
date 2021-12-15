import os
from channels.http import AsgiHandler
from channels.routing import ProtocolTypeRouter,URLRouter
from channels.auth import AuthMiddlewareStack
import server.routing
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'officeTracker.settings')
django.setup()

application = ProtocolTypeRouter({
  "http": AsgiHandler(),
  # Just HTTP for now. (We can add other protocols later.)
    "websocket": AuthMiddlewareStack(
        URLRouter(
            server.routing.websocket_urlpatterns
        )
    )
})