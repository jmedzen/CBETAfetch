"""
CBETAfetch 2.0 - Buddhist Scripture Preset Manager
Manages curated and user-customized Buddhist scripture presets with disk persistence.
"""

import os
import json
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


DEFAULT_BUDDHIST_PRESETS = [
    {
        "id": "weishi",
        "title": "唯識根本經論",
        "category": "瑜伽唯識",
        "badge": "慈恩宗規",
        "description": "窺基大師會釋十師異義之《成唯識論》與無著世親根本論典",
        "sutras": [
            {"id": "T1585", "name": "成唯識論", "vols": "10卷", "author": "護法等菩薩造 玄奘譯"},
            {"id": "T1586", "name": "唯識三十論頌", "vols": "1卷", "author": "世親菩薩造 玄奘譯"},
            {"id": "T1590", "name": "唯識二十論", "vols": "1卷", "author": "世親菩薩造 玄奘譯"},
            {"id": "T1592", "name": "攝大乘論", "vols": "3卷", "author": "無著菩薩造 佛陀扇多譯"},
            {"id": "T1599", "name": "辯中邊論", "vols": "3卷", "author": "世親菩薩造 玄奘譯"}
        ],
        "default_ids": "T1585\nT1586\nT1590\nT1592\nT1599",
        "is_custom": False
    },
    {
        "id": "prajna",
        "title": "般若波羅蜜多部",
        "category": "般若空宗",
        "badge": "斷疑生信",
        "description": "大乘空宗核心寶典，破執顯性、甚深般若直指菩提",
        "sutras": [
            {"id": "T0235", "name": "金剛般若波羅蜜經", "vols": "1卷", "author": "鳩摩羅什譯"},
            {"id": "T0251", "name": "般若波羅蜜多心經", "vols": "1卷", "author": "玄奘譯"},
            {"id": "T0261", "name": "大乘大集地藏十輪經", "vols": "8卷", "author": "玄奘譯"},
            {"id": "T0220", "name": "大般若波羅蜜多經(精選)", "vols": "初分卷一", "author": "玄奘譯"}
        ],
        "default_ids": "T0235\nT0251\nT0261",
        "is_custom": False
    },
    {
        "id": "agama",
        "title": "根本阿含部類",
        "category": "原始根本",
        "badge": "正法久住",
        "description": "初期佛教佛陀親炙言教，四阿含根本聖典選輯",
        "sutras": [
            {"id": "T0001", "name": "長阿含經", "vols": "22卷", "author": "後秦 佛陀耶舍共竺佛念譯"},
            {"id": "T0026", "name": "中阿含經", "vols": "60卷", "author": "東晉 僧伽提婆譯"},
            {"id": "T0099", "name": "雜阿含經", "vols": "50卷", "author": "劉宋 求那跋陀羅譯"}
        ],
        "default_ids": "T0001\nT0026\nT0099",
        "is_custom": False
    },
    {
        "id": "saddharma",
        "title": "法華楞嚴楞伽部",
        "category": "法華涅槃",
        "badge": "如來藏識",
        "description": "一乘圓教與性相融通之傳世重典，直指如來藏真如妙心",
        "sutras": [
            {"id": "T0262", "name": "妙法蓮華經", "vols": "7卷", "author": "後秦 鳩摩羅什譯"},
            {"id": "T0945", "name": "大佛頂如來密因修證了義諸菩薩萬行首楞嚴經", "vols": "10卷", "author": "般剌密帝譯"},
            {"id": "T0670", "name": "楞伽阿跋多羅寶經", "vols": "4卷", "author": "劉宋 求那跋陀羅譯"}
        ],
        "default_ids": "T0262\nT0945\nT0670",
        "is_custom": False
    },
    {
        "id": "chan",
        "title": "禪宗祖師要籍",
        "category": "禪門祖印",
        "badge": "直指人心",
        "description": "東土祖師真傳心印，不立文字，見性成佛之宗門寶鑑",
        "sutras": [
            {"id": "T2008", "name": "六祖大師法寶壇經", "vols": "1卷", "author": "唐 惠能大師說"},
            {"id": "T2076", "name": "景德傳燈錄", "vols": "30卷", "author": "宋 道原纂"}
        ],
        "default_ids": "T2008\nT2076",
        "is_custom": False
    },
    {
        "id": "rare_canons",
        "title": "嘉興藏與卍續藏珍稀論著",
        "category": "明清嘉興",
        "badge": "雙字藏號",
        "description": "嘉興藏方冊本與續藏珍稀注疏（測試雙字元 JB、ZS 藏號解析能力）",
        "sutras": [
            {"id": "JB234", "name": "慈恩宗規", "vols": "1卷", "author": "明 嘉興大藏經"},
            {"id": "JB235", "name": "慈恩傳略", "vols": "1卷", "author": "明 嘉興大藏經"},
            {"id": "X0367", "name": "金剛經解註", "vols": "1卷", "author": "卍新纂續藏經"}
        ],
        "default_ids": "JB234\nJB235\nX0367",
        "is_custom": False
    }
]


