#!/usr/bin/env python3
"""
RAM AI CCTV ADVANCED — single-file prototype

Core:
  - webcam / video / RTSP, multi-camera
  - motion + person detection
  - optional YOLO object detection
  - face detection + optional LBPH known/unknown recognition
  - event clips with pre/post buffer
  - SQLite event memory
  - camera health diagnostics
  - SHA-256 evidence capsule
  - conservative possible-object-removal review
  - local English/Telugu-style query commands
  - optional voice input/output
  - Telegram/webhook alerts
  - REST API + MJPEG stream for RAM AI app
  - controlled feedback tuning (no self-rewriting code)

This is an advanced prototype, not a certified security product. AI can be wrong.
Unknown identity does NOT imply wrongdoing. Object disappearance is NOT proof of theft.
Production deployment needs TLS, strong auth, encrypted storage, legal/privacy review,
calibrated models, redundancy, monitoring and professional security testing.

Core install:
  python -m pip install --upgrade pip
  python -m pip install numpy opencv-contrib-python

Optional advanced features:
  python -m pip install ultralytics requests SpeechRecognition pyttsx3
  python -m pip install pyaudio

Run webcam:
  python RAM_AI_CCTV_ADVANCED.py --source 0

Run video:
  python RAM_AI_CCTV_ADVANCED.py --source "test.mp4"

RTSP:
  python RAM_AI_CCTV_ADVANCED.py --source "rtsp://user:pass@camera/stream"

Two cameras:
  python RAM_AI_CCTV_ADVANCED.py --source 0 --source "rtsp://..."

Enable YOLO:
  python RAM_AI_CCTV_ADVANCED.py --source 0 --enable-yolo

LAN API for RAM AI app:
  set RAM_AI_API_KEY=use-a-long-random-key
  python RAM_AI_CCTV_ADVANCED.py --source 0 --bind 0.0.0.0 --port 8765

API examples:
  GET  /api/status
  GET  /api/health
  GET  /api/events?limit=20
  GET  /api/event/12
  POST /api/query     {"query":"what happened recently?"}
  POST /api/feedback  {"event_id":12,"label":"useful"}
  GET  /stream/cam1.mjpg
  GET  /clip/12

Environment variables:
  RAM_AI_API_KEY
  RAM_AI_ALERT_WEBHOOK
  RAM_AI_TELEGRAM_TOKEN
  RAM_AI_TELEGRAM_CHAT_ID
  RAM_AI_LLM_ENDPOINT
  RAM_AI_VOICE_LANG=en-IN   (or te-IN)
"""
from __future__ import annotations

import argparse, collections, contextlib, datetime as dt, hashlib, json, os, queue
import re, shutil, signal, sqlite3, subprocess, sys, threading, time, traceback
import urllib.parse
from dataclasses import dataclass, asdict, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

VERSION = "2.0.0-prototype"

try:
    import numpy as np
except Exception:
    np = None
try:
    import cv2
except Exception:
    cv2 = None
try:
    import requests
except Exception:
    requests = None
try:
    from ultralytics import YOLO
except Exception:
    YOLO = None
try:
    import speech_recognition as sr
except Exception:
    sr = None
try:
    import pyttsx3
except Exception:
    pyttsx3 = None

BASE_DIR = Path(os.environ.get("RAM_AI_CCTV_DATA", "cctv_ai_data")).resolve()
CLIPS_DIR = BASE_DIR / "recordings"
EVIDENCE_DIR = BASE_DIR / "evidence"
FACES_DIR = BASE_DIR / "known_faces"
DB_PATH = BASE_DIR / "ram_ai_cctv.sqlite3"
CONFIG_PATH = BASE_DIR / "config.json"

DEFAULT_CONFIG = {
    "motion_threshold": 0.018,
    "pre_event_seconds": 4.0,
    "post_event_seconds": 5.0,
    "min_event_seconds": 0.8,
    "health_interval_seconds": 5.0,
    "blur_threshold": 65.0,
    "dark_threshold": 35.0,
    "bright_threshold": 225.0,
    "frozen_threshold": 1.0,
    "frozen_seconds": 7.0,
    "disk_warn_gb": 2.0,
    "person_confidence": 0.40,
    "yolo_confidence": 0.40,
    "face_lbph_threshold": 72.0,
    "valuable_missing_seconds": 8.0,
    "valuable_min_seen_count": 5,
    "watched_objects": ["laptop", "cell phone", "backpack", "handbag"],
    "alert_priorities": ["high", "critical"],
    "record_width": 960,
    "record_height": 540,
    "record_fps": 15.0,
    "jpeg_quality": 75,
    "retention_days": 14,
    "privacy_mask_unknown_faces": False,
}


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def ensure_dirs():
    for p in (BASE_DIR, CLIPS_DIR, EVIDENCE_DIR, FACES_DIR):
        p.mkdir(parents=True, exist_ok=True)


def safe_name(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s.strip())
    return s[:80] or "item"


def load_config() -> Dict[str, Any]:
    ensure_dirs()
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            x = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(x, dict): cfg.update(x)
        except Exception: pass
    else:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return cfg


def save_config(cfg: Dict[str, Any]):
    tmp = CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    tmp.replace(CONFIG_PATH)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


