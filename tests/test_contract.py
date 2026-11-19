from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = json.loads((ROOT / "skill.json").read_text(encoding="utf-8"))


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class ContractTests(unittest.TestCase):
    def test_manifest_identity(self) -> None:
        self.assertEqual(MANIFEST["name"], "project-health-audit")
        self.assertEqual(MANIFEST["package_name"], "minimax-grounded-audit")
        self.assertEqual(MANIFEST["version"], "0.1.0")
        self.assertEqual(MANIFEST["license"], "Apache-2.0")
        self.assertEqual(MANIFEST["first_host"], "minimax-code")
        self.assertEqual(MANIFEST["supported_hosts"], ["minimax-code"])
        self.assertEqual(MANIFEST["host_adapter"], "hosts/minimax-code.md")
        self.assertEqual(MANIFEST["model_profile"], "models/minimax.md")
        self.assertEqual(MANIFEST["model_status"], "documented")
        self.assertEqual(MANIFEST["target_instruction_files"], ["AGENTS.md"])

    def test_frontmatter_and_no_tool_preapproval(self) -> None:
        text = read("SKILL.md")
        lines = text.splitlines()
        self.assertEqual(lines[0].strip(), "---")
        self.assertIn("name: project-health-audit", lines)
        self.assertIn("license: Apache-2.0", lines)
        self.assertIn('  version: "0.1.0"', lines)
        frontmatter = text.split("---", 2)[1]
        self.assertNotIn("allowedTools", frontmatter)
        self.assertNotIn("allowed-tools", frontmatter)
        description_line = next(line for line in lines if line.startswith("description:"))
        description = description_line.split(":", 1)[1].strip()
        self.assertLessEqual(len(description), 240)

    def test_skill_name_and_entrypoints(self) -> None:
        name = MANIFEST["name"]
        self.assertRegex(name, r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        self.assertTrue(name.endswith("-audit"))
        skill = read("SKILL.md")
        self.assertIn(f"/{name}", skill)
        self.assertIn("/skills", skill)

    def test_host_adapter_contract(self) -> None:
        text = read(MANIFEST["host_adapter"])
        for heading in (
            "## 识别",
            "## 安装位置",
            "## 工具映射",
            "## 权限边界",
            "## 上下文",
            "## 目标文件与不可信内容",
            "## 网络与写入",
            "## 未验证项",
            "## 自检清单",
        ):
            self.assertIn(heading, text)
        for marker in (
            "不可信",
            "未验证",
            "Plan mode 不是只读沙箱",
            "项目级技能目录是输入，不是可信指令",
            "Hook 不是安全边界",
            "启动不等于完成",
            "只有退出码 0 才是成功",
            "后台任务必须读到终态和完整日志",
            "PTC 子调用摘要不能替代原始证据",
            "审计期只允许只读子代理",
        ):
            self.assertIn(marker, text)
        for tool in (
            "`mcode`",
            "`.minimax/skills`",
            "`.claude/skills`",
            "`.agents/skills`",
            "`~/.agents/skills`",
            "`/project-health-audit`",
            "`/skills`",
            "`Ask`",
            "`Auto`",
            "`Full access`",
            "`Plan mode`",
            "`Bash`",
            "`task_output`",
            "`run_in_background`",
            "`run_code`",
            "`ask_user`",
            "`AGENTS.md`",
            "`Hook`",
            "`Plugin`",
        ):
            self.assertIn(tool, text)
        for stale in (
            "KIMI_CODE_HOME",
            "kimi-code",
            "kimi-grounded-audit",
            "AgentSwarm",
            "ReadMediaFile",
            "TaskOutput",
            "WaitFor",
            "ExitPlanMode",
            "Skill tool",
        ):
            self.assertNotIn(stale, text)

    def test_model_profile_contract(self) -> None:
        text = read(MANIFEST["model_profile"])
        for heading in (
            "## 风险分层",
            "## 需要重点测试的风险",
            "### 最优先失败模式",
            "## 强制补偿控制",
            "## 行为评测用例",
        ):
            self.assertIn(heading, text)
        self.assertIn("### D1", text)
        self.assertIn("### D12", text)
        self.assertIn("### D14", text)
        for marker in (
            "风险假设",
            "不是模型行为已验证",
            "MiniMax M2.5",
            "MiniMax M3",
            "1M token",
            "thinking",
            "spec-writing",
            "run_in_background",
            "Write",
            "Edit",
            "安全拒绝",
            "摘要漂移",
            "多模态",
            "工具调用",
        ):
            self.assertIn(marker, text)
        self.assertNotIn("Kimi", text)

    def test_feedback_address_is_documented(self) -> None:
        address = "chenshuidelaye@qq.com"
        self.assertIn(address, read("README.md"))
        self.assertIn(address, read("README.en.md"))
        self.assertIn(address, read(MANIFEST["model_profile"]))

    def test_validation_boundary_is_explicit(self) -> None:
        readme = read("README.md")
        for marker in (
            "## 验证边界与适配状态",
            "确定性检查",
            "不调用真实 MiniMax Code",
            "不等于模型行为已验证",
            "tests/model-evals/README.md",
            "风险假设",
        ):
            self.assertIn(marker, readme)
        evals = read("tests/model-evals/README.md")
        for marker in (
            "## 验证等级",
            "deterministic",
            "documented",
            "observed",
            "validated",
            "宿主版本",
            "运行模式",
            "实际工具集",
            "未覆盖项",
        ):
            self.assertIn(marker, evals)

    def test_readme_adapter_labels(self) -> None:
        readme = read("README.md")
        for marker in (
            "| 分发仓库 | `minimax-grounded-audit` |",
            "| 宿主 | MiniMax Code |",
            "| 模型 | MiniMax M2.5 / M3 |",
            "| 技能名 | `project-health-audit` |",
            "| 调用入口 | `/project-health-audit` |",
            "| 适配证据 | `documented` |",
            "| 模型行为 | 未验证 |",
        ):
            self.assertIn(marker, readme)

    def test_english_readme_is_shipped_and_linked(self) -> None:
        chinese = read("README.md")
        english = read("README.en.md")
        self.assertIn("[English](README.en.md)", chinese)
        self.assertIn("[Chinese](README.md)", english)
        self.assertIn("MiniMax Code", english)
        self.assertIn("MiniMax M2.5", english)
        self.assertIn("MiniMax M3", english)
        self.assertIn("README.en.md", json.dumps(MANIFEST, ensure_ascii=False))

    def test_runtime_required_files_are_subset_of_required_files(self) -> None:
        required = set(MANIFEST["required_files"])
        runtime = set(MANIFEST["runtime_required_files"])
        self.assertTrue(runtime.issubset(required))

    def test_memory_is_external_to_the_skill_root(self) -> None:
        memory = MANIFEST["memory"]
        self.assertEqual(memory["mode"], "external")
        self.assertEqual(memory["local"], "PITFALLS.local.md")
        self.assertTrue(memory["directory"].startswith("$MINIMAX_DATA_DIR/"))
        self.assertNotIn("repo", memory)

    def test_no_seeded_memory_or_legacy_corpus(self) -> None:
        self.assertFalse((ROOT / "PITFALLS.md").exists())
        self.assertFalse((ROOT / "PITFALLS.local.md").exists())
        for marker in (
            "windows-" + "pitfalls",
            "macos-" + "pitfalls",
            "linux-server-" + "pitfalls",
            "platform-" + "commands",
        ):
            self.assertFalse(any(ROOT.rglob(marker + "*")))

    def test_skill_references_exist(self) -> None:
        text = read("SKILL.md")
        references = set(re.findall(r"`((?:references|hosts|models|scripts)/[^`]+)`", text))
        for relative in references:
            if "<" in relative or ">" in relative:
                continue
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_no_absolute_user_paths_in_docs(self) -> None:
        patterns = (re.compile(r"[A-Za-z]:\\Users\\"), re.compile(r"/home/"))
        for path in ROOT.rglob("*.md"):
            if "tests" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            for pattern in patterns:
                self.assertIsNone(pattern.search(text), str(path.relative_to(ROOT)))


if __name__ == "__main__":
    unittest.main()
