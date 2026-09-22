# Pillefyr (Stokercloud) — Home Assistant integration

Home Assistant-integration til pillefyr på **NBE / Stokercloud-platformen** (fx **Blackstar 1016**), bygget ved at reversere cloud-API'en som appen "NBE v7" bruger (`stokercloud.dk/v2/dataout2/`).

**Sprog:** [Dansk](#dansk) · [English](#english)

---

## Dansk

### Funktioner

- **Sensorer:** kedeltemperatur, setpunkt, diff, ilt, snegle, vacuum, firmware + **alt andet** som attributter (avanceret, rengøring, ventilator, alarmer m.m.)
- **Tilstands-sensor:** `I drift` / `Tænder op` / `Stoppet af ur` / `Off` — opdateret hvert 5. min
- **Tjenester:**
  - `pillefyr.start` — lægger fyret under timeren ("tænd fyr": tænder når nattimeren siger start)
  - `pillefyr.start` med `ignorer_ur: true` — tænder NU, uanset uret; timeren gendannes automatisk ved næste stop
  - `pillefyr.stop` — hård sluk ("off" — tænder ikke af sig selv igen)
  - `pillefyr.timer` med `aktiv: true/false` — slå urstyringen fra/til (fx vinterdrift med konstant kørsel)
  - `pillefyr.set_value` — skriv vilkårlig parameter (fx `boiler.temp`)
  - `pillefyr.reset_alarm` — nulstiller alarmer
- **Auto-relogin** hvis token'en udløber

### Installation (HACS, custom repository)

1. HACS → ⋮ → **Tilfældigt lager (Custom repositories)** → `soerenadk/pillefyr-ha` → **Integration**
2. Genstart Home Assistant
3. Tilføj til `configuration.yaml`:

```yaml
pillefyr:
  username: dit_stokercloud_brugernavn
  password: dit_stokercloud_kodeord

sensor:
  - platform: pillefyr
```

(Har du allerede en `sensor:`-linje, skal du kun tilføje `- platform: pillefyr` under den.)

4. Genstart — entiteterne dukker op som `sensor.pillefyr_*`

### Eksempel: tænd uanset uret

```yaml
service: pillefyr.start
data:
  ignorer_ur: true
```

### Bemærkninger

- **Status:** integrationen er **kortvarigt testet** i reel drift (læs, skriv, start, stop, bypass — Blackstar 1016, controller v7.068). Finder du udfordringer, så skriv et issue her på GitHub — vi kigger på det med det samme.
- Cloud-API'en cacher data (~5 min forsinkelse) — nok til styring og status, ikke sekund-live

---

## English

### Features

- **Sensors:** boiler temp, setpoint, diff, oxygen, auger, vacuum, firmware + **everything else** as attributes (advanced, cleaning, fan, alarms…)
- **State sensor:** `I drift` (running) / `Tænder op` (igniting) / `Stoppet af ur` (stopped by clock) / `Off`
- **Services:**
  - `pillefyr.start` — hand control to the timer schedule (ignites when the clock says so)
  - `pillefyr.start` with `ignorer_ur: true` — ignite NOW, bypassing the clock; the clock setting is restored on the next stop
  - `pillefyr.stop` — hard off (won't ignite by itself again)
  - `pillefyr.timer` with `aktiv: true/false` — enable/disable clock control (e.g. constant winter operation)
  - `pillefyr.set_value` — write any parameter (e.g. `boiler.temp`)
  - `pillefyr.reset_alarm` — clear alarms
- **Auto-relogin** on token expiry

### Installation (HACS custom repository)

1. HACS → ⋮ → **Custom repositories** → `soerenadk/pillefyr-ha` → **Integration**
2. Restart Home Assistant
3. Add to `configuration.yaml`:

```yaml
pillefyr:
  username: your_stokercloud_username
  password: your_stokercloud_password

sensor:
  - platform: pillefyr
```

4. Restart — entities appear as `sensor.pillefyr_*`

### Notes

- **Status:** the integration is **briefly tested** in real operation (read, write, start, stop, bypass — Blackstar 1016, controller v7.068). If you hit issues, open a GitHub issue — we'll look at it right away.
- The cloud API caches data (~5 min lag) — fine for control and status, not second-live telemetry

---

*Bygget af Amber (Sørens assistent), sep 2026. Ubrugt af fabrikken — API'et er reverse-engineeret fra appen "NBE v7" (`com.nbe.v7pelletburner`).*
