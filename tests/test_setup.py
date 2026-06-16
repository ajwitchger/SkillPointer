import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import setup


class SkillPointerTests(unittest.TestCase):
    def setUp(self):
        self.original_config = dict(setup.CONFIG)

    def tearDown(self):
        setup.CONFIG.clear()
        setup.CONFIG.update(self.original_config)

    def configure_agent(self, active_dir: Path, vault_dir: Path, agent_key: str = "cursor"):
        setup.CONFIG.clear()
        setup.CONFIG.update(
            {
                "agent_key": agent_key,
                "agent_name": setup.AGENT_PROFILES[agent_key]["label"],
                "active_skills_dir": active_dir,
                "hidden_library_dir": vault_dir,
                "template_key": setup.AGENT_PROFILES[agent_key]["template_key"],
                "bootstrap_skills_dir": True,
            }
        )

    def create_skill(self, category_dir: Path, skill_name: str):
        skill_dir = category_dir / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(f"# {skill_name}\n", encoding="utf-8")
        return skill_dir

    def test_parse_install_agent_after_subcommand(self):
        _, args = setup.parse_cli_args(["install", "--agent", "cursor"])
        self.assertEqual(args.command, "install")
        self.assertEqual(args.agent, "cursor")

    def test_parse_install_agent_before_subcommand(self):
        _, args = setup.parse_cli_args(["--agent", "cursor", "install"])
        self.assertEqual(args.command, "install")
        self.assertEqual(args.agent, "cursor")

    def test_parse_migrate_no_refresh(self):
        _, args = setup.parse_cli_args(
            ["migrate", "--agent", "cursor", "--no-refresh-pointers"]
        )
        self.assertEqual(args.command, "migrate")
        self.assertEqual(args.agent, "cursor")
        self.assertTrue(args.no_refresh_pointers)

    def test_parse_conflicting_duplicate_agents_fails(self):
        with self.assertRaises(SystemExit) as exc:
            setup.parse_cli_args(["--agent", "cursor", "install", "--agent", "claude"])
        self.assertEqual(exc.exception.code, 2)

    def test_non_interactive_without_agent_exits_one(self):
        with mock.patch("sys.stdin.isatty", return_value=False):
            with self.assertRaises(SystemExit) as exc:
                setup.main([])
        self.assertEqual(exc.exception.code, 1)

    def test_managed_pointer_updated_and_stale_managed_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            active_dir = root / "active"
            vault_dir = root / "vault"
            active_dir.mkdir()
            vault_dir.mkdir()
            self.configure_agent(active_dir, vault_dir)

            self.create_skill(vault_dir / "security", "auth-skill")
            managed_pointer = active_dir / "security-category-pointer"
            managed_pointer.mkdir()
            (managed_pointer / "SKILL.md").write_text("old", encoding="utf-8")
            setup.write_pointer_metadata(managed_pointer, "security")

            stale_pointer = active_dir / "old-category-pointer"
            stale_pointer.mkdir()
            (stale_pointer / "SKILL.md").write_text("old", encoding="utf-8")
            setup.write_pointer_metadata(stale_pointer, "old")

            setup.generate_pointers()

            self.assertTrue((managed_pointer / "SKILL.md").read_text(encoding="utf-8"))
            self.assertTrue(
                (managed_pointer / setup.POINTER_METADATA_FILENAME).is_file()
            )
            self.assertFalse(stale_pointer.exists())

    def test_legacy_pointer_is_adopted_and_marked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            active_dir = root / "active"
            vault_dir = root / "vault"
            active_dir.mkdir()
            vault_dir.mkdir()
            self.configure_agent(active_dir, vault_dir)

            self.create_skill(vault_dir / "security", "auth-skill")
            legacy_pointer = active_dir / "security-category-pointer"
            legacy_pointer.mkdir()
            (legacy_pointer / "SKILL.md").write_text(
                setup.get_pointer_content("security", 1), encoding="utf-8"
            )

            setup.generate_pointers()

            metadata = json.loads(
                (legacy_pointer / setup.POINTER_METADATA_FILENAME).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(metadata["managed_by"], setup.POINTER_MANAGER_NAME)
            self.assertEqual(metadata["category"], "security")
            self.assertEqual(metadata["agent"], "cursor")

    def test_unmanaged_pointer_is_neither_overwritten_nor_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            active_dir = root / "active"
            vault_dir = root / "vault"
            active_dir.mkdir()
            vault_dir.mkdir()
            self.configure_agent(active_dir, vault_dir)

            unmanaged_pointer = active_dir / "security-category-pointer"
            unmanaged_pointer.mkdir()
            original_content = "third-party pointer\n"
            (unmanaged_pointer / "SKILL.md").write_text(
                original_content, encoding="utf-8"
            )

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                setup.generate_pointers()

            self.assertEqual(
                (unmanaged_pointer / "SKILL.md").read_text(encoding="utf-8"),
                original_content,
            )
            self.assertFalse(
                (unmanaged_pointer / setup.POINTER_METADATA_FILENAME).exists()
            )
            self.assertIn("Left security-category-pointer in place", output.getvalue())

    def test_unmanaged_collision_warns_and_skips_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            active_dir = root / "active"
            vault_dir = root / "vault"
            active_dir.mkdir()
            vault_dir.mkdir()
            self.configure_agent(active_dir, vault_dir)

            self.create_skill(vault_dir / "security", "auth-skill")
            unmanaged_pointer = active_dir / "security-category-pointer"
            unmanaged_pointer.mkdir()
            (unmanaged_pointer / "SKILL.md").write_text("custom", encoding="utf-8")

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                setup.generate_pointers()

            self.assertEqual(
                (unmanaged_pointer / "SKILL.md").read_text(encoding="utf-8"),
                "custom",
            )
            self.assertFalse(
                (unmanaged_pointer / setup.POINTER_METADATA_FILENAME).exists()
            )
            self.assertIn("Skipped security-category-pointer", output.getvalue())

    def test_install_bat_supports_optional_agent_and_interactive_flow(self):
        content = Path("Install.bat").read_text(encoding="utf-8")
        self.assertIn('if /I "%~1"=="cursor"', content)
        self.assertIn("python setup.py install --agent %~1", content)
        self.assertIn("python setup.py install", content)

    def test_install_vbs_shows_success_only_on_zero_exit(self):
        content = Path("Install.vbs").read_text(encoding="utf-8")
        self.assertIn("WshShell.Run", content)
        self.assertIn("If exitCode = 0 Then", content)
        self.assertIn('MsgBox "SkillPointer installed successfully!"', content)


if __name__ == "__main__":
    unittest.main()
