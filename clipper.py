import asyncio
import aiohttp
import aiofiles
import os
import time
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from config import (
    TWITCH_CLIENT_ID, TWITCH_ACCESS_TOKEN,
    GDRIVE_FOLDER_NAME, COOLDOWN_SEC,
    AUTO_UPLOAD_TIKTOK, AUTO_UPLOAD_YOUTUBE
)

TEMP_DIR = "/tmp/clipbot"
os.makedirs(TEMP_DIR, exist_ok=True)


class Clipper:
    """
    Crée un clip Twitch, télécharge le fichier,
    l'uploade sur Google Drive, puis sur YouTube si activé.
    """

    def __init__(self):
        self.gdrive_service   = None
        self.gdrive_folder_id = None
        self._cooldowns: dict[str, float] = {}

    def init_gdrive(self, credentials_path: str):
        creds = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/drive.file"]
        )
        self.gdrive_service   = build("drive", "v3", credentials=creds)
        self.gdrive_folder_id = self._get_or_create_folder(GDRIVE_FOLDER_NAME)
        print(f"[Drive] Connecté — dossier '{GDRIVE_FOLDER_NAME}' prêt.")

    def _get_or_create_folder(self, name: str) -> str:
        query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = self.gdrive_service.files().list(q=query, fields="files(id)").execute()
        files = results.get("files", [])
        if files:
            return files[0]["id"]
        meta = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
        folder = self.gdrive_service.files().create(body=meta, fields="id").execute()
        return folder["id"]

    def _get_or_create_subfolder(self, streamer_name: str) -> str:
        query = (
            f"name='{streamer_name}' and "
            f"mimeType='application/vnd.google-apps.folder' and "
            f"'{self.gdrive_folder_id}' in parents and trashed=false"
        )
        results = self.gdrive_service.files().list(q=query, fields="files(id)").execute()
        files = results.get("files", [])
        if files:
            return files[0]["id"]
        meta = {
            "name": streamer_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [self.gdrive_folder_id]
        }
        folder = self.gdrive_service.files().create(body=meta, fields="id").execute()
        return folder["id"]

    async def handle_spike(self, streamer_name: str, rate: float):
        now  = time.time()
        last = self._cooldowns.get(streamer_name, 0)
        if now - last < COOLDOWN_SEC:
            remaining = int(COOLDOWN_SEC - (now - last))
            print(f"[{streamer_name}] Cooldown actif — {remaining}s restantes.")
            return

        self._cooldowns[streamer_name] = now
        print(f"[{streamer_name}] Spike détecté ({rate:.0f} msg/s) — création du clip...")

        clip_url, clip_id = await self._create_twitch_clip(streamer_name)
        if not clip_url:
            print(f"[{streamer_name}] Echec de création du clip.")
            return

        timestamp  = datetime.now().strftime("%Y-%m-%d_%Hh%M")
        filename   = f"{streamer_name}_{timestamp}_spike{rate:.0f}.mp4"
        local_path = os.path.join(TEMP_DIR, filename)

        print(f"[{streamer_name}] Téléchargement du clip...")
        await self._download_clip(clip_url, local_path)

        if self.gdrive_service:
            print(f"[{streamer_name}] Upload Google Drive...")
            drive_url = self._upload_to_drive(streamer_name, local_path, filename)
            print(f"[{streamer_name}] Clip disponible : {drive_url}")

        if AUTO_UPLOAD_TIKTOK:
            await self._upload_tiktok(local_path, streamer_name, rate)

        if AUTO_UPLOAD_YOUTUBE:
            await self._upload_youtube(local_path, streamer_name, rate)

        if os.path.exists(local_path):
            os.remove(local_path)
            print(f"[{streamer_name}] Fichier temporaire supprimé.")

    async def _create_twitch_clip(self, streamer_name: str):
        headers = {
            "Client-ID": TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {TWITCH_ACCESS_TOKEN}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.twitch.tv/helix/users?login={streamer_name}",
                headers=headers
            ) as resp:
                data  = await resp.json()
                users = data.get("data", [])
                if not users:
                    return None, None
                broadcaster_id = users[0]["id"]

            async with session.post(
                f"https://api.twitch.tv/helix/clips?broadcaster_id={broadcaster_id}",
                headers=headers
            ) as resp:
                data  = await resp.json()
                clips = data.get("data", [])
                if not clips:
                    return None, None
                clip_id = clips[0]["id"]

            await asyncio.sleep(15)

            async with session.get(
                f"https://api.twitch.tv/helix/clips?id={clip_id}",
                headers=headers
            ) as resp:
                data  = await resp.json()
                clips = data.get("data", [])
                if not clips:
                    return None, clip_id
                thumbnail    = clips[0].get("thumbnail_url", "")
                download_url = thumbnail.split("-preview")[0] + ".mp4"
                return download_url, clip_id

    async def _download_clip(self, url: str, dest_path: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                async with aiofiles.open(dest_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(1024 * 256):
                        await f.write(chunk)

    def _upload_to_drive(self, streamer_name: str, local_path: str, filename: str) -> str:
        subfolder_id = self._get_or_create_subfolder(streamer_name)
        file_meta    = {"name": filename, "parents": [subfolder_id]}
        media        = MediaFileUpload(local_path, mimetype="video/mp4", resumable=True)
        uploaded     = self.gdrive_service.files().create(
            body=file_meta, media_body=media, fields="id, webViewLink"
        ).execute()
        return uploaded.get("webViewLink", "")

    async def _upload_youtube(self, local_path: str, streamer_name: str, rate: float):
        try:
            from config import YOUTUBE_CREDENTIALS_PATH
        except ImportError:
            print("[YouTube] YOUTUBE_CREDENTIALS_PATH manquant dans config.py")
            return

        from google.oauth2.credentials import Credentials
        from googleapiclient.http import MediaFileUpload as MFU

        creds = Credentials.from_authorized_user_file(
            YOUTUBE_CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/youtube.upload"]
        )
        yt    = build("youtube", "v3", credentials=creds)
        title = f"{streamer_name} clip — {int(rate)} msgs/s"
        body  = {
            "snippet": {
                "title": title,
                "description": f"Clip automatique — ClipBot\n#shorts #{streamer_name}",
                "tags": [streamer_name, "clip", "shorts", "stream"],
                "categoryId": "20"
            },
            "status": {"privacyStatus": "public"}
        }
        media   = MFU(local_path, mimetype="video/mp4", resumable=True)
        request = yt.videos().insert(part="snippet,status", body=body, media_body=media)

        print(f"[YouTube] Upload en cours : {title}")
        response = None
        while response is None:
            _, response = request.next_chunk()
        print(f"[YouTube] Upload réussi — video id: {response.get('id')}")


    async def _upload_tiktok(self, local_path: str, streamer_name: str, rate: float):
        try:
            from config import TIKTOK_ACCESS_TOKEN
            if not TIKTOK_ACCESS_TOKEN:
                print("[TikTok] Token vide — configure TIKTOK_ACCESS_TOKEN dans config.py")
                return
        except ImportError:
            print("[TikTok] TIKTOK_ACCESS_TOKEN manquant dans config.py")
            return

        title = f"{streamer_name} moment fou — {int(rate)} msgs/s"
        print(f"[TikTok] Upload en cours : {title}")

        file_size = os.path.getsize(local_path)

        async with aiohttp.ClientSession() as session:
            # Étape 1 : initialiser l'upload
            async with session.post(
                "https://open.tiktokapis.com/v2/post/publish/video/init/",
                headers={
                    "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
                    "Content-Type": "application/json"
                },
                json={
                    "post_info": {
                        "title": title,
                        "privacy_level": "PUBLIC_TO_EVERYONE",
                        "disable_duet": False,
                        "disable_comment": False,
                        "disable_stitch": False,
                    },
                    "source_info": {"source": "FILE_UPLOAD"}
                }
            ) as resp:
                data       = await resp.json()
                upload_url = data.get("data", {}).get("upload_url")
                publish_id = data.get("data", {}).get("publish_id")
                if not upload_url:
                    print(f"[TikTok] Echec init upload : {data}")
                    return

            # Étape 2 : envoyer le fichier
            async with aiofiles.open(local_path, "rb") as f:
                video_data = await f.read()

            async with session.put(
                upload_url,
                headers={
                    "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
                    "Content-Length": str(file_size),
                    "Content-Type": "video/mp4"
                },
                data=video_data
            ) as resp:
                if resp.status in (200, 201):
                    print(f"[TikTok] Upload réussi — publish_id: {publish_id}")
                else:
                    print(f"[TikTok] Echec upload : HTTP {resp.status}")
