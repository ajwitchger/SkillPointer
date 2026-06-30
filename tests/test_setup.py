import contextlib
import io
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest import mock

import setup


class SkillPointerTests(unittest.TestCase):
    def setUp(self):
        self.original_config = dict(setup.CONFIG)
        self.original_agent_profiles = deepcopy(setup.AGENT_PROFILES)

    def tearDown(self):
        setup.CONFIG.clear()
        setup.CONFIG.update(self.original_config)
        setup.AGENT_PROFILES.clear()
        setup.AGENT_PROFILES.update(deepcopy(self.original_agent_profiles))

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

    def override_agent_profile(
        self, active_dir: Path, vault_dir: Path, agent_key: str = "codex"
    ):
        profile = dict(setup.AGENT_PROFILES[agent_key])
        profile["active_skills_dir"] = active_dir
        profile["hidden_library_dir"] = vault_dir
        setup.AGENT_PROFILES[agent_key] = profile

    def capture_call(self, func, *args, **kwargs):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = func(*args, **kwargs)
        return result, stdout.getvalue(), stderr.getvalue()

    def capture_system_exit(self, func, *args, **kwargs):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with self.assertRaises(SystemExit) as exc:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                func(*args, **kwargs)
        return exc.exception.code, stdout.getvalue(), stderr.getvalue()

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

    def test_parse_install_agent_codex(self):
        _, args = setup.parse_cli_args(["install", "--agent", "codex"])
        self.assertEqual(args.command, "install")
        self.assertEqual(args.agent, "codex")

    def test_parse_migrate_no_refresh(self):
        _, args = setup.parse_cli_args(
            ["migrate", "--agent", "cursor", "--no-refresh-pointers"]
        )
        self.assertEqual(args.command, "migrate")
        self.assertEqual(args.agent, "cursor")
        self.assertTrue(args.no_refresh_pointers)

    def test_parse_conflicting_duplicate_agents_fails(self):
        code, _, _ = self.capture_system_exit(
            setup.parse_cli_args,
            ["--agent", "cursor", "install", "--agent", "claude"],
        )
        self.assertEqual(code, 2)

    def test_non_interactive_without_agent_exits_one(self):
        with mock.patch("sys.stdin.isatty", return_value=False):
            code, _, _ = self.capture_system_exit(setup.main, [])
        self.assertEqual(code, 1)

    def test_codex_profile_paths(self):
        profile = setup.AGENT_PROFILES["codex"]
        self.assertEqual(profile["label"], "Codex")
        self.assertEqual(profile["active_skills_dir"], Path.home() / ".agents" / "skills")
        self.assertEqual(profile["hidden_library_dir"], Path.home() / ".codex-skill-libraries")
        self.assertEqual(profile["template_key"], "codex")
        self.assertTrue(profile["bootstrap_skills_dir"])

    def test_codex_pointer_template_mentions_vault_and_not_cursor_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            active_dir = root / "active"
            vault_dir = root / "vault"
            active_dir.mkdir()
            vault_dir.mkdir()
            self.configure_agent(active_dir, vault_dir, agent_key="codex")

            content = setup.get_pointer_content("security", 1)

            self.assertIn("outside Codex's active skill directory", content)
            self.assertIn("Inspect this local vault path", content)
            self.assertIn("Find candidate `SKILL.md` files", content)
            self.assertNotIn("`Glob`", content)
            self.assertNotIn("`Read`", content)
            self.assertNotIn("`Grep`", content)

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

            _, _, _ = self.capture_call(setup.generate_pointers)

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

            _, _, _ = self.capture_call(setup.generate_pointers)

            metadata = json.loads(
                (legacy_pointer / setup.POINTER_METADATA_FILENAME).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(metadata["managed_by"], setup.POINTER_MANAGER_NAME)
            self.assertEqual(metadata["category"], "security")
            self.assertEqual(metadata["agent"], "cursor")

    def test_legacy_codex_pointer_is_adopted_and_marked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            active_dir = root / "active"
            vault_dir = root / "vault"
            active_dir.mkdir()
            vault_dir.mkdir()
            self.configure_agent(active_dir, vault_dir, agent_key="codex")

            self.create_skill(vault_dir / "security", "auth-skill")
            legacy_pointer = active_dir / "security-category-pointer"
            legacy_pointer.mkdir()
            (legacy_pointer / "SKILL.md").write_text(
                setup.get_pointer_content("security", 1), encoding="utf-8"
            )

            _, _, _ = self.capture_call(setup.generate_pointers)

            metadata = json.loads(
                (legacy_pointer / setup.POINTER_METADATA_FILENAME).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(metadata["managed_by"], setup.POINTER_MANAGER_NAME)
            self.assertEqual(metadata["category"], "security")
            self.assertEqual(metadata["agent"], "codex")

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

    def test_codex_help_exits_zero_without_bootstrapping_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            active_dir = root / "active"
            vault_dir = root / "vault"
            self.override_agent_profile(active_dir, vault_dir)

            code, stdout, stderr = self.capture_system_exit(
                setup.main, ["--agent", "codex", "--help"]
            )

            self.assertEqual(code, 0)
            self.assertIn("usage:", stdout)
            self.assertEqual(stderr, "")
            self.assertFalse(active_dir.exists())
            self.assertFalse(vault_dir.exists())

    def test_codex_setup_directories_bootstraps_missing_active_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            active_dir = root / "active"
            vault_dir = root / "vault"
            self.configure_agent(active_dir, vault_dir, agent_key="codex")

            result, stdout, stderr = self.capture_call(setup.setup_directories)

            self.assertTrue(result)
            self.assertEqual(stderr, "")
            self.assertTrue(active_dir.is_dir())
            self.assertTrue(vault_dir.is_dir())
            self.assertIn("Created skills directory", stdout)

    def test_codex_refresh_pointers_creates_pointer_from_temp_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            active_dir = root / "active"
            vault_dir = root / "vault"
            self.override_agent_profile(active_dir, vault_dir)
            self.create_skill(vault_dir / "security", "auth-skill")

            result, stdout, stderr = self.capture_call(
                setup.main, ["refresh-pointers", "--agent", "codex"]
            )

            pointer_dir = active_dir / "security-category-pointer"
            metadata = json.loads(
                (pointer_dir / setup.POINTER_METADATA_FILENAME).read_text(
                    encoding="utf-8"
                )
            )

            self.assertIsNone(result)
            self.assertEqual(stderr, "")
            self.assertTrue((pointer_dir / "SKILL.md").is_file())
            self.assertEqual(metadata["agent"], "codex")
            self.assertEqual(metadata["category"], "security")
            self.assertIn("Created skills directory", stdout)
            self.assertIn("Created security-category-pointer", stdout)

    def test_codex_install_migrates_skill_and_leaves_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            active_dir = root / "active"
            vault_dir = root / "vault"
            self.override_agent_profile(active_dir, vault_dir)
            active_dir.mkdir()
            skill_dir = self.create_skill(active_dir, "auth-skill")

            with mock.patch("setup_core.time.sleep", return_value=None):
                result, stdout, stderr = self.capture_call(
                    setup.main, ["install", "--agent", "codex"]
                )

            pointer_dir = active_dir / "security-category-pointer"
            migrated_skill = vault_dir / "security" / "auth-skill" / "SKILL.md"
            metadata = json.loads(
                (pointer_dir / setup.POINTER_METADATA_FILENAME).read_text(
                    encoding="utf-8"
                )
            )

            self.assertIsNone(result)
            self.assertEqual(stderr, "")
            self.assertFalse(skill_dir.exists())
            self.assertTrue(migrated_skill.is_file())
            self.assertTrue((pointer_dir / "SKILL.md").is_file())
            self.assertEqual(metadata["agent"], "codex")
            self.assertIn("Successfully migrated 1 raw skills", stdout)
            self.assertIn("Created security-category-pointer", stdout)

    def test_install_bat_supports_optional_agent_and_interactive_flow(self):
        content = Path("Install.bat").read_text(encoding="utf-8")
        self.assertIn('if /I "%~1"=="cursor"', content)
        self.assertIn('if /I "%~1"=="codex"', content)
        self.assertIn("python setup.py install --agent %~1", content)
        self.assertIn("python setup.py install", content)

    def test_install_vbs_shows_success_only_on_zero_exit(self):
        content = Path("Install.vbs").read_text(encoding="utf-8")
        self.assertIn("WshShell.Run", content)
        self.assertIn("If exitCode = 0 Then", content)
        self.assertIn('MsgBox "SkillPointer installed successfully!"', content)


if __name__ == "__main__":
    unittest.main()
