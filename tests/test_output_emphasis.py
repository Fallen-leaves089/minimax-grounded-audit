from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class OutputDensityContractTests(unittest.TestCase):
    def test_skill_emphasizes_primary_findings(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for marker in (
            "**输出密度。**",
            "**P0/P1 完整展开**",
            "**P2 简写**",
            "**P3 默认只列一行**",
            "次要点仅在改变上线、交接或回滚判断时展开",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
