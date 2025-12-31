from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
import json
import logging
import datetime

logger = logging.getLogger("main.models")

@dataclass
class AutomationItem:
    name: str = "Sin nombre"
    comment: str = ""
    type: str = "base"

    def to_dict(self):
        return {
            "name": self.name,
            "comment": self.comment,
            "type": self.type
        }

@dataclass
class DemoItem(AutomationItem):
    data: List[Any] = field(default_factory=list)
    type: str = "demo"

    def to_dict(self):
        d = super().to_dict()
        d["data"] = self.data
        return d

@dataclass
class WildcardItem(AutomationItem):
    min_time: float = 0.0
    max_time: float = 0.0
    datetime_target: Optional[str] = None
    threshold: Optional[int] = None
    type: str = "wildcard" # or internet_wait, battery_wait, date_start, etc.
    
    # Override init to handle different wildcard types easily if needed, 
    # but for now we keep it simple data container
    
    def to_dict(self):
        d = super().to_dict()
        if self.min_time: d["min_time"] = self.min_time
        if self.max_time: d["max_time"] = self.max_time
        if self.datetime_target: d["datetime_target"] = self.datetime_target
        if self.threshold is not None: d["threshold"] = self.threshold
        return d

@dataclass
class Project:
    name: str = "Proyecto Sin Nombre"
    description: str = ""
    created: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    modified: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    version: str = "2.0"
    sequence: List[AutomationItem] = field(default_factory=list)
    file_path: Optional[str] = None

    def to_dict(self):
        return {
            "metadata": {
                "name": self.name,
                "description": self.description,
                "created": self.created,
                "modified": self.modified,
                "version": self.version
            },
            "sequence": [item.to_dict() for item in self.sequence],
            "demonstrations": [item.to_dict() for item in self.sequence if item.type == 'demo'],
            "wildcards": [item.to_dict() for item in self.sequence if item.type != 'demo']
        }
    
    @classmethod
    def from_dict(cls, data):
        meta = data.get("metadata", {})
        proj = cls(
            name=meta.get("name", "Sin nombre"),
            description=meta.get("description", ""),
            created=meta.get("created", ""),
            modified=meta.get("modified", ""),
            version=meta.get("version", "2.0")
        )
        
        # Load sequence
        # Try 'sequence' list first, if not exists, merge demos and wildcards (legacy support)
        seq_data = data.get("sequence", [])
        if not seq_data:
             seq_data = data.get("demonstrations", []) + data.get("wildcards", [])

        for item_data in seq_data:
             itype = item_data.get("type", "demo")
             if itype == "demo":
                 proj.sequence.append(DemoItem(
                     name=item_data.get("name", ""),
                     comment=item_data.get("comment", ""),
                     data=item_data.get("data", [])
                 ))
             else:
                 # It's a wildcard of some sort
                 proj.sequence.append(WildcardItem(
                     name=item_data.get("name", ""),
                     comment=item_data.get("comment", ""),
                     type=itype,
                     min_time=item_data.get("min_time", 0.0),
                     max_time=item_data.get("max_time", 0.0),
                     datetime_target=item_data.get("datetime_target"),
                     threshold=item_data.get("threshold")
                 ))
        return proj

    def save(self, filepath):
        self.modified = datetime.datetime.now().isoformat()
        self.file_path = filepath
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            
    @classmethod
    def load(cls, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        proj = cls.from_dict(data)
        proj.file_path = filepath
        return proj
