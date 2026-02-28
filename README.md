# Joan Home Display Network

> A self-hosted e-ink display network built from salvaged **Visionect Joan 6** devices, running on a home server with Docker. Displays show scriptures, family menus, inspirational quotes, system stats, games, and more — all served from a single Ubuntu machine.

---

## 📸 What It Looks Like

Each Joan 6 is a **1024×758 grayscale e-ink touchscreen** that connects to your local network over WiFi. The display is always on, uses very little power, and looks great on a wall, shelf, or fridge.

**Active displays in this setup:**
| Display | Content |
|---------|---------|
| Scripture of the Day | Rotating Bible verses, Good Morning / Good Night modes |
| Family Menu | Weekly meal plan with touch navigation |
| Quotes & Wisdom | Inspirational quotes every 30 min, time-aware modes |
| System Monitor | Pi-hole stats, Docker container status, server health |
| Hangman | Fully playable hangman game with touch keyboard |

---

## 🧰 Hardware

- **Displays:** [Visionect Joan 6](https://visionect.com/joan-6/) — 6" e-ink, WiFi, touch, 1024×758
- **Server:** Any x86 machine running Ubuntu Server (this project uses a repurposed ASUS Chromebox 3)
- **Minimum specs:** 2GB RAM, 20GB disk, 2 CPU cores

> 💡 **Tip:** Visionect Joan devices frequently appear on eBay, GovDeals, and e-waste auctions for $10–30 each. Businesses that used them for meeting room signs are common sellers.

---

## 🏗️ Architecture

```
Joan Device (WiFi) ──→ Visionect Server (Docker) ──→ HTML Pages (nginx)
                              │
                              └──→ Home Assistant (optional)
```

- **Visionect Server Suite (VSS)** manages all devices, fetches HTML pages, renders them server-side, and pushes bitmap images to the e-ink screens
- **nginx** serves static HTML files from a local directory
- **Home Assistant** (optional) enables smart home integration
- **Pi-hole** (optional) provides DNS stats for the System Monitor display

---

## ✨ Features

- ✅ **No cloud dependency** — everything runs locally
- ✅ **Touch support** — tap zones for interactive displays
- ✅ **Time-aware displays** — Good Morning / Good Night modes
- ✅ **Auto-refresh** — displays update on a schedule
- ✅ **Easy content editing** — HTML files, no special tools needed
- ✅ **Expandable** — add as many displays as you want
- ✅ **Home Assistant integration** — sensor data, automations (optional)

---

## 🚀 Quick Start

1. **Clone this repo**
   ```bash
   git clone https://github.com/YOUR_USERNAME/joan-home-display-network
   cd joan-home-display-network
   ```

2. **Copy and fill in your config**
   ```bash
   cp .env.example .env
   # Edit .env with your server IP, VSS credentials, etc.
   ```

3. **Start the Docker stack**
   ```bash
   docker compose up -d
   ```

4. **Copy display pages to the static file directory**
   ```bash
   cp displays/*.html /path/to/www/
   ```

5. **Register your Joan device** — see [SETUP.md](SETUP.md) for full instructions

---

## 📂 Repository Structure

```
joan-home-display-network/
├── README.md                    # This file
├── SETUP.md                     # Full installation guide
├── TROUBLESHOOTING.md           # Common issues and fixes
├── FAQ.md                       # Frequently asked questions
├── LICENSE                      # MIT License
├── .env.example                 # Template for your secrets/config
├── docker-compose.example.yml   # Docker stack definition
├── displays/
│   ├── scripture.html           # Scripture of the Day
│   ├── menu.html                # Family weekly menu
│   ├── quotes.html              # Inspirational quotes
│   ├── sysmon.html              # System monitor dashboard
│   └── hangman.html             # Hangman game
└── scripts/
    └── sysmon-update.py         # System monitor data collector
```

---

## 📖 Documentation

- [Full Setup Guide →](SETUP.md)
- [Troubleshooting →](TROUBLESHOOTING.md)
- [FAQ →](FAQ.md)

---

## 🤝 Contributing

Pull requests welcome! If you build a new display page, fix a bug, or improve the docs, please share it.

**Ideas for new displays:**
- Room temperature sensors (via Home Assistant)
- Family calendar
- Google Sheets task board
- Weather forecast
- Daily dad jokes
- Chore chart

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

## 🙏 Acknowledgments

- [Visionect](https://visionect.com/) for the Joan hardware and VSS software
- [bible-api.com](https://bible-api.com/) for the free Bible verse API
- The Home Assistant community
