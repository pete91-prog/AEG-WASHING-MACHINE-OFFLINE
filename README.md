# AEG FSE73768P for Home Assistant

Home Assistant integration for the **AEG 7000 ComfortLift FSE73768P** dishwasher. It controls the **real machine** through the official [Electrolux Group Developer API](https://developer.electrolux.one/) (the same cloud My AEG Kitchen uses). AEG does not offer a local LAN API.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=pete91-prog&repository=AEG-WASHING-MACHINE-OFFLINE&category=integration)

> The FSE73768P is a fully integrated dishwasher (PNC 911 438 399). Remote start, pause, and programme changes go to Electrolux after you pair the appliance in **My AEG Kitchen**.

## What you get

- Start, pause, resume, and stop the real dishwasher
- Live state: running, remaining time, phase, door, salt / rinse aid
- All QuickSelect programmes as buttons, a select, and services
- Tesla-style card with spray-arm graphics while a cycle runs
- HACS install — one repository, card registered automatically

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

## Connect the dishwasher

1. Pair the FSE73768P in **My AEG Kitchen** (2.4 GHz Wi‑Fi, hold the two connectivity buttons until the display shows `AP`).
2. Use the **same email** for [developer.electrolux.one](https://developer.electrolux.one/).
3. Create an **API key**, then generate an **access token** and **refresh token**.
4. On the dishwasher, enable **remote start** before Home Assistant can start a cycle.

Then in Home Assistant:

1. HACS → Integrations → Custom repositories
2. URL: `https://github.com/pete91-prog/AEG-WASHING-MACHINE-OFFLINE`
3. Category: **Integration**
4. Download **AEG FSE73768P** (1.1.0 or newer)
5. Restart Home Assistant
6. Settings → Devices & services → Add **AEG FSE73768P**
7. Paste API key, access token, and refresh token

If several appliances are on the account, pick the FSE73768P.

HACS does **not** refresh custom repositories immediately. Force it:

1. **HACS** → **Integrations** → open **AEG FSE73768P**
2. Top right **⋮** → **Update information** (or *Oppdater informasjon*)
3. **⋮** → **Redownload** / **Download again** (*Last ned på nytt*) — pick **1.1.0** if it appears, otherwise **main**
4. **Restart Home Assistant**
5. Add the integration again and paste Electrolux tokens

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
- ExtraPower, GlassCare, ExtraSilent
- Delay start (0–24 h)

### Services

| Service | What it does |
| --- | --- |
| `aeg_fse73768p.start_program` | Start any programme, with optional extras and delay |
| `aeg_fse73768p.pause` / `resume` / `cancel` | Cycle control on the real machine |

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
- **Door open** — door dropped (reported by the machine)
- **AirDry / finished** — steam, door ajar, green TimeBeam

`prefers-reduced-motion` turns the animations off.

## Notes

AEG does not expose a local LAN API. Every command goes through the official Electrolux Group API after the dishwasher is paired in **My AEG Kitchen**. Enable **remote start** on the door or Electrolux will reject the command.

The physical door cannot be opened from Home Assistant. ExtraPower / GlassCare / ExtraSilent are sent with the programme.

## Development

```bash
pytest -q
python3 scripts/generate_brand.py
```

## License

MIT
