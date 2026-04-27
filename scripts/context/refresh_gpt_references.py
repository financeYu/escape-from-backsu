from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import build_context_packet
import refresh_quant_project_context


@dataclass(frozen=True)
class RefreshGptReferencesConfig:
    project_root: Path
    request: str
    context_config_path: Path = refresh_quant_project_context.DEFAULT_CONFIG_PATH
    brief_output_path: Path = build_context_packet.DEFAULT_GPT_BRIEF_OUTPUT


@dataclass(frozen=True)
class RefreshGptReferencesResult:
    project_reference_path: Path
    gpt_brief_path: Path
    removed_local_paths: tuple[Path, ...]
    project_reference_char_count: int
    gpt_brief_char_count: int
    gpt_brief_missing_references: tuple[str, ...]


def refresh_gpt_references(config: RefreshGptReferencesConfig) -> RefreshGptReferencesResult:
    request = config.request.strip()
    if not request:
        raise ValueError("GPT reference refresh requires --request with the active GPT task.")

    project_root = config.project_root.resolve()
    context_config = refresh_quant_project_context.load_config(project_root, config.context_config_path)
    project_result = refresh_quant_project_context.refresh_context(context_config)
    brief_result = build_context_packet.write_gpt_brief(
        build_context_packet.GptBriefConfig(
            project_root=project_root,
            request=request,
            output_path=config.brief_output_path,
        )
    )

    return RefreshGptReferencesResult(
        project_reference_path=project_result.output_path,
        gpt_brief_path=brief_result.output_path,
        removed_local_paths=project_result.removed_local_paths,
        project_reference_char_count=project_result.char_count,
        gpt_brief_char_count=brief_result.char_count,
        gpt_brief_missing_references=brief_result.missing_references,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Refresh both GPT-facing context files after an explicit user request."
    )
    parser.add_argument("--project-root", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument(
        "--config",
        default=str(refresh_quant_project_context.DEFAULT_CONFIG_PATH),
        help="Root-relative project reference config path.",
    )
    parser.add_argument(
        "--brief-output",
        default=str(build_context_packet.DEFAULT_GPT_BRIEF_OUTPUT),
        help="Root-relative GPT brief output path.",
    )
    parser.add_argument("--request", help="Current GPT task text.")
    parser.add_argument(
        "--user-requested",
        action="store_true",
        help="Required confirmation that the user explicitly requested a GPT context refresh.",
    )
    args = parser.parse_args(argv)

    if not args.user_requested:
        print(
            "Refusing to refresh GPT references without --user-requested. "
            "Run only after the user explicitly asks for this GPT context update.",
            file=sys.stderr,
        )
        return 2
    if not args.request or not args.request.strip():
        print(
            "Refusing to refresh GPT references without --request. "
            "Use --request to record the active GPT task.",
            file=sys.stderr,
        )
        return 2

    result = refresh_gpt_references(
        RefreshGptReferencesConfig(
            project_root=Path(args.project_root),
            request=args.request,
            context_config_path=Path(args.config),
            brief_output_path=Path(args.brief_output),
        )
    )
    print(
        json.dumps(
            {
                "project_reference_path": str(result.project_reference_path),
                "gpt_brief_path": str(result.gpt_brief_path),
                "removed_local_paths": [str(path) for path in result.removed_local_paths],
                "project_reference_char_count": result.project_reference_char_count,
                "gpt_brief_char_count": result.gpt_brief_char_count,
                "gpt_brief_missing_references": list(result.gpt_brief_missing_references),
                "mode": "local_only_no_paid_upload",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
