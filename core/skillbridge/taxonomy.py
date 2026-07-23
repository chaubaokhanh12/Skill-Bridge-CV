"""taxonomy.py — Tầng 3: chuẩn hóa skill về canonical.

Taxonomy.normalize(raw) khớp 3 lớp:
  1. alias      — tra bảng (rẻ, chính xác tuyệt đối)
  2. embedding  — sentence-transformers, cosine ≥ ngưỡng (đồng nghĩa)
  3. unmatched  — (None, 0.0)

Model embedding nạp LƯỜI ở lần normalize() đầu tiên; nếu không nạp được (thiếu torch)
sẽ tự lùi về alias-only kèm cảnh báo, thay vì crash. Nhờ vậy MOCK/offline không cần torch.
"""
import sys
import json
from typing import Optional

from . import config


class Taxonomy:
    """Bảng skill chuẩn: tra cứu metadata + chuẩn hóa chuỗi skill thô."""

    def __init__(self, path: str = None):
        with open(path or config.TAXONOMY_PATH, encoding="utf-8") as f:
            self.skills = json.load(f)

        self.by_id = {s["skill_id"]: s for s in self.skills}
        self.ids = [s["skill_id"] for s in self.skills]
        self.canon = [s["canonical_name"] for s in self.skills]

        # alias (đã lower) -> skill_id, gồm cả canonical_name
        self.alias = {}
        for s in self.skills:
            for a in [s["canonical_name"], *s.get("aliases", [])]:
                self.alias[a.lower().strip()] = s["skill_id"]

        # trạng thái embedding: None = chưa thử, True/False = đã thử
        self._embed_ready: Optional[bool] = None
        self._model = None
        self._emb = None
        self._np = None

    # -- metadata tiện dụng --------------------------------------------------
    def canonical_name(self, sid: str) -> str:
        return self.by_id.get(sid, {}).get("canonical_name", sid)

    def category(self, sid: str) -> str:
        return self.by_id.get(sid, {}).get("category", "")

    def level(self, sid: str) -> str:
        return self.by_id.get(sid, {}).get("level", "intermediate")

    def requires(self, sid: str) -> list:
        return self.by_id.get(sid, {}).get("requires", [])

    # -- embedding (lười) ----------------------------------------------------
    def _ensure_embeddings(self) -> bool:
        if self._embed_ready is not None:
            return self._embed_ready
        try:
            import numpy as np
            from sentence_transformers import SentenceTransformer
            self._np = np
            self._model = SentenceTransformer(config.EMB_MODEL)
            self._emb = self._model.encode(self.canon, normalize_embeddings=True)
            self._embed_ready = True
        except Exception as e:  # noqa: BLE001 - degrade gracefully
            print(f"[taxonomy] Không nạp được embedding ({e!s}); dùng alias-only.", file=sys.stderr)
            self._embed_ready = False
        return self._embed_ready

    # -- chuẩn hóa -----------------------------------------------------------
    def normalize(self, raw: str):
        """Chuỗi skill thô -> (skill_id, confidence). (None, 0.0) nếu unmatched."""
        if not raw or not str(raw).strip():
            return None, 0.0
        key = str(raw).lower().strip()

        # Lớp 1: alias
        if key in self.alias:
            return self.alias[key], 1.0

        # Lớp 2: embedding
        if self._ensure_embeddings():
            v = self._model.encode([str(raw)], normalize_embeddings=True)[0]
            sims = self._emb @ v
            i = int(self._np.argmax(sims))
            score = float(sims[i])
            if score >= config.EMB_THRESHOLD:
                return self.ids[i], score

        # Lớp 3: unmatched
        return None, 0.0


_taxonomy: Taxonomy = None


def get_taxonomy() -> Taxonomy:
    """Taxonomy singleton (nạp JSON một lần)."""
    global _taxonomy
    if _taxonomy is None:
        _taxonomy = Taxonomy()
    return _taxonomy
