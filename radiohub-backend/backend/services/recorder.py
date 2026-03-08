"""
RadioHub v0.1.4 - Recorder Service

Stream-Aufnahme mit FFmpeg
"""
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

from ..database import db_session
from ..config import get_radio_recordings_dir


class RecordingSession:
    def __init__(self, session_id: str, station_uuid: str, station_name: str,
                 stream_url: str, bitrate: int = 0):
        self.id = session_id
        self.station_uuid = station_uuid
        self.station_name = station_name
        self.stream_url = stream_url
        self.bitrate = bitrate
        self.start_time = datetime.now()
        self.process: Optional[subprocess.Popen] = None
        self.file_path: Optional[Path] = None
    
    @property
    def duration(self) -> float:
        return (datetime.now() - self.start_time).total_seconds()
    
    @property
    def file_size(self) -> int:
        if self.file_path and self.file_path.exists():
            return self.file_path.stat().st_size
        return 0


class RecorderManager:
    def __init__(self):
        self.active_session: Optional[RecordingSession] = None
    
    def start(self, station_uuid: str, station_name: str, stream_url: str,
              bitrate: int = 0) -> dict:
        """Startet Aufnahme"""
        
        # Bereits aktive Aufnahme?
        if self.active_session:
            return {
                "success": False,
                "error": "Aufnahme läuft bereits",
                "session_id": self.active_session.id
            }
        
        # Session erstellen
        session_id = f"rec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in station_name)[:50]
        filename = f"{session_id}_{safe_name}.mp3"
        file_path = get_radio_recordings_dir() / filename
        
        session = RecordingSession(
            session_id=session_id,
            station_uuid=station_uuid,
            station_name=station_name,
            stream_url=stream_url,
            bitrate=bitrate
        )
        session.file_path = file_path
        
        # FFmpeg starten
        cmd = [
            "ffmpeg", "-y",
            "-i", stream_url,
            "-c:a", "libmp3lame",
            "-b:a", f"{bitrate}k" if bitrate > 0 else "192k",
            "-f", "mp3",
            str(file_path)
        ]
        
        try:
            session.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.active_session = session
            
            # In DB speichern
            with db_session() as conn:
                c = conn.cursor()
                c.execute('''INSERT INTO sessions 
                    (id, station_uuid, station_name, stream_url, bitrate, start_time, file_path, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (session_id, station_uuid, station_name, stream_url, bitrate,
                     session.start_time.isoformat(), str(file_path), "recording"))
            
            print(f"✓ Aufnahme gestartet: {session_id}")
            return {"success": True, "session_id": session_id}
            
        except Exception as e:
            print(f"✗ Aufnahme fehlgeschlagen: {e}")
            return {"success": False, "error": str(e)}
    
    def stop(self) -> dict:
        """Stoppt aktive Aufnahme"""
        
        if not self.active_session:
            return {"success": False, "error": "Keine aktive Aufnahme"}
        
        session = self.active_session
        
        # FFmpeg stoppen
        if session.process:
            session.process.terminate()
            try:
                session.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                session.process.kill()
        
        # DB aktualisieren
        end_time = datetime.now()
        duration = session.duration
        file_size = session.file_size
        
        with db_session() as conn:
            c = conn.cursor()
            c.execute('''UPDATE sessions SET 
                end_time = ?, duration = ?, file_size = ?, status = ?
                WHERE id = ?''',
                (end_time.isoformat(), duration, file_size, "completed", session.id))
        
        print(f"✓ Aufnahme gestoppt: {session.id} ({duration:.0f}s, {file_size/1024/1024:.1f}MB)")
        
        result = {
            "success": True,
            "session_id": session.id,
            "duration": duration,
            "file_size": file_size,
            "file_path": str(session.file_path)
        }
        
        self.active_session = None
        return result
    
    def get_status(self) -> dict:
        """Aktueller Aufnahme-Status"""
        
        if not self.active_session:
            return {"recording": False}
        
        session = self.active_session
        return {
            "recording": True,
            "session_id": session.id,
            "station_name": session.station_name,
            "duration": session.duration,
            "file_size": session.file_size
        }
    
    def get_sessions(self, limit: int = 50) -> list:
        """Alle Sessions aus DB"""
        
        with db_session() as conn:
            c = conn.cursor()
            c.execute('''SELECT * FROM sessions 
                ORDER BY start_time DESC LIMIT ?''', (limit,))
            return [dict(row) for row in c.fetchall()]
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """Einzelne Session"""
        
        with db_session() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = c.fetchone()
            return dict(row) if row else None
    
    def delete_session(self, session_id: str) -> bool:
        """Session und Datei löschen"""
        
        session = self.get_session(session_id)
        if not session:
            return False
        
        # Datei löschen
        if session.get("file_path"):
            file_path = Path(session["file_path"])
            if file_path.exists():
                file_path.unlink()
        
        # DB-Eintrag löschen
        with db_session() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        
        return True


# Singleton
rec_manager = RecorderManager()
