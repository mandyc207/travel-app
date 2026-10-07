# Travel Collector App

A simple travel places organizer - collect places by city, view by category or district.

## Features
- 📍 Add places with city, name, category (Restaurant/Sightseeing/Activities/Shopping)
- 📁 View by category OR by district (for route planning)
- 🔗 Click to open in Google Maps
- 📱 Mobile-friendly design
- ☁️ Cloud accessible via Cloudflare Tunnel

## Setup Instructions (DigitalOcean + Cloudflare)

### 1. Upload files to your DigitalOcean server
```bash
# SSH to your server
ssh root@your-server-ip

# Create directory
mkdir -p /opt/travel-app
cd /opt/travel-app

# Copy all files from travel-app folder to this directory
# (use scp, rsync, or git clone)
```

### 2. Install dependencies
```bash
cd /opt/travel-app
pip3 install -r requirements.txt
```

### 3. Test locally
```bash
python3 app.py
# Visit http://your-server-ip:5000 to test
```

### 4. Create systemd service (auto-start)
```bash
sudo nano /etc/systemd/system/travel-app.service
```

Paste this:
```ini
[Unit]
Description=Travel Collector App
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/travel-app
ExecStart=/usr/bin/python3 /opt/travel-app/app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable travel-app
sudo systemctl start travel-app
```

### 5. Update Cloudflare Tunnel
If you already have a tunnel running for your expenses app, just add a new public hostname:

```bash
# Edit your tunnel config file (~/.cloudflared/config.yml)
```

Add:
```yaml
publicHostname: travel.otterocean.com
service: http://localhost:5000
```

Or use Cloudflare Dashboard:
1. Go to Cloudflare Zero Trust → Networks → Tunnels
2. Edit your tunnel
3. Add public hostname: `travel.otterocean.com` → `http://localhost:5000`

### 6. Visit
Go to https://travel.otterocean.com 🎉

## Usage

### From Telegram
When you find a place online, just message me:
> "Add Gordon Ramsay Burger to Los Angeles, restaurant, Hollywood, notes: amazing views"

I'll add it to your list automatically!

### From the Web
Just visit https://travel.otterocean.com and:
- Use the dropdown to filter by city
- Toggle between "By Category" and "By District" view
- Click "Add New Place" to add manually
- Click "Maps" to open in Google Maps

## Tech Stack
- Python Flask
- SQLite database
- HTML/CSS (mobile-first)
- Cloudflare Tunnel
