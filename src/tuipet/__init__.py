
import os

# Online feature is disabled by default. 
# To easily turn it on without editing code, run the game with: TUIPET_ONLINE=1 tuipet
SERVIDOR_ONLINE = os.environ.get("TUIPET_ONLINE", "0") == "1"
