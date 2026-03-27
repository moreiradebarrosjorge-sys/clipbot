STREAMERS = [
    {"name": "kai_cenat"},
    {"name": "ishowspeed"},
    {"name": "anyme023"},
]

# Détection de spike
SPIKE_THRESHOLD = 100
SPIKE_WINDOW_SEC = 4

# Mots-clés de réaction — le programme détecte si un message CONTIENT
# l'un de ces termes (pas besoin de correspondance exacte).
# Ex : "mdrrrrrrr" sera capté par "mdr", "ptdrrrrr" par "ptdr".
SPIKE_KEYWORDS = [
    # --- Français ---
    "mdr",       # couvre mdr, mdrrr, mdrrrrrr, mdrrrrrrrrr...
    "ptdr",      # couvre ptdr, ptdrrr, ptdrrrrr...
    "lol",       # couvre lol, loool, lolll...
    "mort",      # "je suis mort", "trop mort"
    "ded",       # version française de "dead"
    "xd",
    "haha",      # couvre haha, hahaha, hahahaha...
    "hihi",
    "héhé",
    "hehe",
    "xptdr",
    "omg",
    "incroyable",
    "impossible",
    "nooon",
    "noooon",
    "wsh",
    "wallah",

    # --- Anglais ---
    "lmao",      # couvre lmao, lmaooo, lmaooooo...
    "lmfao",
    "rofl",
    "kekw",      # émote Twitch emblématique du rire
    "lulw",      # émote Twitch rire
    "hahaa",
    "dead",      # "im dead", "bro is dead"
    "💀",        # crâne — utilisé massivement pour "je suis mort de rire"
    "😂",        # visage qui pleure de rire
    "🤣",        # roulé par terre de rire
    "😭",        # utilisé ironiquement pour exprimer le fou rire
    "bruh",
    "bro",
    "no way",
    "noway",
    "what",
    "wtf",
    "holy",
    "clip",      # les viewers qui écrivent "CLIP" eux-mêmes
    "clip it",
    "clipped",
    "pog",       # émote Twitch de surprise/excitation
    "pogchamp",
    "monkas",
    "gg",
]

# Clip
CLIP_DURATION_SEC  = 180   # durée du clip (3 minutes)
COOLDOWN_SEC       = 120   # délai minimum entre deux clips du même streameur

# Google Drive
GDRIVE_FOLDER_NAME = "ClipBot"

# Upload automatique
# Passer à True une fois l'approbation API TikTok obtenue
AUTO_UPLOAD_TIKTOK  = False
AUTO_UPLOAD_YOUTUBE = False

# Twitch API — https://dev.twitch.tv/console
TWITCH_CLIENT_ID     = "qb2le4xflj8of7ir1cu4h8er119001"
TWITCH_CLIENT_SECRET = "s68oa2o9ey06xi6iswji72r719w5jm"
TWITCH_ACCESS_TOKEN  = "l1r441svpko1x708h9vo087s95hrj2"

# TikTok API — https://developers.tiktok.com/doc/content-posting-api-get-started
# Renseigner une fois l'accès approuvé par TikTok
TIKTOK_ACCESS_TOKEN = ""
