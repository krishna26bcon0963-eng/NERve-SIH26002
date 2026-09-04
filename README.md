# NERve Final Presentation Build v4.1

NERve is a government-only, offline-first prototype for planning emergency supply delivery to disconnected Northeast Indian communities.

## Three connected government views

- **State Control Room:** state-wide priorities, inventory, fleet, simulations and every major escalation.
- **District Logistics Desk:** district planning, warehouse allocation, report verification and mission decisions.
- **Field Officer Tablet:** authorised incident reporting, assigned alerts and offline/low-bandwidth synchronisation.

The views can run on three devices connected to the same Wi-Fi or phone hotspot. Priority events use a live WebSocket channel, while offline field actions remain queued until connectivity returns.

## What works

- Role-specific navigation and alerts for state, district and field levels
- Live device registry, acknowledgement trail and P1/P2 priority events
- Explainable village priority with a factor-by-factor score breakdown
- Demo warehouses with supply inventory and a road/boat/air fleet
- Auditable warehouse reservation, dispatch deduction, cancellation release and receipt ledger
- Multimodal route options with labelled truck, boat, 4×4 and helicopter transfer points
- Departure, arrival, transfer, delivery and safe-operating deadline timeline
- One-click animated Majuli judge-demo mission
- Original-versus-revised disruption map with approval and device broadcast
- Optional satellite layer only inside Relief Planner
- Authorised field-report form with local offline queue
- File hash, GPS, time, duplicate and image metadata screening
- Mandatory official verification; AI never declares an incident true
- Late blockage simulation and replanning actions
- Origin/destination/time route-weather prediction using 93,504 historical rows
- Live English geocoding and OSRM road geometry for the prediction route
- Offline mission pack and priority-based 2G/3G sync
- Dynamic backend address, so phones/tablets use the laptop host instead of `127.0.0.1`

## Data honesty

Villages, warehouses, fleet, incidents and stock quantities are `SIMULATED_OPERATIONAL` demo records. The route-weather baseline uses 93,504 NASA POWER historical feature rows from the supplied dataset, but it estimates **weather hazard—not incident probability** because verified disruption labels are not present. Live route lookup needs internet. The prioritisation, allocation, capacity, multimodal planning, event delivery, report screening, offline queue and simulation workflows execute real application logic. Production deployment still requires government authentication, a database, authorised feeds, approved map/satellite licensing, a trained and validated evidence model, and field trials.

## Start with one command on Windows PowerShell

Extract the ZIP, open its `nerve_relief_ops` folder in VS Code, then run:

```powershell
powershell -ExecutionPolicy Bypass -File .\START_NERVE.ps1
```

The first run creates the Python 3.13 virtual environment and uses `npm.cmd` to install the frontend. Later runs detect installed packages and skip downloading them. Keep both opened server windows running.

## Open on three devices

On the laptop, run `ipconfig` and find the Wi-Fi adapter's **IPv4 Address**, for example `192.168.1.8`. All three devices must be on the same Wi-Fi or hotspot. Replace `YOUR-IP` below:

- State: `http://YOUR-IP:5173/?role=STATE_CONTROL`
- District: `http://YOUR-IP:5173/?role=DISTRICT_OPS`
- Field: `http://YOUR-IP:5173/?role=FIELD_OFFICER`

If Windows Firewall asks, allow access on **Private networks**. For one-laptop judging, open the same three links in separate browser tabs and replace `YOUR-IP` with `localhost`.

## Judge demo flow

1. Open the State, District and Field URLs in three devices or tabs.
2. District opens **Priority Villages**, expands the first village and explains every score factor.
3. District opens **Relief Planner** and presses **Start Judge Demo Mission** to show moving vehicles, transfer points and the full clock timeline.
4. Press **Approve & reserve stock**, inspect reserved quantities in **Warehouses**, then press **Dispatch & deduct stock**.
5. From Field, submit an official report (disconnect Wi-Fi first to demonstrate the offline queue if desired), reconnect and sync it.
6. District receives the verification alert, verifies the evidence and broadcasts the incident.
7. In **Simulate & Replan**, block ROAD, compare original/revised routes and approve the revised plan.
8. Enter Guwahati → Jorhat with a departure time to demonstrate the 93,504-row historical route-weather model.

## Manual fallback

Backend:

```powershell
cd backend; py -3.13 -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements.txt; .\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend:

```powershell
cd frontend; npm.cmd install; npm.cmd run dev -- --host 0.0.0.0
```