class EventDB:
    def __init__(self, path: Path):
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        with self.lock, self.conn:
            self.conn.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS events(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              camera_id TEXT,start_time TEXT,end_time TEXT,event_type TEXT,priority TEXT,
              motion_score REAL,confidence REAL,person_detected INTEGER,
              identities_json TEXT,objects_json TEXT,clip_path TEXT,sha256 TEXT,
              evidence_path TEXT,note TEXT,feedback TEXT,created_at TEXT);
            CREATE INDEX IF NOT EXISTS idx_events_time ON events(start_time DESC);
            CREATE TABLE IF NOT EXISTS audit(
              id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT,actor TEXT,action TEXT,detail TEXT);
            CREATE TABLE IF NOT EXISTS feedback(
              id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT,event_id INTEGER,label TEXT);
            """)

    def audit(self, action: str, detail: str = "", actor: str = "local"):
        with self.lock, self.conn:
            self.conn.execute("INSERT INTO audit(at,actor,action,detail) VALUES(?,?,?,?)",
                              (now_iso(), actor, action, detail[:2000]))

    def insert(self, e: Dict[str, Any]) -> int:
        keys = ["camera_id","start_time","end_time","event_type","priority","motion_score",
                "confidence","person_detected","identities_json","objects_json","clip_path",
                "sha256","evidence_path","note","created_at"]
        with self.lock, self.conn:
            cur = self.conn.execute(
                f"INSERT INTO events({','.join(keys)}) VALUES({','.join(['?']*len(keys))})",
                [e.get(k) for k in keys])
            return int(cur.lastrowid)

    def update_evidence(self, eid: int, digest: str, path: str):
        with self.lock, self.conn:
            self.conn.execute("UPDATE events SET sha256=?,evidence_path=? WHERE id=?", (digest,path,eid))

    def recent(self, limit=20, camera_id=None):
        limit = max(1, min(int(limit), 500))
        with self.lock:
            if camera_id:
                rows = self.conn.execute("SELECT * FROM events WHERE camera_id=? ORDER BY id DESC LIMIT ?",
                                         (camera_id,limit)).fetchall()
            else:
                rows = self.conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [self._row(r) for r in rows]

    def get(self, eid: int):
        with self.lock:
            r = self.conn.execute("SELECT * FROM events WHERE id=?", (eid,)).fetchone()
        return self._row(r) if r else None

    def set_feedback(self, eid: int, label: str):
        label = label.lower().strip()
        if label not in {"useful","ignore","false_alarm","confirmed"}:
            raise ValueError("label must be useful, ignore, false_alarm, or confirmed")
        with self.lock, self.conn:
            self.conn.execute("UPDATE events SET feedback=? WHERE id=?", (label,eid))
            self.conn.execute("INSERT INTO feedback(at,event_id,label) VALUES(?,?,?)", (now_iso(),eid,label))

    @staticmethod
    def _row(r):
        d = dict(r)
        for k, out in (("identities_json","identities"),("objects_json","objects")):
            try: d[out] = json.loads(d.get(k) or "[]")
            except Exception: d[out] = []
            d.pop(k, None)
        d["person_detected"] = bool(d.get("person_detected"))
        return d


@dataclass
class Detection:
    label: str
    confidence: float
    box: Tuple[int,int,int,int]
    identity: Optional[str] = None


class Detector:
    def __init__(self, cfg, enable_yolo=False, model="yolo11n.pt"):
        self.cfg, self.yolo, self.hog, self.mode = cfg, None, None, "hog"
        if enable_yolo and YOLO is not None:
            try:
                self.yolo = YOLO(model); self.mode = "yolo"
            except Exception as e:
                print("[WARN] YOLO unavailable; HOG fallback:", e)
        if cv2 is not None:
            try:
                self.hog = cv2.HOGDescriptor()
                self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            except Exception: pass

    def detect(self, frame) -> List[Detection]:
        if self.mode == "yolo" and self.yolo is not None:
            out=[]
            try:
                for res in self.yolo.predict(frame, verbose=False, conf=float(self.cfg["yolo_confidence"]), imgsz=640):
                    names = res.names
                    for b in res.boxes:
                        x1,y1,x2,y2 = map(int,b.xyxy[0].tolist())
                        out.append(Detection(str(names[int(b.cls[0])]), float(b.conf[0]), (x1,y1,x2,y2)))
            except Exception as e: print("[WARN] YOLO detect error:",e)
            return out
        if self.hog is None or cv2 is None: return []
        try:
            h,w = frame.shape[:2]; scale=min(1.0,640.0/max(w,1))
            small = cv2.resize(frame,(int(w*scale),int(h*scale))) if scale<1 else frame
            rects, weights = self.hog.detectMultiScale(small,winStride=(8,8),padding=(8,8),scale=1.05)
            out=[]
            for (x,y,bw,bh),wt in zip(rects,weights):
                c=max(0,min(float(wt),1))
                if c >= float(self.cfg["person_confidence"]):
                    out.append(Detection("person",c,(int(x/scale),int(y/scale),int((x+bw)/scale),int((y+bh)/scale))))
            return out
        except Exception: return []


class FaceEngine:
    def __init__(self,cfg):
        self.cfg,self.detector,self.recognizer,self.label_map,self.ready=cfg,None,None,{},False
        if cv2 is not None:
            try:
                self.detector=cv2.CascadeClassifier(str(Path(cv2.data.haarcascades)/"haarcascade_frontalface_default.xml"))
            except Exception: pass
        self.reload()

    def reload(self):
        self.recognizer,self.label_map,self.ready=None,{},False
        if cv2 is None or self.detector is None or not hasattr(cv2,"face") or np is None: return
        imgs=[]; labels=[]; lid=0
        for d in sorted(FACES_DIR.iterdir() if FACES_DIR.exists() else []):
            if not d.is_dir(): continue
            person=[]
            for p in d.glob("*"):
                if p.suffix.lower() not in {".jpg",".jpeg",".png"}: continue
                g=cv2.imread(str(p),cv2.IMREAD_GRAYSCALE)
                if g is not None: person.append(cv2.resize(g,(160,160)))
            if person:
                self.label_map[lid]=d.name; imgs.extend(person); labels.extend([lid]*len(person)); lid+=1
        if imgs:
            try:
                r=cv2.face.LBPHFaceRecognizer_create(); r.train(imgs,np.array(labels,dtype=np.int32))
                self.recognizer=r; self.ready=True
            except Exception: pass

    def largest_face(self,gray):
        if self.detector is None: return None
        faces=self.detector.detectMultiScale(gray,1.1,5,minSize=(55,55))
        return max(faces,key=lambda b:b[2]*b[3]) if len(faces) else None

    def detect(self,frame):
        if cv2 is None or self.detector is None: return []
        try:
            g=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY); faces=self.detector.detectMultiScale(g,1.1,5,minSize=(55,55)); out=[]
            for x,y,w,h in faces:
                ident="unknown"; conf=.5
                if self.ready and self.recognizer is not None:
                    label,dist=self.recognizer.predict(cv2.resize(g[y:y+h,x:x+w],(160,160)))
                    if dist <= float(self.cfg["face_lbph_threshold"]) and label in self.label_map:
                        ident=self.label_map[label]; conf=max(0,min(1,1-dist/120))
                out.append(Detection("face",conf,(x,y,x+w,y+h),ident))
            return out
        except Exception: return []


@dataclass
class CameraHealth:
    camera_id: str
    online: bool=False
    fps: float=0.0
    brightness: float=0.0
    blur_score: float=0.0
    frozen: bool=False
    read_failures: int=0
    width: int=0
    height: int=0
    disk_free_gb: float=0.0
    health_score: float=0.0
    issues: List[str]=field(default_factory=list)
    updated_at: str=field(default_factory=now_iso)


class HealthEngine:
    def __init__(self,cid,cfg):
        self.cid,self.cfg=cid,cfg; self.prev=None; self.frozen_since=None; self.read_failures=0; self.times=collections.deque(maxlen=60)
        self.health=CameraHealth(cid)
    def failed(self): self.read_failures += 1
    def update(self,frame):
        h=self.health; h.updated_at=now_iso(); h.read_failures=self.read_failures
        if cv2 is None or frame is None:
            h.online=False; h.health_score=0; h.issues=["camera unavailable"]; return h
        h.online=True; hh,ww=frame.shape[:2]; h.width=ww; h.height=hh
        g=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY); h.brightness=float(g.mean()); h.blur_score=float(cv2.Laplacian(g,cv2.CV_64F).var())
        t=time.time(); self.times.append(t)
        if len(self.times)>2 and self.times[-1]>self.times[0]: h.fps=(len(self.times)-1)/(self.times[-1]-self.times[0])
        sm=cv2.resize(g,(64,36)); frozen=False
        if self.prev is not None:
            diff=float(cv2.absdiff(sm,self.prev).mean())
            if diff<=float(self.cfg["frozen_threshold"]):
                self.frozen_since=self.frozen_since or t
                frozen=(t-self.frozen_since)>=float(self.cfg["frozen_seconds"])
            else: self.frozen_since=None
        self.prev=sm; h.frozen=frozen
        try: h.disk_free_gb=shutil.disk_usage(BASE_DIR).free/(1024**3)
        except Exception: h.disk_free_gb=0
        issues=[]
        if h.brightness<float(self.cfg["dark_threshold"]): issues.append("scene too dark")
        elif h.brightness>float(self.cfg["bright_threshold"]): issues.append("scene overexposed")
        if h.blur_score<float(self.cfg["blur_threshold"]): issues.append("blur/out-of-focus suspected")
        if h.frozen: issues.append("feed may be frozen")
        if h.read_failures>=5: issues.append("repeated frame read failures")
        if h.disk_free_gb<float(self.cfg["disk_warn_gb"]): issues.append("low disk space")
        score=100-min(30,h.read_failures*2)-(40 if h.frozen else 0)-(15 if h.blur_score<float(self.cfg["blur_threshold"]) else 0)-(10 if (h.brightness<float(self.cfg["dark_threshold"]) or h.brightness>float(self.cfg["bright_threshold"])) else 0)-(20 if h.disk_free_gb<float(self.cfg["disk_warn_gb"]) else 0)
        h.health_score=max(0,round(score,1)); h.issues=issues; return h


class ValuableWatcher:
    def __init__(self,cfg):
        self.cfg=cfg; self.state={x:{"seen":0,"last":0.0,"armed":False,"reported":False} for x in cfg.get("watched_objects",[])}
    def update(self,labels,activity):
        now=time.time(); present=set(labels); alerts=[]
        for label,s in self.state.items():
            if label in present:
                s["seen"]+=1; s["last"]=now; s["reported"]=False
                if s["seen"]>=int(self.cfg["valuable_min_seen_count"]): s["armed"]=True
            elif s["armed"] and s["last"] and now-s["last"]>=float(self.cfg["valuable_missing_seconds"]) and activity and not s["reported"]:
                alerts.append(label); s["reported"]=True
        return alerts


class AlertManager:
    def __init__(self):
        self.webhook=os.environ.get("RAM_AI_ALERT_WEBHOOK","").strip(); self.token=os.environ.get("RAM_AI_TELEGRAM_TOKEN","").strip(); self.chat=os.environ.get("RAM_AI_TELEGRAM_CHAT_ID","").strip(); self.q=queue.Queue(); self.stop_evt=threading.Event(); threading.Thread(target=self._run,daemon=True).start()
    def send(self,msg,payload): self.q.put((msg,payload))
    def _run(self):
        while not self.stop_evt.is_set():
            try: msg,payload=self.q.get(timeout=.5)
            except queue.Empty: continue
            if requests is not None:
                if self.webhook:
                    with contextlib.suppress(Exception): requests.post(self.webhook,json={"message":msg,"event":payload},timeout=5)
                if self.token and self.chat:
                    with contextlib.suppress(Exception): requests.post(f"https://api.telegram.org/bot{self.token}/sendMessage",data={"chat_id":self.chat,"text":msg},timeout=5)
            self.q.task_done()
    def close(self): self.stop_evt.set()


class CameraWorker(threading.Thread):
    def __init__(self,system,cid,source):
        super().__init__(daemon=True,name=f"camera-{cid}"); self.system=system; self.cid=cid; self.source=source; self.cfg=system.cfg; self.stop_evt=threading.Event(); self.lock=threading.RLock(); self.latest=None; self.health=HealthEngine(cid,self.cfg); self.watcher=ValuableWatcher(self.cfg); self.bg=cv2.createBackgroundSubtractorMOG2(history=500,varThreshold=28,detectShadows=True); self.pre=collections.deque(); self.recording=False; self.writer=None; self.started=0.0; self.last_trigger=0.0; self.event={}; self.path=None; self.last_health=0.0; self.n=0
    def _src(self): return int(self.source) if re.fullmatch(r"\d+",self.source) else self.source
    def run(self):
        cap=None; retry=1.0
        while not self.stop_evt.is_set():
            if cap is None:
                cap=cv2.VideoCapture(self._src())
                if not cap.isOpened(): cap=None; self.health.failed(); time.sleep(min(retry,8)); retry=min(8,retry*1.5); continue
                retry=1
            ok,frame=cap.read()
            if not ok or frame is None:
                self.health.failed(); cap.release(); cap=None; time.sleep(.5); continue
            self.n+=1; ts=time.time(); frame=cv2.resize(frame,(int(self.cfg["record_width"]),int(self.cfg["record_height"])))
            motion_score=self._motion(frame); motion=motion_score>=float(self.cfg["motion_threshold"])
            dets=self.system.detector.detect(frame) if (motion or self.n%3==0) else []
            faces=self.system.faces.detect(frame) if (motion or self.n%5==0) else []
            persons=[d for d in dets if d.label=="person"]; objects=[d for d in dets if d.label!="person"]; identities=sorted(set(d.identity or "unknown" for d in faces)); labels=sorted(set(d.label for d in objects)); missing=self.watcher.update(labels,bool(persons) or motion)
            types=[]; priority="low"; confidence=motion_score
            if motion: types.append("motion"); priority="medium"
            if persons: types.append("person"); priority="medium"; confidence=max(confidence,max(d.confidence for d in persons))
            if faces:
                types.append("face")
                if "unknown" in identities: priority="high"
            if missing: types.append("possible_object_removed"); priority="high"; confidence=max(confidence,.65)
            trigger=bool(types)
            self._set_latest(self._annotate(frame,dets,faces,motion_score,missing)); self._buffer(frame,ts)
            if trigger and not self.recording: self._start(ts,frame,types,priority,motion_score,confidence,identities,labels,missing)
            elif trigger: self.last_trigger=ts; self._merge(types,priority,motion_score,confidence,identities,labels,missing)
            if self.recording:
                self.writer.write(frame)
                if ts-self.last_trigger>=float(self.cfg["post_event_seconds"]): self._finish(ts)
            if ts-self.last_health>=float(self.cfg["health_interval_seconds"]): self.system.health[self.cid]=asdict(self.health.update(frame)); self.last_health=ts
        if self.recording: self._finish(time.time())
        if cap is not None: cap.release()
    def _motion(self,frame):
        g=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY); fg=self.bg.apply(g); _,fg=cv2.threshold(fg,220,255,cv2.THRESH_BINARY); fg=cv2.medianBlur(fg,5); return cv2.countNonZero(fg)/float(fg.shape[0]*fg.shape[1])
    def _buffer(self,frame,ts):
        ok,enc=cv2.imencode(".jpg",frame,[int(cv2.IMWRITE_JPEG_QUALITY),int(self.cfg["jpeg_quality"])])
        if ok: self.pre.append((ts,enc.tobytes()))
        cutoff=ts-float(self.cfg["pre_event_seconds"])
        while self.pre and self.pre[0][0]<cutoff: self.pre.popleft()
    def _start(self,ts,frame,types,priority,motion,conf,ids,objs,missing):
        self.recording=True; self.started=ts; self.last_trigger=ts; stamp=dt.datetime.now().strftime("%Y%m%d_%H%M%S"); self.path=CLIPS_DIR/f"{self.cid}_{stamp}.mp4"; h,w=frame.shape[:2]; self.writer=cv2.VideoWriter(str(self.path),cv2.VideoWriter_fourcc(*"mp4v"),float(self.cfg["record_fps"]),(w,h))
        for _,jpg in list(self.pre):
            f=cv2.imdecode(np.frombuffer(jpg,dtype=np.uint8),cv2.IMREAD_COLOR)
            if f is not None: self.writer.write(f)
        self.event={"types":set(types),"priority":priority,"motion":motion,"conf":conf,"ids":set(ids),"objs":set(objs),"missing":set(missing)}
    def _merge(self,types,priority,motion,conf,ids,objs,missing):
        e=self.event; e["types"].update(types); e["motion"]=max(e["motion"],motion); e["conf"]=max(e["conf"],conf); e["ids"].update(ids); e["objs"].update(objs); e["missing"].update(missing)
        rank={"low":0,"medium":1,"high":2,"critical":3}
        if rank[priority]>rank[e["priority"]]: e["priority"]=priority
    def _finish(self,ts):
        if not self.recording: return
        self.writer.release(); duration=ts-self.started; path=self.path; e=self.event; self.recording=False; self.writer=None; self.path=None; self.event={}
        if duration<float(self.cfg["min_event_seconds"]) or path is None or not path.exists():
            if path and path.exists(): path.unlink(); return
        ids=sorted(e["ids"]); objs=sorted(e["objs"]); missing=sorted(e["missing"]); types=sorted(e["types"]); note=""
        if missing: note="Possible object removal signal: "+", ".join(missing)+". Review video; this is not a theft determination."
        elif "unknown" in [x.lower() for x in ids]: note="Unknown face detected. Unknown identity does not imply wrongdoing."
        row={"camera_id":self.cid,"start_time":dt.datetime.fromtimestamp(self.started).astimezone().isoformat(timespec="seconds"),"end_time":dt.datetime.fromtimestamp(ts).astimezone().isoformat(timespec="seconds"),"event_type":"+".join(types) or "activity","priority":e["priority"],"motion_score":round(e["motion"],4),"confidence":round(e["conf"],4),"person_detected":1 if "person" in types else 0,"identities_json":json.dumps(ids),"objects_json":json.dumps(objs),"clip_path":str(path.resolve()),"sha256":"","evidence_path":"","note":note,"created_at":now_iso()}
        eid=self.system.db.insert(row); digest=sha256_file(path); capsule={"schema":"ram-ai-evidence-capsule/v1","event_id":eid,"software_version":VERSION,"created_at":now_iso(),"camera_id":self.cid,"event":{"start_time":row["start_time"],"end_time":row["end_time"],"type":row["event_type"],"priority":row["priority"],"confidence":row["confidence"],"identities":ids,"objects":objs,"note":note},"clip":{"path":str(path.resolve()),"sha256":digest,"size_bytes":path.stat().st_size},"camera_health":self.system.health.get(self.cid,{}),"integrity_note":"SHA-256 detects later file changes; it is not capture-time authenticity by itself."}
        ep=EVIDENCE_DIR/f"event_{eid:06d}.json"; ep.write_text(json.dumps(capsule,indent=2),encoding="utf-8"); self.system.db.update_evidence(eid,digest,str(ep.resolve())); payload=self.system.db.get(eid); print(f"\n[EVENT {eid}] {self.cid} | {row['event_type']} | {row['priority'].upper()}")
        if note: print(" ",note)
        if row["priority"] in self.cfg.get("alert_priorities",[]): self.system.alerts.send(f"RAM AI CCTV {row['priority'].upper()} event #{eid} on {self.cid}: {row['event_type']}",payload)
    def _annotate(self,frame,dets,faces,motion,missing):
        out=frame.copy()
        for d in dets:
            x1,y1,x2,y2=d.box; cv2.rectangle(out,(x1,y1),(x2,y2),(255,255,255),2); cv2.putText(out,f"{d.label} {d.confidence:.2f}",(x1,max(20,y1-8)),cv2.FONT_HERSHEY_SIMPLEX,.55,(255,255,255),2)
        for d in faces:
            x1,y1,x2,y2=d.box; cv2.rectangle(out,(x1,y1),(x2,y2),(200,200,200),2); cv2.putText(out,f"face:{d.identity or 'unknown'}",(x1,max(20,y1-8)),cv2.FONT_HERSHEY_SIMPLEX,.55,(255,255,255),2)
            if self.cfg.get("privacy_mask_unknown_faces") and d.identity=="unknown":
                roi=out[y1:y2,x1:x2]
                if roi.size: out[y1:y2,x1:x2]=cv2.GaussianBlur(roi,(31,31),0)
        cv2.putText(out,f"{self.cid} motion={motion:.3f}",(10,25),cv2.FONT_HERSHEY_SIMPLEX,.65,(255,255,255),2)
        if missing: cv2.putText(out,"REVIEW: possible object removed",(10,55),cv2.FONT_HERSHEY_SIMPLEX,.65,(255,255,255),2)
        return out
    def _set_latest(self,f):
        with self.lock: self.latest=f.copy()
    def jpeg(self):
        with self.lock:
            if self.latest is None: return None
            ok,enc=cv2.imencode(".jpg",self.latest,[int(cv2.IMWRITE_JPEG_QUALITY),75]); return enc.tobytes() if ok else None
    def stop(self): self.stop_evt.set()


class QueryEngine:
    def __init__(self,system): self.system=system
    def answer(self,q):
        q=(q or "").strip(); low=q.lower(); self.system.db.audit("query",q[:500],"assistant-user")
        endpoint=os.environ.get("RAM_AI_LLM_ENDPOINT","").strip()
        if endpoint and requests is not None:
            with contextlib.suppress(Exception):
                r=requests.post(endpoint,json={"question":q,"events":self.system.db.recent(20)},timeout=15)
                if r.ok:
                    d=r.json()
                    if isinstance(d,dict) and d.get("answer"): return {"answer":str(d["answer"]),"data":d.get("data")}
        if any(k in low for k in ["help","commands","ఏం అడగాలి","emi adagali"]): return {"answer":self.help(),"data":None}
        if "status" in low or "స్టేటస్" in low: return {"answer":json.dumps(self.system.status(),indent=2),"data":self.system.status()}
        if "health" in low or "హెల్త్" in low or "camera ela" in low or "కెమెరా ఎలా" in low: return {"answer":self.health_text(),"data":self.system.health}
        m=re.search(r"(?:event|ఈవెంట్)\s*#?\s*(\d+)",low)
        if m:
            e=self.system.db.get(int(m.group(1))); return {"answer":self.event_text(e) if e else "Event not found.","data":e}
        rows=self.system.db.recent(50)
        if any(k in low for k in ["unknown","తెలియని","evaru teliyadu"]): rows=[e for e in rows if "unknown" in [x.lower() for x in e.get("identities",[])]]; return {"answer":self.events(rows[:10],"Unknown-face events"),"data":rows[:10]}
        if any(k in low for k in ["who came","person","ఎవరు వచ్చారు","evaru vacharu","ఎవరు"]): rows=[e for e in rows if e.get("person_detected")]; return {"answer":self.events(rows[:10],"Person events"),"data":rows[:10]}
        if any(k in low for k in ["object","missing","removed","వస్తువు","తీసుకెళ్ల","theft"]): rows=[e for e in rows if "possible_object_removed" in e.get("event_type","")]; return {"answer":self.events(rows[:10],"Object-removal review events")+"\nNot a theft determination.","data":rows[:10]}
        if any(k in low for k in ["what happened","recent","ఏం జరిగింది","emi jarigindi","unusual"]): return {"answer":self.events(rows[:10],"Recent CCTV events"),"data":rows[:10]}
        return {"answer":"Try: what happened recently? | camera health | who came? | unknown events | event 5","data":None}
    def help(self): return "Commands: status | health | recent question | who came? | unknown | event 12 | feedback 12 useful | open 12 | enroll Alice | voice | quit"
    def health_text(self):
        if not self.system.health: return "Health data not ready yet."
        return "\n".join(f"{cid}: {h.get('health_score',0):.0f}/100, FPS {h.get('fps',0):.1f}; {', '.join(h.get('issues') or []) or 'no major issue detected'}" for cid,h in self.system.health.items())
    def event_text(self,e): return f"Event {e['id']} | {e['camera_id']} | {e['start_time']} | {e['event_type']} | {e['priority']} | identities={','.join(e.get('identities') or []) or '-'} | confidence={float(e.get('confidence') or 0):.2f} | {e.get('note') or ''}"
    def events(self,rows,title): return title+": none found." if not rows else title+":\n"+"\n".join(f"#{e['id']} | {e['camera_id']} | {e['start_time']} | {e['event_type']} | {e['priority']} | identity={','.join(e.get('identities') or []) or '-'}" for e in rows)


class APIServer:
    def __init__(self,system,bind,port,key): self.system,self.bind,self.port,self.key=system,bind,port,key; self.httpd=None
    def start(self):
        system,key=self.system,self.key
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*a): return
            def cors(self): self.send_header("Access-Control-Allow-Origin","*"); self.send_header("Access-Control-Allow-Headers","Content-Type, X-API-Key"); self.send_header("Access-Control-Allow-Methods","GET, POST, OPTIONS")
            def auth(self):
                if not key: return True
                supplied=self.headers.get("X-API-Key","") or (urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("key") or [""])[0]
                return hashlib.sha256(supplied.encode()).digest()==hashlib.sha256(key.encode()).digest()
            def js(self,obj,status=200):
                raw=json.dumps(obj,ensure_ascii=False,default=str).encode(); self.send_response(status); self.cors(); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)
            def body(self):
                n=int(self.headers.get("Content-Length","0") or 0); return json.loads(self.rfile.read(min(n,1048576)).decode() or "{}")
            def do_OPTIONS(self): self.send_response(204); self.cors(); self.end_headers()
            def do_GET(self):
                if not self.auth(): return self.js({"error":"unauthorized"},401)
                parsed=urllib.parse.urlparse(self.path); path=parsed.path; qs=urllib.parse.parse_qs(parsed.query)
                if path=="/": return self.js({"service":"RAM AI CCTV","version":VERSION})
                if path=="/api/status": return self.js(system.status())
                if path=="/api/health": return self.js(system.health)
                if path=="/api/events": return self.js(system.db.recent(int((qs.get("limit") or ["20"])[0]),(qs.get("camera") or [None])[0]))
                m=re.fullmatch(r"/api/event/(\d+)",path)
                if m:
                    e=system.db.get(int(m.group(1))); return self.js(e or {"error":"not found"},200 if e else 404)
                m=re.fullmatch(r"/stream/([^/]+)\.mjpg",path)
                if m: return self.stream(urllib.parse.unquote(m.group(1)))
                m=re.fullmatch(r"/clip/(\d+)",path)
                if m: return self.clip(int(m.group(1)))
                return self.js({"error":"not found"},404)
            def do_POST(self):
                if not self.auth(): return self.js({"error":"unauthorized"},401)
                try: b=self.body()
                except Exception: return self.js({"error":"invalid json"},400)
                path=urllib.parse.urlparse(self.path).path
                if path=="/api/query": return self.js(system.query.answer(str(b.get("query",""))))
                if path=="/api/feedback":
                    try: system.feedback(int(b["event_id"]),str(b["label"])); return self.js({"ok":True})
                    except Exception as e: return self.js({"error":str(e)},400)
                return self.js({"error":"not found"},404)
            def stream(self,cid):
                w=system.workers_by_id.get(cid)
                if not w: return self.js({"error":"camera not found"},404)
                self.send_response(200); self.cors(); self.send_header("Cache-Control","no-cache"); self.send_header("Content-Type","multipart/x-mixed-replace; boundary=frame"); self.end_headers()
                try:
                    while system.running:
                        jpg=w.jpeg()
                        if jpg: self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "+str(len(jpg)).encode()+b"\r\n\r\n"+jpg+b"\r\n")
                        time.sleep(.08)
                except Exception: pass
            def clip(self,eid):
                e=system.db.get(eid); p=Path(e.get("clip_path") or "") if e else None
                if p is None or not p.exists(): return self.js({"error":"clip missing"},404)
                self.send_response(200); self.cors(); self.send_header("Content-Type","video/mp4"); self.send_header("Content-Length",str(p.stat().st_size)); self.end_headers()
                with p.open("rb") as f: shutil.copyfileobj(f,self.wfile)
        self.httpd=ThreadingHTTPServer((self.bind,self.port),Handler); threading.Thread(target=self.httpd.serve_forever,daemon=True).start()
    def stop(self):
        if self.httpd:
            with contextlib.suppress(Exception): self.httpd.shutdown(); self.httpd.server_close()


class RamAICCTV:
    def __init__(self,args):
        ensure_dirs(); self.args=args; self.cfg=load_config();
        if args.watch_object: self.cfg["watched_objects"]=list(dict.fromkeys(self.cfg.get("watched_objects",[])+args.watch_object)); save_config(self.cfg)
        self.db=EventDB(DB_PATH); self.alerts=AlertManager(); self.detector=Detector(self.cfg,args.enable_yolo,args.yolo_model); self.faces=FaceEngine(self.cfg); self.health={}; self.workers=[]; self.workers_by_id={}; self.running=False; self.query=QueryEngine(self); self.api=None; self.started_at=now_iso()
    def start(self):
        self.running=True
        for i,src in enumerate(self.args.source,1):
            w=CameraWorker(self,f"cam{i}",src); self.workers.append(w); self.workers_by_id[w.cid]=w; w.start()
        key=os.environ.get("RAM_AI_API_KEY","").strip()
        if self.args.bind not in {"127.0.0.1","localhost","::1"} and not key: raise RuntimeError("Set RAM_AI_API_KEY before exposing API beyond localhost.")
        self.api=APIServer(self,self.args.bind,self.args.port,key); self.api.start(); self.db.audit("system_start",str(self.args.source)); self.retention()
    def stop(self):
        if not self.running: return
        self.running=False
        for w in self.workers: w.stop()
        for w in self.workers: w.join(timeout=3)
        if self.api: self.api.stop()
        self.alerts.close(); self.db.audit("system_stop"); print("\nRAM AI CCTV stopped.")
    def status(self):
        with self.db.lock: count=self.db.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        return {"service":"RAM AI CCTV","version":VERSION,"running":self.running,"started_at":self.started_at,"cameras":list(self.workers_by_id),"detector_mode":self.detector.mode,"face_recognition_ready":self.faces.ready,"event_count":count,"data_dir":str(BASE_DIR),"api":f"http://{self.args.bind}:{self.args.port}"}
    def feedback(self,eid,label):
        if not self.db.get(eid): raise ValueError("event not found")
        self.db.set_feedback(eid,label); mt=float(self.cfg["motion_threshold"]); mt=min(.08,mt*1.04) if label in {"ignore","false_alarm"} else max(.005,mt*.99); self.cfg["motion_threshold"]=round(mt,5); save_config(self.cfg)
    def retention(self):
        days=int(self.cfg.get("retention_days",14)); cutoff=time.time()-days*86400
        if days<=0: return
        for folder in (CLIPS_DIR,EVIDENCE_DIR):
            for p in folder.glob("*"):
                with contextlib.suppress(Exception):
                    if p.is_file() and p.stat().st_mtime<cutoff: p.unlink()
    def enroll(self,name,samples=12):
        if not self.workers: return print("No camera.")
        d=FACES_DIR/safe_name(name); d.mkdir(parents=True,exist_ok=True); w=self.workers[0]; saved=0; deadline=time.time()+35; print(f"Enrolling {name}; look at camera.")
        while saved<samples and time.time()<deadline:
            with w.lock: frame=None if w.latest is None else w.latest.copy()
            if frame is None: time.sleep(.3); continue
            g=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY); face=self.faces.largest_face(g)
            if face is not None:
                x,y,fw,fh=face; crop=g[y:y+fh,x:x+fw]
                if crop.size: cv2.imwrite(str(d/f"{int(time.time()*1000)}_{saved}.jpg"),cv2.resize(crop,(160,160))); saved+=1; print(f" sample {saved}/{samples}"); time.sleep(.35)
            else: time.sleep(.2)
        self.faces.reload(); print(f"Saved {saved}; recognition_ready={self.faces.ready}")
    def open_event(self,eid):
        e=self.db.get(eid); p=Path(e.get("clip_path") or "") if e else None
        if p is None or not p.exists(): return print("Clip not found.")
        try:
            if os.name=="nt": os.startfile(str(p))
            elif sys.platform=="darwin": subprocess.Popen(["open",str(p)])
            else: subprocess.Popen(["xdg-open",str(p)])
        except Exception: print("Clip:",p)


def listen_once():
    if sr is None: print("Install SpeechRecognition + microphone dependency."); return None
    try:
        r=sr.Recognizer(); lang=os.environ.get("RAM_AI_VOICE_LANG","en-IN")
        with sr.Microphone() as source: print("Listening..."); r.adjust_for_ambient_noise(source,duration=.5); audio=r.listen(source,timeout=7,phrase_time_limit=12)
        text=r.recognize_google(audio,language=lang); print("You:",text); return text
    except Exception as e: print("Voice input failed:",e); return None


def speak(text):
    if pyttsx3 is None: return
    with contextlib.suppress(Exception):
        e=pyttsx3.init(); e.say(text); e.runAndWait()


def doctor():
    print("RAM AI CCTV Doctor")
    print("Python:",sys.version.split()[0]); print("NumPy:","OK" if np is not None else "MISSING"); print("OpenCV:",getattr(cv2,"__version__","MISSING") if cv2 is not None else "MISSING"); print("OpenCV LBPH:","YES" if cv2 is not None and hasattr(cv2,"face") else "NO"); print("YOLO:","YES" if YOLO is not None else "NO (optional)"); print("requests:","YES" if requests is not None else "NO (optional)"); print("SpeechRecognition:","YES" if sr is not None else "NO (optional)"); print("pyttsx3:","YES" if pyttsx3 is not None else "NO (optional)"); print("Data:",BASE_DIR)


def self_test():
    ensure_dirs(); print("Running self-test...")
    if np is None or cv2 is None: print("[FAIL] install numpy opencv-contrib-python"); return 2
    try:
        p=BASE_DIR/"_selftest.sqlite3"; p.unlink(missing_ok=True); db=EventDB(p); eid=db.insert({"camera_id":"test","start_time":now_iso(),"end_time":now_iso(),"event_type":"motion","priority":"low","motion_score":.1,"confidence":.5,"person_detected":0,"identities_json":"[]","objects_json":"[]","clip_path":"","sha256":"","evidence_path":"","note":"selftest","created_at":now_iso()}); assert db.get(eid)["event_type"]=="motion"; frame=np.zeros((240,320,3),dtype=np.uint8); assert cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY).shape==(240,320); print("[PASS] SQLite + OpenCV"); return 0
    except Exception: traceback.print_exc(); return 1


def cli(system):
    print("\nRAM AI CCTV ready."); print(system.query.help()); print(f"API: http://{system.args.bind}:{system.args.port}")
    while system.running:
        try: line=input("\nRAM-AI> ").strip()
        except (EOFError,KeyboardInterrupt): break
        if not line: continue
        low=line.lower()
        if low in {"quit","exit","stop"}: break
        if low=="doctor": doctor(); continue
        if low=="voice":
            q=listen_once()
            if q: ans=system.query.answer(q)["answer"]; print(ans); speak(ans)
            continue
        m=re.fullmatch(r"feedback\s+(\d+)\s+(useful|ignore|false_alarm|confirmed)",low)
        if m:
            try: system.feedback(int(m.group(1)),m.group(2)); print("Feedback saved; bounded sensitivity update applied.")
            except Exception as e: print("Error:",e)
            continue
        m=re.fullmatch(r"open\s+(\d+)",low)
        if m: system.open_event(int(m.group(1))); continue
        m=re.fullmatch(r"enroll\s+(.+)",line,re.I)
        if m: system.enroll(m.group(1).strip()); continue
        print(system.query.answer(line)["answer"])


def parser():
    p=argparse.ArgumentParser(description="RAM AI CCTV advanced single-file prototype"); p.add_argument("--source",action="append",default=None,help="camera index, video path, RTSP; repeat for multi-camera"); p.add_argument("--enable-yolo",action="store_true"); p.add_argument("--yolo-model",default="yolo11n.pt"); p.add_argument("--watch-object",action="append",default=[]); p.add_argument("--bind",default="127.0.0.1"); p.add_argument("--port",type=int,default=8765); p.add_argument("--doctor",action="store_true"); p.add_argument("--self-test",action="store_true"); return p


def main():
    args=parser().parse_args()
    if args.doctor: doctor(); return 0
    if args.self_test: return self_test()
    if cv2 is None or np is None: print("Install: python -m pip install numpy opencv-contrib-python"); return 2
    if not args.source: args.source=["0"]
    system=RamAICCTV(args)
    def sig(*_): system.stop()
    with contextlib.suppress(Exception): signal.signal(signal.SIGINT,sig); signal.signal(signal.SIGTERM,sig)
    try: system.start(); cli(system)
    except Exception as e: print("Fatal error:",e); traceback.print_exc(); return 1
    finally: system.stop()
    return 0

if __name__=="__main__": raise SystemExit(main())
