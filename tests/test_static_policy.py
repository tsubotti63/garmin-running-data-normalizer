from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_static_policy_module():
    script = ROOT / "scripts/static_policy_scan.py"
    spec = importlib.util.spec_from_file_location("static_policy_scan_for_test", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("static policy scan could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StaticPolicyTest(unittest.TestCase):
    def _assert_workflow_policy_violation(
        self,
        expected: str,
        *,
        ci_transform=None,
        publish_transform=None,
    ) -> None:
        module = load_static_policy_module()
        ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        publish = (ROOT / ".github/workflows/publish-pypi.yml").read_text(
            encoding="utf-8"
        )
        if ci_transform is not None:
            ci = ci_transform(ci)
        if publish_transform is not None:
            publish = publish_transform(publish)
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            workflows = temporary / ".github/workflows"
            workflows.mkdir(parents=True)
            (workflows / "ci.yml").write_text(ci, encoding="utf-8")
            (workflows / "publish-pypi.yml").write_text(publish, encoding="utf-8")
            module.ROOT = temporary
            self.assertIn(expected, module.workflow_security_violations())

    def test_repository_workflows_satisfy_security_policy(self) -> None:
        module = load_static_policy_module()
        self.assertEqual(module.workflow_security_violations(), [])

    def test_workflow_policy_rejects_input_selected_checkout(self) -> None:
        self._assert_workflow_policy_violation(
            ".github/workflows/publish-pypi.yml: workflow input controls checkout ref",
            publish_transform=lambda text: text.replace(
                "ref: ${{ github.sha }}", "ref: ${{ inputs.source_sha }}"
            ),
        )

    def test_workflow_policy_rejects_missing_ci_permissions(self) -> None:
        self._assert_workflow_policy_violation(
            ".github/workflows/ci.yml: top-level permissions must be exactly contents: read",
            ci_transform=lambda text: text.replace(
                "\npermissions:\n  contents: read\n", ""
            ),
        )

    def test_workflow_policy_rejects_publish_write_all_permissions(self) -> None:
        self._assert_workflow_policy_violation(
            ".github/workflows/publish-pypi.yml: top-level permissions must be exactly contents: read",
            publish_transform=lambda text: text.replace(
                "permissions:\n  contents: read",
                "permissions: write-all",
                1,
            ),
        )

    def test_workflow_policy_rejects_quoted_top_level_permission_override(self) -> None:
        for quoted_key in ('"permissions"', "'permissions'"):
            with self.subTest(quoted_key=quoted_key):
                self._assert_workflow_policy_violation(
                    ".github/workflows/publish-pypi.yml: top-level permissions must be exactly contents: read",
                    publish_transform=lambda text, key=quoted_key: text.replace(
                        "\njobs:\n",
                        f"\n{key}: write-all\n\njobs:\n",
                        1,
                    ),
                )

    def test_workflow_policy_rejects_global_oidc_permissions(self) -> None:
        self._assert_workflow_policy_violation(
            ".github/workflows/publish-pypi.yml: top-level permissions must be exactly contents: read",
            publish_transform=lambda text: text.replace(
                "permissions:\n  contents: read",
                "permissions: {contents: read, id-token: write}",
                1,
            ),
        )

    def test_workflow_policy_rejects_ci_job_permission_override(self) -> None:
        self._assert_workflow_policy_violation(
            ".github/workflows/ci.yml: job-level permissions must not override the read-only workflow default",
            ci_transform=lambda text: text.replace(
                "    runs-on: ubuntu-latest",
                "    runs-on: ubuntu-latest\n    permissions: write-all",
                1,
            ),
        )

    def test_workflow_policy_rejects_quoted_ci_job_permission_override(self) -> None:
        for quoted_key in ('"permissions"', "'permissions'"):
            with self.subTest(quoted_key=quoted_key):
                self._assert_workflow_policy_violation(
                    ".github/workflows/ci.yml: job-level permissions must not override the read-only workflow default",
                    ci_transform=lambda text, key=quoted_key: text.replace(
                        "    runs-on: ubuntu-latest",
                        f"    runs-on: ubuntu-latest\n    {key}: write-all",
                        1,
                    ),
                )

    def test_workflow_policy_rejects_publish_build_permission_override(self) -> None:
        self._assert_workflow_policy_violation(
            ".github/workflows/publish-pypi.yml: OIDC permission must be exclusive to both publish jobs",
            publish_transform=lambda text: text.replace(
                "    runs-on: ubuntu-latest",
                "    runs-on: ubuntu-latest\n    permissions: write-all",
                1,
            ),
        )

    def test_workflow_policy_rejects_quoted_publish_build_permission_override(self) -> None:
        for quoted_key in ('"permissions"', "'permissions'"):
            with self.subTest(quoted_key=quoted_key):
                self._assert_workflow_policy_violation(
                    ".github/workflows/publish-pypi.yml: OIDC permission must be exclusive to both publish jobs",
                    publish_transform=lambda text, key=quoted_key: text.replace(
                        "    runs-on: ubuntu-latest",
                        f"    runs-on: ubuntu-latest\n    {key}: write-all",
                        1,
                    ),
                )

    def test_workflow_policy_rejects_extra_publish_job_permission(self) -> None:
        self._assert_workflow_policy_violation(
            ".github/workflows/publish-pypi.yml: OIDC permission must be exclusive to both publish jobs",
            publish_transform=lambda text: text.replace(
                "    permissions:\n      id-token: write",
                "    permissions:\n      id-token: write\n      contents: write",
                1,
            ),
        )

    def test_workflow_policy_rejects_persisted_checkout_credentials(self) -> None:
        self._assert_workflow_policy_violation(
            ".github/workflows/publish-pypi.yml: checkout must use github.sha without persisted credentials",
            publish_transform=lambda text: text.replace(
                "persist-credentials: false", "persist-credentials: true", 1
            ),
        )

    def test_workflow_policy_rejects_a_second_checkout(self) -> None:
        second_checkout = (
            "      - uses: actions/checkout@"
            "d23441a48e516b6c34aea4fa41551a30e30af803\n"
            "        with:\n"
            "          ref: main\n"
            "          persist-credentials: true\n"
        )
        self._assert_workflow_policy_violation(
            ".github/workflows/publish-pypi.yml: exactly one trusted checkout is required",
            publish_transform=lambda text: text.replace(
                "      - uses: actions/setup-python@",
                second_checkout + "      - uses: actions/setup-python@",
                1,
            ),
        )

    def test_workflow_policy_rejects_execution_before_identity_check(self) -> None:
        self._assert_workflow_policy_violation(
            ".github/workflows/publish-pypi.yml: trusted-source guards must surround checkout and precede repository code execution",
            publish_transform=lambda text: text.replace(
                "      - name: Verify checked-out source identity",
                "      - run: python scripts/validate_bootstrap.py\n"
                "      - name: Verify checked-out source identity",
                1,
            ),
        )

    def test_workflow_policy_rejects_input_derived_source_mutation_after_identity(self) -> None:
        commands = (
            'git fetch origin "${{ inputs.source_sha }}"',
            'git checkout "${{ inputs.source_sha }}"',
            'git switch --detach "${{ inputs.source_sha }}"',
            'git reset --hard "${{ inputs.source_sha }}"',
        )
        for command in commands:
            with self.subTest(command=command):
                injected_step = (
                    "      - name: Mutate trusted source\n"
                    f"        run: {command}\n"
                )
                self._assert_workflow_policy_violation(
                    ".github/workflows/publish-pypi.yml: source_sha may appear only in both trusted identity guards",
                    publish_transform=lambda text, step=injected_step: text.replace(
                        "      - name: Install validation tooling",
                        step + "      - name: Install validation tooling",
                        1,
                    ),
                )

    def test_workflow_policy_rejects_any_later_source_mutation(self) -> None:
        injected_step = (
            "      - name: Mutate trusted source\n"
            '        run: git checkout "$WORKFLOW_SHA"\n'
        )
        self._assert_workflow_policy_violation(
            ".github/workflows/publish-pypi.yml: git usage must be limited to both trusted identity checks",
            publish_transform=lambda text: text.replace(
                "      - name: Install validation tooling",
                injected_step + "      - name: Install validation tooling",
                1,
            ),
        )

    def test_workflow_policy_rejects_git_global_option_and_line_continuation_bypasses(self) -> None:
        continuation = "          git " + chr(92) + "\n          checkout main\n"
        injected_steps = (
            (
                "git -C",
                "      - name: Mutate trusted source\n"
                "        run: git -C . checkout main\n",
            ),
            (
                "git --work-tree",
                "      - name: Mutate trusted source\n"
                "        run: git --work-tree=. reset --hard main\n",
            ),
            (
                "line continuation",
                "      - name: Mutate trusted source\n"
                "        run: |\n"
                + continuation,
            ),
        )
        for variant, injected_step in injected_steps:
            with self.subTest(variant=variant):
                self._assert_workflow_policy_violation(
                    ".github/workflows/publish-pypi.yml: git usage must be limited to both trusted identity checks",
                    publish_transform=lambda text, step=injected_step: text.replace(
                        "      - name: Install validation tooling",
                        step + "      - name: Install validation tooling",
                        1,
                    ),
                )

    def test_workflow_policy_rejects_alternate_source_sha_input_contexts(self) -> None:
        expressions = (
            "${{ github.event.inputs.source_sha }}",
            "${{ inputs['source_sha'] }}",
            "${{  inputs.source_sha  }}",
        )
        for expression in expressions:
            with self.subTest(expression=expression):
                injected_step = (
                    "      - name: Mutate trusted source\n"
                    "        env:\n"
                    f"          SOURCE_REF: {expression}\n"
                    '        run: git -C . checkout "$SOURCE_REF"\n'
                )
                self._assert_workflow_policy_violation(
                    ".github/workflows/publish-pypi.yml: source_sha may appear only in both trusted identity guards",
                    publish_transform=lambda text, step=injected_step: text.replace(
                        "      - name: Install validation tooling",
                        step + "      - name: Install validation tooling",
                        1,
                    ),
                )

    def test_workflow_policy_rejects_missing_job_scoped_oidc(self) -> None:
        self._assert_workflow_policy_violation(
            ".github/workflows/publish-pypi.yml: OIDC permission must be exclusive to both publish jobs",
            publish_transform=lambda text: text.replace(
                "      id-token: write", "      # id-token: write"
            ),
        )

    def test_workflow_policy_rejects_commented_dispatch_guard(self) -> None:
        self._assert_workflow_policy_violation(
            ".github/workflows/publish-pypi.yml: missing pre-checkout guard "
            'test "$WORKFLOW_GIT_REF" = "refs/heads/main"',
            publish_transform=lambda text: text.replace(
                '          test "$WORKFLOW_GIT_REF" = "refs/heads/main"',
                '          # test "$WORKFLOW_GIT_REF" = "refs/heads/main"',
                1,
            ),
        )

    def test_workflow_policy_rejects_commented_identity_guard(self) -> None:
        self._assert_workflow_policy_violation(
            ".github/workflows/publish-pypi.yml: missing post-checkout guard "
            'test "$(git rev-parse HEAD)" = "$WORKFLOW_SHA"',
            publish_transform=lambda text: text.replace(
                '          test "$(git rev-parse HEAD)" = "$WORKFLOW_SHA"',
                '          # test "$(git rev-parse HEAD)" = "$WORKFLOW_SHA"',
                1,
            ),
        )

    def test_workflow_policy_rejects_execution_inside_identity_step(self) -> None:
        self._assert_workflow_policy_violation(
            ".github/workflows/publish-pypi.yml: post-checkout identity step may contain only the ordered trust guards",
            publish_transform=lambda text: text.replace(
                "      - name: Verify checked-out source identity\n"
                "        env:\n"
                "          SOURCE_SHA: ${{ inputs.source_sha }}\n"
                "          WORKFLOW_SHA: ${{ github.sha }}\n"
                "        run: |\n",
                "      - name: Verify checked-out source identity\n"
                "        env:\n"
                "          SOURCE_SHA: ${{ inputs.source_sha }}\n"
                "          WORKFLOW_SHA: ${{ github.sha }}\n"
                "        run: |\n"
                "          python scripts/validate_bootstrap.py\n",
                1,
            ),
        )

    def test_generated_development_metadata_is_excluded(self) -> None:
        module = load_static_policy_module()
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            source = temporary / "src"
            source.mkdir()
            virtual_environment = temporary / ".venv/site-packages/example"
            virtual_environment.mkdir(parents=True)
            (virtual_environment / "metadata.txt").write_text(
                "maintainer" + "@example.invalid\n" + "token" + " = 'dependency-owned-value'\n",
                encoding="utf-8",
            )
            egg_info = source / "example.egg-info"
            egg_info.mkdir()
            (egg_info / "PKG-INFO").write_text(
                "Metadata-Version: 2.4\nDescription: wellness\n",
                encoding="utf-8",
            )
            (temporary / "README.md").write_text("Synthetic project content.\n", encoding="utf-8")

            module.ROOT = temporary
            module.SOURCE = source
            self.assertEqual(module.production_imports(), [])
            self.assertEqual(module.content_violations(), [])

    def test_product_source_remains_scanned(self) -> None:
        module = load_static_policy_module()
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            source = temporary / "src"
            source.mkdir()
            production = source / "production.py"
            production.write_text(
                "import phase" + "1_private\nfeature = 'wellness'\n",
                encoding="utf-8",
            )

            module.ROOT = temporary
            module.SOURCE = source
            self.assertEqual(
                module.production_imports(),
                ["src/production.py: banned import phase1_private"],
            )
            self.assertEqual(
                module.content_violations(),
                ["src/production.py: non-Garmin production term"],
            )

    def test_exact_garmin_wellness_source_name_is_allowed(self) -> None:
        module = load_static_policy_module()
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            source = temporary / "src"
            source.mkdir()
            (source / "production.py").write_text(
                "source_family = 'DI-Connect-Wellness'\n",
                encoding="utf-8",
            )

            module.ROOT = temporary
            module.SOURCE = source
            self.assertEqual(module.content_violations(), [])


if __name__ == "__main__":
    unittest.main()
