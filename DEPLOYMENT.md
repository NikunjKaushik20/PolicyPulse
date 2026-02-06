# Deployment Guide (DigitalOcean)

This guide documents your **LIVE** deployment on DigitalOcean.
**Public URL:** `http://64.227.174.109:8000`
**Server IP:** `64.227.174.109`

> **Note:** To enable microphone access on this HTTP URL, see [Enabling Microphone](#enabling-microphone-on-http).

---

## 1. Accessing the Server (SSH)
To manage the server, open a terminal on your laptop and run:
```bash
ssh root@64.227.174.109
# Enter password when prompted
```

---

## 2. Server Architecture (Setup Details)
We used a **DigitalOcean Droplet** ($6/mo) with **Ubuntu 24.04**.

### Installed Components:
1.  **Python 3.12** + `venv`
2.  **ChromaDB** (Persistent Vector Database)
3.  **Twilio Webhook** (for WhatsApp) on `/sms`
4.  **Systemd Service** (Keeps it running 24/7)
5.  **Swap File** (2GB) to prevent crashes on 1GB RAM.

---

## 3. Maintenance Commands

### Check Server Status
See if the app is running:
```bash
systemctl status policypulse
```

### View Live Logs
See what the AI is doing (or debug errors):
```bash
journalctl -u policypulse -f
# Press Ctrl+C to exit
```

### Restart Server
If something feels stuck or after changing code:
```bash
systemctl restart policypulse
```

### Update Code (after pushing to GitHub)
```bash
cd ~/PolicyPulse
git pull origin main
systemctl restart policypulse
```

---

## 4. Configuration (Env Vars)
Your API keys are stored in `/root/PolicyPulse/.env`.
To edit them (e.g., to add a Gemini Key later):
```bash
cd ~/PolicyPulse
nano .env
# Edit file -> Ctrl+O (Save) -> Enter -> Ctrl+X (Exit)
systemctl restart policypulse
```

---

## 5. Troubleshooting History
### "Address already in use"
*   **Cause**: `nohup` process conflict.
*   **Fix**: `pkill -f python` then `systemctl start policypulse`.

### "OS file watch limit reached"
*   **Cause**: Auto-reload watching `transformers` files.
*   **Fix**: Disabled reload in `start.py` (`reload=False`).

### "Killed" (Out of Memory)
*   **Cause**: Loading AI models on 1GB RAM.
*   **Fix**: Added 2GB Swap file.

### "AttributeError: bcrypt"
*   **Cause**: `passlib` incompatibility with Python 3.12.
*   **Fix**: Switched to `argon2` hashing in `src/auth.py`.

### Enabling Microphone on HTTP
Browsers block microphone access on non-HTTPS sites by default. To fix this:
1.  Open `chrome://flags/#unsafely-treat-insecure-origin-as-secure` in Chrome/Edge.
2.  Select **Enabled** from the dropdown.
3.  Enter `http://64.227.174.109:8000` in the text box.
4.  Click **Relaunch**.

---

