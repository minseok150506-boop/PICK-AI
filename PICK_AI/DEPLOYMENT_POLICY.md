# PICK deployment policy

PICK production deployment is permanently standardized on:

pick-ai.kr
-> Cloudflare
-> Cloudflare Named Tunnel
-> Windows MiniPC
-> Waitress / PICK Flask
-> local Ollama
-> Turso

Rules:
- Render is not used for PICK production, testing, fallback, or recovery.
- Do not add Render deployment files or Render environment dependencies back.
- Do not suggest Render as a PICK deployment or recovery option.
- The MiniPC is the web and AI server.
- Turso is the required persistent database when PICK_REQUIRE_PERSISTENT_DB=1.