class PresetModel(BaseModel):
    id: str
    title: str
    category: str = "自訂部類"
    badge: str = "常用"
    description: str = ""
    sutras: List[Dict[str, str]] = Field(default_factory=list)
    default_ids: str
    is_custom: bool = True


class PresetManager:
    """
    Manages loading, creating, updating, and deleting scripture presets.
    """

    def __init__(self, storage_dir: str):
        self.storage_dir = os.path.abspath(storage_dir)
        os.makedirs(self.storage_dir, exist_ok=True)
        self.presets: Dict[str, PresetModel] = {}
        self._init_storage()

    def _init_storage(self):
        """Seed default presets if absent, then load all presets."""
        for p in DEFAULT_BUDDHIST_PRESETS:
            fpath = os.path.join(self.storage_dir, f"{p['id']}.json")
            if not os.path.exists(fpath):
                try:
                    with open(fpath, "w", encoding="utf-8") as f:
                        json.dump(p, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(f"Error seeding preset {p['id']}: {e}")

        self.reload()

    def reload(self):
        self.presets.clear()
        if not os.path.exists(self.storage_dir):
            return

        for fname in sorted(os.listdir(self.storage_dir)):
            if fname.endswith(".json") and not fname.startswith("."):
                fpath = os.path.join(self.storage_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        preset = PresetModel(**data)
                        self.presets[preset.id] = preset
                except Exception as e:
                    print(f"Error loading preset from {fname}: {e}")

    def list_presets(self) -> List[Dict[str, Any]]:
        return [p.model_dump() for p in self.presets.values()]

    def get_preset(self, preset_id: str) -> Optional[PresetModel]:
        return self.presets.get(preset_id)

    def save_preset(self, preset_data: Dict[str, Any]) -> PresetModel:
        # Generate safe slug id if needed
        p_id = preset_data.get("id") or ""
        p_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", p_id).strip("_")
        if not p_id:
            import time
            p_id = f"custom_{int(time.time())}"
        preset_data["id"] = p_id

        # Auto-generate sutras summary if missing
        if not preset_data.get("sutras"):
            ids = [line.strip() for line in preset_data.get("default_ids", "").splitlines() if line.strip()]
            preset_data["sutras"] = [{"id": sid, "name": sid} for sid in ids[:6]]

        preset = PresetModel(**preset_data)
        self.presets[preset.id] = preset

        fpath = os.path.join(self.storage_dir, f"{preset.id}.json")
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(preset.model_dump(), f, ensure_ascii=False, indent=2)

        return preset

    def delete_preset(self, preset_id: str) -> bool:
        if preset_id in self.presets:
            del self.presets[preset_id]
        fpath = os.path.join(self.storage_dir, f"{preset_id}.json")
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
                return True
            except OSError:
                return False
        return False
