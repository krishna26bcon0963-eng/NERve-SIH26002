import os
"""NERve government relief-operations API."""
from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Literal
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from model_service import predict_route_weather_risk, public_model_info

app = FastAPI(title="NERve Relief Operations API", version="4.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in os.getenv("FRONTEND_ORIGINS", "*").split(",") if o.strip()], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
NOW=lambda: datetime.now(timezone.utc).isoformat()

VILLAGES=[
{"id":"V-101","name":"Dibang Riverside","district":"Lower Dibang Valley","state":"Arunachal Pradesh","lat":28.11,"lng":95.83,"population":860,"medical_cases":14,"hours_disconnected":19,"food_hours":10,"water_hours":7,"access":"DISCONNECTED","network":"OFFLINE","risk":91},
{"id":"V-102","name":"Majuli North Bank","district":"Majuli","state":"Assam","lat":27.02,"lng":94.22,"population":1420,"medical_cases":8,"hours_disconnected":11,"food_hours":18,"water_hours":14,"access":"DISCONNECTED","network":"2G INTERMITTENT","risk":84},
{"id":"V-103","name":"Mawlyngbna Cluster","district":"East Khasi Hills","state":"Meghalaya","lat":25.22,"lng":91.60,"population":620,"medical_cases":5,"hours_disconnected":8,"food_hours":26,"water_hours":20,"access":"LIMITED","network":"3G WEAK","risk":68},
{"id":"V-104","name":"Tamenglong East","district":"Tamenglong","state":"Manipur","lat":24.99,"lng":93.50,"population":1080,"medical_cases":11,"hours_disconnected":15,"food_hours":12,"water_hours":16,"access":"DISCONNECTED","network":"OFFLINE","risk":88},
{"id":"V-105","name":"Kolasib River Ward","district":"Kolasib","state":"Mizoram","lat":24.22,"lng":92.68,"population":740,"medical_cases":3,"hours_disconnected":5,"food_hours":30,"water_hours":22,"access":"LIMITED","network":"3G WEAK","risk":57}]
WAREHOUSES=[
{"id":"WH-GHY","name":"Guwahati Central Depot","lat":26.14,"lng":91.74,"network":"ONLINE","supplies":{"food_kg":8400,"water_l":12000,"medicine_kg":620,"shelter_kg":2800,"fuel_l":5400}},
{"id":"WH-JRH","name":"Jorhat Relief Depot","lat":26.75,"lng":94.20,"network":"3G STABLE","supplies":{"food_kg":5100,"water_l":7600,"medicine_kg":280,"shelter_kg":1700,"fuel_l":3200}},
{"id":"WH-SHG","name":"Shillong Regional Store","lat":25.58,"lng":91.89,"network":"ONLINE","supplies":{"food_kg":3900,"water_l":5200,"medicine_kg":410,"shelter_kg":1300,"fuel_l":2600}}]
FLEET=[
{"id":"TR-12","mode":"ROAD","type":"Medium truck","capacity_kg":2400,"status":"AVAILABLE","base":"WH-GHY","lat":26.14,"lng":91.74},
{"id":"TR-18","mode":"ROAD","type":"4x4 pickup","capacity_kg":850,"status":"AVAILABLE","base":"WH-SHG","lat":25.58,"lng":91.89},
{"id":"BT-04","mode":"BOAT","type":"Motor rescue boat","capacity_kg":600,"status":"AVAILABLE","base":"JET-MAJ","lat":26.96,"lng":94.18},
{"id":"BT-09","mode":"BOAT","type":"Shallow-water boat","capacity_kg":420,"status":"MISSION","base":"JET-DIB","lat":28.05,"lng":95.78},
{"id":"HL-02","mode":"AIR","type":"Utility helicopter","capacity_kg":300,"status":"AVAILABLE","base":"HEL-GHY","lat":26.11,"lng":91.59},
{"id":"DR-07","mode":"AIR","type":"Medical cargo drone","capacity_kg":12,"status":"AVAILABLE","base":"WH-JRH","lat":26.75,"lng":94.20}]
INCIDENTS=[
{"id":"IN-201","type":"BRIDGE BLOCKED","location":"Majuli approach bridge","lat":26.93,"lng":94.17,"severity":"CRITICAL","occurred_at":"2026-09-03T07:20:00Z","received_at":"2026-09-03T08:02:00Z","status":"VERIFIED","source":"PWD OFFICIAL","affects":["V-102"]},
{"id":"IN-202","type":"LANDSLIDE","location":"Tamenglong ridge road","lat":24.96,"lng":93.48,"severity":"CRITICAL","occurred_at":"2026-09-03T06:55:00Z","received_at":"2026-09-03T07:41:00Z","status":"VERIFIED","source":"DISTRICT FIELD OFFICER","affects":["V-104"]}]
REPORTS=[{"id":"RP-301","officer":"PWD Officer AS-14","location":"Dibang last-mile road","village_id":"V-101","report_type":"ROAD SUBMERGED","description":"Water above axle height; heavy vehicle passage unsafe.","evidence_name":"IMG_4821.jpg","evidence_hash":"demo-a82f","gps_match":True,"capture_age_minutes":18,"ai_score":86,"ai_checks":["Image type accepted","GPS near corridor","Recent capture time","No duplicate hash","Possible water obstruction"],"status":"AWAITING_OFFICIAL_VERIFICATION","created_at":NOW()}]
PLANS=[]
INVENTORY_LEDGER=[]
for warehouse in WAREHOUSES:
 warehouse["capacity_kg"]=35000
 warehouse["reserved"]={key:0 for key in warehouse["supplies"]}
DEVICES=[
 {"id":"STATE-CTRL-01","name":"State Control Room","role":"STATE_CONTROL","district":"ALL","status":"ONLINE","network":"LAN","last_seen":NOW(),"pending":0},
 {"id":"DISTRICT-OPS-01","name":"District Logistics Desk","role":"DISTRICT_OPS","district":"Majuli","status":"ONLINE","network":"LAN","last_seen":NOW(),"pending":1},
 {"id":"FIELD-TAB-07","name":"Field Officer Tablet","role":"FIELD_OFFICER","district":"Majuli","status":"OFFLINE","network":"OFFLINE PACK","last_seen":"2026-09-03T08:12:00Z","pending":4}]
EVENTS=[
 {"id":"EV-501","priority":1,"type":"VILLAGE_DISCONNECTED","title":"Majuli North Bank disconnected","message":"Bridge blockage requires multimodal replanning.","source_device":"DISTRICT-OPS-01","target_roles":["STATE_CONTROL","DISTRICT_OPS","FIELD_OFFICER"],"district":"Majuli","entity_id":"V-102","created_at":NOW(),"acknowledged_by":[]},
 {"id":"EV-502","priority":2,"type":"STOCK_WARNING","title":"Medicine stock requires attention","message":"Jorhat depot medicine reserve is below the requested critical load.","source_device":"STATE-CTRL-01","target_roles":["DISTRICT_OPS"],"district":"Majuli","entity_id":"WH-JRH","created_at":NOW(),"acknowledged_by":[]}]

class PlanRequest(BaseModel):
 village_id:str; food_kg:int=Field(ge=0,le=10000); water_l:int=Field(ge=0,le=20000); medicine_kg:int=Field(ge=0,le=2000); shelter_kg:int=Field(ge=0,le=10000); urgency:Literal["NORMAL","HIGH","CRITICAL"]="HIGH"; departure_at:datetime|None=None
class IncidentReport(BaseModel):
 officer:str=Field(min_length=3); village_id:str; report_type:str=Field(min_length=3); location:str=Field(min_length=3); description:str=Field(min_length=10); evidence_name:str=""; evidence_type:str=""; evidence_size:int=0; evidence_hash:str=""; lat:float; lng:float; captured_at:datetime
class ReviewRequest(BaseModel):
 action:Literal["VERIFY","REJECT","REQUEST_EVIDENCE"]; note:str=""
class IncidentRequest(BaseModel):
 report_id:str; severity:Literal["MEDIUM","HIGH","CRITICAL"]="HIGH"
class SyncItem(BaseModel):
 id:str; method:str; path:str; body:dict={}; priority:int=Field(ge=1,le=5); device_time:str
class SyncRequest(BaseModel):
 device_id:str; items:list[SyncItem]
class ScenarioRequest(BaseModel):
 village_id:str; blocked_mode:Literal["ROAD","BOAT","AIR"]; delay_minutes:int=Field(ge=0,le=720)
class DeviceRegistration(BaseModel):
 device_id:str; name:str; role:Literal["STATE_CONTROL","DISTRICT_OPS","FIELD_OFFICER"]; district:str="ALL"; network:str="LAN"
class EventCreate(BaseModel):
 priority:int=Field(ge=1,le=5); event_type:str; title:str; message:str; source_device:str; target_roles:list[Literal["STATE_CONTROL","DISTRICT_OPS","FIELD_OFFICER"]]; district:str="ALL"; entity_id:str=""
class EventAck(BaseModel):
 device_id:str
class RouteRiskRequest(BaseModel):
 origin:str=Field(min_length=2); destination:str=Field(min_length=2); departure:datetime
class PlanAction(BaseModel):
 officer:str=Field(min_length=3)
class StockReceipt(BaseModel):
 officer:str=Field(min_length=3); item:Literal["food_kg","water_l","medicine_kg","shelter_kg","fuel_l"]; quantity:int=Field(gt=0,le=50000)
class ReplanApproval(BaseModel):
 village_id:str; blocked_mode:Literal["ROAD","BOAT","AIR"]; officer:str=Field(min_length=3); response:str

class ConnectionManager:
 def __init__(self): self.connections={}
 async def connect(self,ws,device_id,role,district):
  await ws.accept();self.connections[device_id]={"socket":ws,"role":role,"district":district}
 async def broadcast(self,event):
  stale=[]
  for device_id,item in self.connections.items():
   role_ok=item["role"] in event["target_roles"]
   district_ok=event["district"] in ("ALL",item["district"]) or item["role"]=="STATE_CONTROL"
   if role_ok and district_ok:
    try:await item["socket"].send_json({"kind":"PRIORITY_EVENT","event":event})
    except Exception:stale.append(device_id)
  for device_id in stale:self.connections.pop(device_id,None)
 def disconnect(self,device_id):self.connections.pop(device_id,None)

manager=ConnectionManager()
async def emit(priority,event_type,title,message,source_device,target_roles,district="ALL",entity_id=""):
 event={"id":f"EV-{501+len(EVENTS)}","priority":priority,"type":event_type,"title":title,"message":message,"source_device":source_device,"target_roles":target_roles,"district":district,"entity_id":entity_id,"created_at":NOW(),"acknowledged_by":[]}
 EVENTS.insert(0,event);await manager.broadcast(event);return event

def priority_details(v):
 factors=[
  {"label":"Population affected","points":round(min(16,v["population"]/90),1),"value":f'{v["population"]:,} people'},
  {"label":"Medical urgency","points":round(min(24,v["medical_cases"]*1.8),1),"value":f'{v["medical_cases"]} cases'},
  {"label":"Isolation duration","points":round(min(24,v["hours_disconnected"]*1.6),1),"value":f'{v["hours_disconnected"]} hours'},
  {"label":"Essential stock pressure","points":round(max(0,20-min(v["food_hours"],v["water_hours"]))*1.2,1),"value":f'{min(v["food_hours"],v["water_hours"])}h remaining'},
  {"label":"Hazard exposure","points":round(v["risk"]*.24,1),"value":f'{v["risk"]}/100'},
  {"label":"Alternative access adjustment","points":-8 if v["access"]=="LIMITED" else 0,"value":"Limited alternate access" if v["access"]=="LIMITED" else "No reliable alternate"}]
 score=round(max(0,min(100,sum(f["points"] for f in factors))),1)
 reason=f'{v["medical_cases"]} medical cases, {v["hours_disconnected"]}h isolation and {min(v["food_hours"],v["water_hours"])}h essential stock remaining.'
 return score,factors,reason
def village_priority(v):return priority_details(v)[0]
def available(mode): return [x for x in FLEET if x["mode"]==mode and x["status"]=="AVAILABLE"]

def build_plan(p):
 v=next((x for x in VILLAGES if x["id"]==p.village_id),None)
 if not v: raise HTTPException(404,"Village not found")
 req={"food_kg":p.food_kg,"water_l":p.water_l,"medicine_kg":p.medicine_kg,"shelter_kg":p.shelter_kg}; total=sum(req.values())
 wh=max(WAREHOUSES,key=lambda w:sum(min(w["supplies"][k]-w["reserved"].get(k,0),value) for k,value in req.items()))
 available_stock={k:max(0,wh["supplies"][k]-wh["reserved"].get(k,0)) for k in req};alloc={k:min(value,available_stock[k]) for k,value in req.items()}; shortage={k:max(0,req[k]-alloc[k]) for k in req}
 road=available("ROAD")[0]; boat=available("BOAT")[0] if available("BOAT") else None; air=available("AIR")[0] if available("AIR") else None; opts=[]
 if v["access"]=="LIMITED":
  cap=road["capacity_kg"]; opts.append({"id":"OPT-A","label":"Road + last-mile 4×4","modes":["ROAD"],"capacity_kg":cap,"trips":max(1,ceil(total/cap)),"eta_minutes":210,"cost_index":32,"risk":v["risk"],"segments":[{"mode":"ROAD","from":wh["name"],"to":"Last accessible road point","vehicle":road["id"],"coordinates":[[wh["lat"],wh["lng"]],[v["lat"]-.05,v["lng"]-.04]]},{"mode":"ROAD","from":"Last accessible road point","to":v["name"],"vehicle":"TR-18","coordinates":[[v["lat"]-.05,v["lng"]-.04],[v["lat"],v["lng"]]]}]})
 if boat:
  cap=boat["capacity_kg"]; mid=[(wh["lat"]+v["lat"])/2,(wh["lng"]+v["lng"])/2];landing=[v["lat"]-.025,v["lng"]-.018]; opts.append({"id":"OPT-B","label":"Truck → river hub → boat → 4×4","modes":["ROAD","BOAT","ROAD"],"capacity_kg":cap,"trips":max(1,ceil(total/cap)),"eta_minutes":300,"cost_index":49,"risk":max(25,v["risk"]-18),"segments":[{"mode":"ROAD","from":wh["name"],"to":"Demo river transfer hub","vehicle":road["id"],"coordinates":[[wh["lat"],wh["lng"]],mid]},{"mode":"BOAT","from":"Demo river transfer hub","to":"Demo village landing point","vehicle":boat["id"],"coordinates":[mid,landing]},{"mode":"ROAD","from":"Demo village landing point","to":v["name"],"vehicle":"TR-18","coordinates":[landing,[v["lat"],v["lng"]]]}]})
 if air:
  cap=air["capacity_kg"]; heli=[wh["lat"]-.03,wh["lng"]-.12]; opts.append({"id":"OPT-C","label":"Truck → helipad → helicopter","modes":["ROAD","AIR"],"capacity_kg":cap,"trips":max(1,ceil(total/cap)),"eta_minutes":95,"cost_index":94,"risk":42,"segments":[{"mode":"ROAD","from":wh["name"],"to":"Government helipad","vehicle":road["id"],"coordinates":[[wh["lat"],wh["lng"]],heli]},{"mode":"AIR","from":"Government helipad","to":v["name"],"vehicle":air["id"],"coordinates":[heli,[v["lat"],v["lng"]]]}]})
 if not opts: raise HTTPException(409,"No transport resources available")
 rec=min(opts,key=lambda o:(0 if ((p.urgency=="CRITICAL" and "AIR" in o["modes"]) or (p.urgency!="CRITICAL" and "BOAT" in o["modes"])) else 60)+o["risk"]+o["eta_minutes"]/10)
 departure=(p.departure_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
 for o in opts:
  o["recommended"]=o["id"]==rec["id"];cursor=departure;leg_minutes=max(20,(o["eta_minutes"]-15*(len(o["segments"])-1))//len(o["segments"]))
  for index,segment in enumerate(o["segments"]):
   segment["departure_at"]=cursor.isoformat();cursor+=timedelta(minutes=leg_minutes);segment["arrival_at"]=cursor.isoformat();segment["duration_minutes"]=leg_minutes;segment["transfer_minutes"]=15 if index<len(o["segments"])-1 else 0
   if segment["transfer_minutes"]:cursor+=timedelta(minutes=segment["transfer_minutes"])
  o["expected_arrival_at"]=cursor.isoformat();o["safe_operating_deadline"]=(departure+timedelta(hours=9)).isoformat()
 plan={"id":f"PLAN-{401+len(PLANS)}","created_at":NOW(),"departure_at":departure.isoformat(),"data_source":"DEMO_OPERATIONAL_WITH_FUNCTIONAL_OPTIMISER","village":v,"priority_score":village_priority(v),"warehouse":wh,"warehouse_id":wh["id"],"requested":req,"allocated":alloc,"shortage":shortage,"total_payload_kg":total,"recommended_option_id":rec["id"],"options":opts,"status":"DRAFT","approval_status":"DRAFT—OFFICIAL APPROVAL REQUIRED","inventory_state":"NOT_RESERVED","explanation":f'{v["name"]} has been disconnected for {v["hours_disconnected"]} hours, has {v["medical_cases"]} medical cases and only {min(v["food_hours"],v["water_hours"])} hours of essential stock remaining.'}
 PLANS.insert(0,plan); return plan

@app.get("/")
def root():return {"message":"NERve relief operations backend running","version":"4.0.0"}
@app.get("/api/bootstrap")
def bootstrap():
 ranked=[]
 for v in VILLAGES:
  score,factors,reason=priority_details(v);ranked.append({**v,"priority_score":score,"priority_factors":factors,"priority_reason":reason})
 ranked.sort(key=lambda x:x["priority_score"],reverse=True)
 return {"data_source":"SIMULATED_OPERATIONAL","updated_at":NOW(),"villages":ranked,"warehouses":WAREHOUSES,"inventory_ledger":INVENTORY_LEDGER,"fleet":FLEET,"incidents":INCIDENTS,"reports":REPORTS,"plans":PLANS,"devices":DEVICES,"events":EVENTS,"network":{"online_nodes":6,"weak_nodes":3,"offline_nodes":2,"pending_sync":4,"last_sync":"38 seconds ago"},"notice":"Operational entities are simulated. Planning, prioritisation, inventory transactions, multi-device events and sync workflows are functional."}
@app.post("/api/plans",status_code=201)
async def create_plan(p:PlanRequest):
 plan=build_plan(p);await emit(2,"MISSION_PLAN_CREATED",f'New relief plan for {plan["village"]["name"]}',f'{plan["total_payload_kg"]} kg multimodal draft requires approval.',"DISTRICT-OPS-01",["STATE_CONTROL","DISTRICT_OPS"],plan["village"]["district"],plan["id"]);return plan
@app.get("/api/plans")
def get_plans():return PLANS

def plan_record(plan_id):
 plan=next((item for item in PLANS if item["id"]==plan_id),None)
 if not plan:raise HTTPException(404,"Plan not found")
 return plan

def inventory_transaction(warehouse,plan,action,officer):
 row={"id":f"TX-{1001+len(INVENTORY_LEDGER)}","created_at":NOW(),"warehouse_id":warehouse["id"],"plan_id":plan["id"],"action":action,"officer":officer,"quantities":plan["allocated"].copy()};INVENTORY_LEDGER.insert(0,row);return row

@app.post("/api/plans/{plan_id}/approve")
async def approve_plan(plan_id:str,p:PlanAction):
 plan=plan_record(plan_id)
 if plan["status"]!="DRAFT":raise HTTPException(409,"Only a draft plan can be approved")
 warehouse=next(w for w in WAREHOUSES if w["id"]==plan["warehouse_id"])
 for item,quantity in plan["allocated"].items():
  if warehouse["supplies"][item]-warehouse["reserved"].get(item,0)<quantity:raise HTTPException(409,f"Insufficient available {item}")
 for item,quantity in plan["allocated"].items():warehouse["reserved"][item]+=quantity
 plan.update(status="APPROVED",approval_status="APPROVED—STOCK RESERVED",inventory_state="RESERVED",approved_by=p.officer,approved_at=NOW());inventory_transaction(warehouse,plan,"RESERVE",p.officer);await emit(1,"MISSION_APPROVED",f'{plan_id} approved',"Warehouse stock reserved; dispatch is ready.","DISTRICT-OPS-01",["STATE_CONTROL","DISTRICT_OPS","FIELD_OFFICER"],plan["village"]["district"],plan_id);return plan

@app.post("/api/plans/{plan_id}/dispatch")
async def dispatch_plan(plan_id:str,p:PlanAction):
 plan=plan_record(plan_id)
 if plan["status"]!="APPROVED":raise HTTPException(409,"Approve and reserve stock before dispatch")
 warehouse=next(w for w in WAREHOUSES if w["id"]==plan["warehouse_id"])
 for item,quantity in plan["allocated"].items():warehouse["reserved"][item]-=quantity;warehouse["supplies"][item]-=quantity
 plan.update(status="DISPATCHED",approval_status="DISPATCHED—MISSION ACTIVE",inventory_state="DEDUCTED_AND_IN_TRANSIT",dispatched_by=p.officer,dispatched_at=NOW());inventory_transaction(warehouse,plan,"DISPATCH_DEDUCT",p.officer);await emit(1,"MISSION_DISPATCHED",f'{plan_id} dispatched',f'{plan["total_payload_kg"]} kg is now in transit.',"DISTRICT-OPS-01",["STATE_CONTROL","DISTRICT_OPS","FIELD_OFFICER"],plan["village"]["district"],plan_id);return plan

@app.post("/api/plans/{plan_id}/cancel")
async def cancel_plan(plan_id:str,p:PlanAction):
 plan=plan_record(plan_id)
 if plan["status"]=="DISPATCHED":raise HTTPException(409,"A dispatched mission needs a return/incident workflow, not stock release")
 if plan["status"]=="CANCELLED":raise HTTPException(409,"Plan is already cancelled")
 warehouse=next(w for w in WAREHOUSES if w["id"]==plan["warehouse_id"])
 if plan["status"]=="APPROVED":
  for item,quantity in plan["allocated"].items():warehouse["reserved"][item]-=quantity
  inventory_transaction(warehouse,plan,"RELEASE_RESERVATION",p.officer)
 plan.update(status="CANCELLED",approval_status="CANCELLED",inventory_state="RELEASED",cancelled_by=p.officer,cancelled_at=NOW());return plan

@app.post("/api/warehouses/{warehouse_id}/receive")
async def receive_stock(warehouse_id:str,p:StockReceipt):
 warehouse=next((w for w in WAREHOUSES if w["id"]==warehouse_id),None)
 if not warehouse:raise HTTPException(404,"Warehouse not found")
 warehouse["supplies"][p.item]+=p.quantity;row={"id":f"TX-{1001+len(INVENTORY_LEDGER)}","created_at":NOW(),"warehouse_id":warehouse_id,"plan_id":None,"action":"RECEIPT","officer":p.officer,"quantities":{p.item:p.quantity}};INVENTORY_LEDGER.insert(0,row);return {"warehouse":warehouse,"transaction":row}

@app.get("/api/demo-mission")
def demo_mission():
 departure=datetime.now(timezone.utc).replace(hour=2,minute=30,second=0,microsecond=0)
 plan=build_plan(PlanRequest(village_id="V-102",food_kg=800,water_l=1000,medicine_kg=120,shelter_kg=300,urgency="HIGH",departure_at=departure));plan["demo_mode"]=True;plan["demo_label"]="JUDGE DEMO—SIMULATED LOCATIONS AND TIMING";return plan
@app.post("/api/reports",status_code=201)
async def create_report(p:IncidentReport):
 v=next((x for x in VILLAGES if x["id"]==p.village_id),None)
 if not v:raise HTTPException(404,"Village not found")
 gps=abs(p.lat-v["lat"])+abs(p.lng-v["lng"])<.35; age=max(0,int((datetime.now(timezone.utc)-p.captured_at.astimezone(timezone.utc)).total_seconds()/60)); dup=any(r.get("evidence_hash") and r.get("evidence_hash")==p.evidence_hash for r in REPORTS); valid=p.evidence_type.startswith("image/") and 10000<=p.evidence_size<=12000000; score=25+(22 if gps else 0)+(18 if age<180 else 0)+(20 if valid else 0)-(35 if dup else 0)
 checks=["GPS near reported village" if gps else "GPS mismatch—manual review","Recent capture time" if age<180 else "Old capture time","Image type/size accepted" if valid else "Evidence requires review","Duplicate hash detected" if dup else "No duplicate hash found"]
 r={"id":f"RP-{301+len(REPORTS)}","officer":p.officer,"village_id":p.village_id,"report_type":p.report_type,"location":p.location,"description":p.description,"evidence_name":p.evidence_name,"evidence_hash":p.evidence_hash,"lat":p.lat,"lng":p.lng,"captured_at":p.captured_at.isoformat(),"gps_match":gps,"capture_age_minutes":age,"ai_score":max(0,min(95,score)),"ai_checks":checks,"status":"AWAITING_OFFICIAL_VERIFICATION","created_at":NOW(),"data_source":"AUTHORISED_OFFICIAL_REPORT","ai_disclaimer":"Prototype AI-assisted screening; not proof of authenticity."}; REPORTS.insert(0,r);await emit(1,"OFFICIAL_REPORT_PENDING",f'{p.report_type} requires verification',f'{p.officer} submitted evidence near {v["name"]}. AI triage {r["ai_score"]}/100; not yet verified.',"FIELD-TAB-07",["DISTRICT_OPS"],v["district"],r["id"]);return r
@app.patch("/api/reports/{report_id}")
async def review(report_id:str,p:ReviewRequest):
 r=next((x for x in REPORTS if x["id"]==report_id),None)
 if not r:raise HTTPException(404,"Report not found")
 r["status"]={"VERIFY":"VERIFIED_BY_CONTROL_ROOM","REJECT":"REJECTED","REQUEST_EVIDENCE":"MORE_EVIDENCE_REQUESTED"}[p.action];r["review_note"]=p.note;r["reviewed_at"]=NOW();v=next(x for x in VILLAGES if x["id"]==r["village_id"]);await emit(1 if p.action=="VERIFY" else 2,"REPORT_REVIEWED",f'Report {r["status"].replace("_"," ")}',f'{r["report_type"]} at {r["location"]}.',"DISTRICT-OPS-01",["STATE_CONTROL","FIELD_OFFICER"],v["district"],r["id"]);return r
@app.post("/api/incidents",status_code=201)
async def promote(p:IncidentRequest):
 r=next((x for x in REPORTS if x["id"]==p.report_id),None)
 if not r or r["status"]!="VERIFIED_BY_CONTROL_ROOM":raise HTTPException(409,"Only a verified report can become an incident")
 i={"id":f"IN-{201+len(INCIDENTS)}","type":r["report_type"],"location":r["location"],"lat":r["lat"],"lng":r["lng"],"severity":p.severity,"occurred_at":r["captured_at"],"received_at":NOW(),"status":"VERIFIED","source":r["officer"],"affects":[r["village_id"]],"late_arrival_minutes":r["capture_age_minutes"]};INCIDENTS.insert(0,i);r["incident_id"]=i["id"];v=next(x for x in VILLAGES if x["id"]==r["village_id"]);await emit(1,"VERIFIED_BLOCKAGE",f'Verified blockage affects {v["name"]}',"Active missions must hold and replan using last synchronised checkpoint.","DISTRICT-OPS-01",["STATE_CONTROL","DISTRICT_OPS","FIELD_OFFICER"],v["district"],i["id"]);return {"incident":i,"replanning_alert":f'Late-arriving blockage affects {r["village_id"]}. Missions must be re-evaluated.'}
@app.post("/api/simulate")
def simulate(p:ScenarioRequest):
 v=next((x for x in VILLAGES if x["id"]==p.village_id),None)
 if not v:raise HTTPException(404,"Village not found")
 alts={"ROAD":"Boat transfer or helicopter priority lift","BOAT":"Road staging plus helicopter bridge","AIR":"Truck/boat chain with split medical load"}
 warehouse=WAREHOUSES[0];blocked=[(warehouse["lat"]+v["lat"])/2,(warehouse["lng"]+v["lng"])/2];detour=[blocked[0]+.18,blocked[1]-.16]
 return {"data_source":"USER_SCENARIO_SIMULATION","village":v["name"],"village_id":v["id"],"blocked_mode":p.blocked_mode,"blocked_point":blocked,"original_route":[[warehouse["lat"],warehouse["lng"]],blocked,[v["lat"],v["lng"]]],"revised_route":[[warehouse["lat"],warehouse["lng"]],detour,[v["lat"],v["lng"]]],"original_eta_minutes":240,"revised_eta_minutes":240+p.delay_minutes+55,"reported_delay_minutes":p.delay_minutes,"new_risk":min(99,v["risk"]+round(p.delay_minutes/18)),"recommended_response":alts[p.blocked_mode],"late_update_warning":p.delay_minutes>=30,"actions":["Freeze affected dispatch","Estimate vehicle from last checkpoint","Send compressed priority alert","Generate alternate multimodal plan","Require official approval"],"disclaimer":"Decision-support simulation using demo operational data."}

@app.post("/api/replans/apply")
async def apply_replan(p:ReplanApproval):
 village=next((v for v in VILLAGES if v["id"]==p.village_id),None)
 if not village:raise HTTPException(404,"Village not found")
 event=await emit(1,"REVISED_PLAN_APPROVED",f'Revised mission approved for {village["name"]}',f'{p.blocked_mode} unavailable. {p.response}',"DISTRICT-OPS-01",["STATE_CONTROL","DISTRICT_OPS","FIELD_OFFICER"],village["district"],village["id"]);return {"status":"APPROVED_AND_BROADCAST","approved_by":p.officer,"event":event}

@app.get("/api/model-info")
def model_info():return public_model_info()

@app.post("/api/predict-route")
async def predict_route(p:RouteRiskRequest):
 try:return await predict_route_weather_risk(p.origin,p.destination,p.departure)
 except ValueError as error:raise HTTPException(400,str(error))
 except Exception as error:raise HTTPException(502,f"Live route lookup unavailable: {error}")
@app.post("/api/sync")
async def sync(p:SyncRequest):
 ordered=sorted(p.items,key=lambda x:x.priority);device=next((d for d in DEVICES if d["id"]==p.device_id),None);processed=[]
 for item in ordered:
  result={"id":item.id,"priority":item.priority,"status":"ACKNOWLEDGED"}
  if item.method.upper()=="POST" and item.path=="/api/reports":
   try:
    report=await create_report(IncidentReport(**item.body));result.update(status="APPLIED",entity_id=report["id"])
   except Exception as error:
    result.update(status="NEEDS_MANUAL_REVIEW",detail=str(error))
  processed.append(result)
 if device:device.update(status="ONLINE",network="2G/3G SYNC",last_seen=NOW(),pending=0)
 await emit(1,"FIELD_DEVICE_SYNC",f'{p.device_id} restored connectivity',f'{len(ordered)} queued updates received in priority order.',p.device_id,["DISTRICT_OPS"],device["district"] if device else "ALL")
 return {"device_id":p.device_id,"received_at":NOW(),"processed":processed,"server_changes":{"incidents":INCIDENTS[:3],"mission_plans":PLANS[:2],"events":EVENTS[:10]},"sync_policy":"Critical text/GPS first; media and map updates later."}

@app.post("/api/devices/register")
async def register_device(p:DeviceRegistration):
 device=next((d for d in DEVICES if d["id"]==p.device_id),None);record={"id":p.device_id,"name":p.name,"role":p.role,"district":p.district,"status":"ONLINE","network":p.network,"last_seen":NOW(),"pending":0}
 if device:device.update(record)
 else:DEVICES.append(record)
 await emit(3,"DEVICE_ONLINE",f'{p.name} connected',f'{p.role.replace("_"," ")} endpoint is now online.',p.device_id,["STATE_CONTROL","DISTRICT_OPS"],p.district,p.device_id);return record

@app.get("/api/events")
def get_events(role:str="STATE_CONTROL",district:str="ALL"):
 return [e for e in EVENTS if role in e["target_roles"] and (e["district"] in ("ALL",district) or role=="STATE_CONTROL")]

@app.post("/api/events",status_code=201)
async def create_event(p:EventCreate):return await emit(p.priority,p.event_type,p.title,p.message,p.source_device,p.target_roles,p.district,p.entity_id)

@app.patch("/api/events/{event_id}/ack")
async def acknowledge(event_id:str,p:EventAck):
 event=next((e for e in EVENTS if e["id"]==event_id),None)
 if not event:raise HTTPException(404,"Event not found")
 if p.device_id not in event["acknowledged_by"]:event["acknowledged_by"].append(p.device_id)
 await manager.broadcast(event);return event

@app.websocket("/ws/{device_id}")
async def websocket_endpoint(ws:WebSocket,device_id:str,role:str="STATE_CONTROL",district:str="ALL"):
 await manager.connect(ws,device_id,role,district)
 try:
  await ws.send_json({"kind":"CONNECTED","device_id":device_id,"role":role,"district":district,"server_time":NOW()})
  while True:
   message=await ws.receive_text()
   if message=="ping":await ws.send_text("pong")
 except WebSocketDisconnect:manager.disconnect(device_id)
