# AEG FSE73768P for Home Assistant

Offline Home Assistant integration for the **AEG 7000 ComfortLift FSE73768P** dishwasher.

No My AEG Kitchen account. No Electrolux cloud. Every QuickSelect programme is a one-tap entity, and a Tesla-style Lovelace card shows the machine as a living graphic while it runs.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=pete91-prog&repository=AEG-WASHING-MACHINE-OFFLINE&category=integration)

> The FSE73768P is a fully integrated dishwasher (PNC 911 438 399). AEG does not publish a local LAN API for this model, so this integration keeps the full programme set on your Home Assistant box instead of phoning home.

## What you get

- **Fully offline** — calculated locally, `iot_class: calculated`
- **All factory programmes** as buttons, a select, and services
- **EXTRAS** — ExtraPower, GlassCare, ExtraSilent (ECO)
- **Tesla-style card** — cutaway cabinet, spinning spray arms, TimeBeam on the floor, ComfortLift basket, AirDry steam
- **HACS install** — one repository, card is registered automatically

![Running FSE73768P card](images/card-preview.svg)

Add the card from the dashboard picker (**AEG FSE73768P**) or:

```yaml
type: custom:aeg-fse73768p-card
```

## Programmes

Values follow the 7000-series QuickSelect manuals. ECO is the Ecodesign (EU) 2019/2022 rated cycle.

| Programme | Duration | Water | Energy | Wash | EXTRAS |
| --- | --- | --- | --- | --- | --- |
| Quick | 30 min | 10.6 L | 0.58 kWh | 50 °C | ExtraPower, GlassCare |
| 1h | 60 min | 11.7 L | 0.99 kWh | 60 °C | ExtraPower, GlassCare |
| 1h 30min | 90 min | 12.9 L | 1.08 kWh | 60 °C | ExtraPower, GlassCare |
| 2h 40min | 160 min | 12.3 L | 1.19 kWh | 60 °C | ExtraPower, GlassCare |
| **ECO** | **240 min** | **11.0 L** | **0.86 kWh** | 50 °C | ExtraPower, GlassCare, ExtraSilent |
| AUTO Sense | 145 min | 11.9 L | 0.99 kWh | 50–60 °C | — |
| Machine Care | 60 min | 10.8 L | 0.67 kWh | 70 °C | — |

The machine advances through prewash → main wash → rinses → drying → AirDry, pauses if you open the door, and opens the door itself for AirDry when that setting is on. TimeBeam is red while running, green when finished, and flashes on a fault.

## GitHub settings for HACS

HACS also reads **repository** metadata (not just files). In the GitHub repo, set:

- **Description:** `Offline Home Assistant integration for the AEG FSE73768P dishwasher`
- **Topics:** `home-assistant`, `hacs`, `integration`, `aeg`, `dishwasher`
- **License:** MIT (this repo already includes `LICENSE`; GitHub picks it up on the default branch)

## Install with HACS

1. HACS → Integrations → Custom repositories
2. URL: `https://github.com/pete91-prog/AEG-WASHING-MACHINE-OFFLINE`
3. Category: **Integration**
4. Download **AEG FSE73768P**
5. Restart Home Assistant
6. Settings → Devices & services → Add integration → **AEG FSE73768P**

If you see **Invalid handler specified** / *Konfigurasjonsflyt kunne ikke lastes inn*, update to **1.0.1+** in HACS and restart Home Assistant. That error was a broken import in the Lovelace card loader.

The Lovelace card is registered as a frontend module on setup. In YAML Lovelace mode add:

```yaml
resources:
  - url: /aeg_fse73768p/aeg-fse73768p-card.js
    type: module
```

## Entities

The device exposes:

- State, programme, cycle phase, remaining time, progress, temperatures, Ecometer, TimeBeam
- Energy and water used this cycle
- Running / door / salt / rinse aid / Machine Care binary sensors
- Programme select plus **Start Quick**, **Start ECO**, … buttons
- ExtraPower, GlassCare, ExtraSilent, AirDry, ComfortLift, power, door
- Delay start (0–24 h), water softener, rinse aid dosage
- Interior light (when the door is open)

### Services

| Service | What it does |
| --- | --- |
| `aeg_fse73768p.start_program` | Start any programme, with optional extras and delay |
| `aeg_fse73768p.pause` / `resume` / `cancel` | Cycle control |
| `aeg_fse73768p.set_door` | Open or close the door (opening pauses a wash) |

```yaml
action: aeg_fse73768p.start_program
data:
  program: eco
  extra_silent: true
  delay_hours: 3
```

## How the graphic works

The card behaves like a vehicle card in Home Assistant:

- **Idle** — closed 7000-series cabinet, MY TIME dots, dark TimeBeam
- **Running** — cutaway stainless tub, rotating spray arms, water droplets, red progress ring, red TimeBeam on the floor
- **Door open** — door dropped, interior light, ComfortLift raises the lower basket
- **AirDry / finished** — steam, door ajar, green TimeBeam

`prefers-reduced-motion` turns the animations off.

## Notes

This is a local model of the FSE73768P, not a reverse-engineered Wi-Fi bind. Use it for dashboards, cheap-rate automations, and a complete programme panel without the AEG cloud. Pair a smart plug if you also want measured watts from the real appliance.

Settings and cycle counts survive Home Assistant restarts. A wash that is mid-cycle at restart returns to idle (the real machine is not being driven over the network).

## Development

```bash
pytest -q
python3 scripts/generate_brand.py
```

## License

MIT
