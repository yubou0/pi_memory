"""持久層：把記憶存成 JSON 檔，重啟後讀得回來，並用 id 去重。
load()/_persist()/add() 要你填。"""
from __future__ import annotations
import json
import os


class JsonStore:
    def __init__(self, path: str):
        self.path = path
        self.items: list[dict] = []
        self.load()

    def load(self) -> None:
        """從硬碟讀回 self.items。
        檔案不存在、解析失敗、或內容不是 list 都視為空 list。
        """
        if not os.path.exists(self.path):
            self.items = []
            return

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                self.items = data
            else:
                self.items = []
        except (json.JSONDecodeError, OSError):
            self.items = []

    def _persist(self) -> None:
        """把 self.items 寫回硬碟。"""
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.items, f, ensure_ascii=False, indent=2)

    def add(self, obs: dict) -> bool:
        """新增一筆記憶；若 id 已存在則跳過。"""
        obs_id = obs.get("id")

        if any(item.get("id") == obs_id for item in self.items):
            return False

        self.items.append(obs)
        self._persist()
        return True

    def all(self) -> list[dict]:
        return list(self.items)

    def clear(self) -> None:
        self.items = []
        self._persist()