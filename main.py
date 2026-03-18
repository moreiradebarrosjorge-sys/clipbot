import asyncio
import os
import json
import tempfile
from chat_monitor import ChatMonitor
from clipper import Clipper
from config import STREAMERS


async def main():
    print("=" * 50)
    print("  ClipBot — démarrage")
    print("=" * 50)

    # Initialisation Google Drive depuis variable d'environnement
    clipper = Clipper()
    gdrive_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if gdrive_json:
        try:
            tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
            tmp.write(gdrive_json)
            tmp.close()
            clipper.init_gdrive(tmp.name)
        except Exception as e:
            print(f"[Attention] Erreur Google Drive : {e}")
            print("  Les clips seront sauvegardés temporairement dans /tmp/clipbot/")
    else:
        credentials_path = os.path.expanduser("~/clipbot_credentials.json")
        if os.path.exists(credentials_path):
            clipper.init_gdrive(credentials_path)
        else:
            print(f"[Attention] Fichier credentials Google Drive introuvable : {credentials_path}")
            print("  Les clips seront sauvegardés temporairement dans /tmp/clipbot/")

    # Callback appelé par chaque ChatMonitor lors d'un spike
    async def on_spike(streamer_name: str, rate: float):
        await clipper.handle_spike(streamer_name, rate)

    # Lancement d'un monitor par streameur en parallèle
    monitors = [ChatMonitor(s, on_spike) for s in STREAMERS]
    tasks    = [asyncio.create_task(m.start()) for m in monitors]

    print(f"[ClipBot] {len(monitors)} streameur(s) surveillé(s) : {[s['name'] for s in STREAMERS]}")
    print("[ClipBot] En attente de spikes... (Ctrl+C pour arrêter)\n")

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        print("\n[ClipBot] Arrêt demandé.")
    finally:
        for m in monitors:
            m.stop()
        for t in tasks:
            t.cancel()
        print("[ClipBot] Arrêté proprement.")


if __name__ == "__main__":
    asyncio.run(main())
