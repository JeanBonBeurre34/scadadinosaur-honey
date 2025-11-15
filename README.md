# SCADADinosaur-Honey — Siemens S7-1200 Modbus Honeypot

SCADADinosaur-Honey is a **high‑interaction industrial honeypot** that emulates:
- A Siemens **S7‑1200 PLC**
- A full **Modbus‑TCP stack**
- Realistic **DB1 / DB10 / DB100 internal logic**
- Siemens‑style **UnitID behavior**
- Fully logged Modbus packets (requests + responses)

This project is designed for **research, attacker telemetry, training, and deception operations**.

---

## 🚀 Features

### ✔ Full Siemens Modbus Emulation
- UnitID = **1** behaves like a real Siemens PLC.
- UnitID = **255** allowed for **Device Identification (MEI 0x2B)**.
- All other UnitIDs are ignored (like real S7 PLCs).

### ✔ Full Modbus Packet Logging
Every request and response is logged with:
- TXID
- Protocol ID
- Length
- UnitID
- Function Code
- Raw ADU (HEX)

### ✔ Realistic Internal PLC Data Blocks
Values automatically map to Modbus Holding Registers:
| DB | Value            | Register |
|----|------------------|----------|
| DB1 | Temperature      | HR 0     |
| DB1 | Pressure         | HR 1     |
| DB10 | Tank Level      | HR 2     |
| DB10 | Valve State     | HR 3     |
| DB1 | Motor1 Running   | HR 4     |
| DB1 | Motor2 Running   | HR 5     |
| DB100 | CPU Load       | HR 100   |
| DB100 | Scan Time      | HR 101   |

Updates every **1 second**, simulating a real OB1 scan loop.

---

## 🧱 Architecture

```
┌────────────┐        ┌────────────────┐        ┌───────────────────┐
│ Attacker    │ <───► │ Wrapper (502)  │ <───►  │ Pymodbus Server   │
│ Scanner     │        │ Logs + Filters │        │ Real PLC Emulator │
└────────────┘        └────────────────┘        └───────────────────┘
```

Port overview:
- **502** → Externally exposed honeypot (wrapper)
- **1502** → Internal Pymodbus server
- **102** → S7Comm server (simulated)

---

## 📡 What Scanners See

### Nmap modbus-discover
Works and extracts:
- VendorName: SIEMENS AG  
- ProductCode: 6ES7  
- ModelName: S7-1200  
- Revision: 4.2  

### Metasploit modbus_banner_grabbing
Full device identification data returned.

### Shodan / Censys Fingerprints
Honeypot returns realistic Siemens‑style Modbus responses.


---

## 🐳 Running with Docker

```bash
docker build -t scadadinosaur .
docker run -p 502:502 -p 102:102 scadadinosaur
```

Logs:

```bash
docker logs -f <container>
```

---

## 🛡 Security Notes

This honeypot:
- **Should never be deployed inside production networks**
- Logs all activity clearly
- Does NOT execute arbitrary writes (safe)

---

## 📄 License
This project is released for **research and defensive purposes only**.

---

## 👤 Author
Created by (JeanBonBeurre34).

