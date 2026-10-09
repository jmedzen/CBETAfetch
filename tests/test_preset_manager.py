"""
Unit tests for core.preset_manager module.
"""

import os
import pytest
from core.preset_manager import PresetManager, PresetModel, DEFAULT_BUDDHIST_PRESETS


def test_preset_manager_initial_seeding(temp_dir):
    presets_dir = os.path.join(temp_dir, "presets")
    pm = PresetManager(presets_dir)
    presets = pm.list_presets()

    assert len(presets) == len(DEFAULT_BUDDHIST_PRESETS)
    assert any(p["id"] == "weishi" for p in presets)
    assert any(p["id"] == "prajna" for p in presets)


def test_preset_manager_get(temp_dir):
    presets_dir = os.path.join(temp_dir, "presets")
    pm = PresetManager(presets_dir)

    p = pm.get_preset("weishi")
    assert p is not None
    assert p.title == "唯識根本經論"
    assert "T1585" in p.default_ids


def test_preset_manager_create_and_persist(temp_dir):
    presets_dir = os.path.join(temp_dir, "presets")
    pm = PresetManager(presets_dir)

    new_data = {
        "id": "sanlun",
        "title": "中觀三論部",
        "category": "中觀般若",
        "badge": "龍樹提婆",
        "description": "中論、十二門論、百論",
        "default_ids": "T1564\nT1568\nT1569",
        "is_custom": True
    }

    saved = pm.save_preset(new_data)
    assert saved.id == "sanlun"
    assert saved.title == "中觀三論部"

    # Verify disk persistence with new instance
    pm2 = PresetManager(presets_dir)
    p2 = pm2.get_preset("sanlun")
    assert p2 is not None
    assert p2.title == "中觀三論部"
    assert len(p2.sutras) == 3


def test_preset_manager_update(temp_dir):
    presets_dir = os.path.join(temp_dir, "presets")
    pm = PresetManager(presets_dir)

    update_data = {
        "id": "weishi",
        "title": "唯識宗精選經論 (已更新)",
        "default_ids": "T1585\nT1586"
    }

    pm.save_preset(update_data)
    p = pm.get_preset("weishi")
    assert p.title == "唯識宗精選經論 (已更新)"


def test_preset_manager_delete(temp_dir):
    presets_dir = os.path.join(temp_dir, "presets")
    pm = PresetManager(presets_dir)

    # Create then delete
    pm.save_preset({"id": "to_delete", "title": "臨時預設", "default_ids": "T0001"})
    assert pm.get_preset("to_delete") is not None

    deleted = pm.delete_preset("to_delete")
    assert deleted is True
    assert pm.get_preset("to_delete") is None
    assert not os.path.exists(os.path.join(presets_dir, "to_delete.json"))
