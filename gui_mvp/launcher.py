"""Small desktop launcher for local MVP viewers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk


REPO_ROOT = Path(__file__).resolve().parents[1]
CHART_OUTPUTS_DIR = REPO_ROOT / "chart_mvp" / "outputs"


@dataclass(frozen=True)
class ViewerLaunchSpec:
    """A launchable GUI target."""

    key: str
    label: str
    command: tuple[str, ...]


def build_viewer_command(target: str, *, python_executable: str | None = None) -> tuple[str, ...]:
    """Return the command used by the launcher and desktop shortcut."""

    executable = python_executable or sys.executable
    return (executable, "-m", "gui_mvp", target)


def build_launch_specs(*, python_executable: str | None = None) -> tuple[ViewerLaunchSpec, ...]:
    """Return stable launch specs for the two user-facing viewers."""

    return (
        ViewerLaunchSpec(
            key="chart",
            label="차트 Top-N 결과",
            command=build_viewer_command("chart", python_executable=python_executable),
        ),
        ViewerLaunchSpec(
            key="backtest",
            label="백테스트 평가 결과",
            command=build_viewer_command("backtest", python_executable=python_executable),
        ),
    )


def latest_chart_status() -> str:
    """Return a compact status line for already generated chart outputs."""

    meta_path = CHART_OUTPUTS_DIR / "last_run_meta.json"
    top_csv = CHART_OUTPUTS_DIR / "latest_top.csv"
    top_json = CHART_OUTPUTS_DIR / "latest_top.json"
    if not meta_path.exists() and not top_csv.exists() and not top_json.exists():
        return "차트 결과: 저장된 Top-N 결과 없음"

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    except Exception:
        meta = {}

    as_of = meta.get("as_of") or "확인 필요"
    processed = meta.get("processed_count", "?")
    failed = meta.get("failed_count", "?")
    return f"차트 결과: {as_of}, 처리 {processed}, 실패 {failed}"


class GuiMvpLauncher(tk.Tk):
    """One-window launcher for the local chart and backtest viewers."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Master MVP GUI")
        self.geometry("560x260")
        self.minsize(520, 240)
        self.status_var = tk.StringVar(value=latest_chart_status())
        self._build_layout()

    def _build_layout(self) -> None:
        container = ttk.Frame(self, padding=16)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)

        ttk.Label(container, text="Master MVP", font=("", 18, "bold")).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 12),
        )

        for column, spec in enumerate(build_launch_specs()):
            button = ttk.Button(
                container,
                text=spec.label,
                command=lambda selected=spec: self._launch(selected),
            )
            button.grid(row=1, column=column, sticky="ew", padx=(0 if column == 0 else 8, 0), ipady=16)

        ttk.Label(container, textvariable=self.status_var).grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(18, 0),
        )
        ttk.Button(container, text="상태 새로고침", command=self._refresh_status).grid(
            row=3,
            column=0,
            sticky="w",
            pady=(14, 0),
        )

    def _launch(self, spec: ViewerLaunchSpec) -> None:
        try:
            subprocess.Popen(spec.command, cwd=REPO_ROOT)
            self.status_var.set(f"{spec.label} 창을 열었습니다.")
        except Exception as exc:
            self.status_var.set("실행 실패")
            messagebox.showerror("실행 실패", str(exc))

    def _refresh_status(self) -> None:
        self.status_var.set(latest_chart_status())


def main() -> int:
    app = GuiMvpLauncher()
    app.mainloop()
    return 0


__all__ = (
    "GuiMvpLauncher",
    "ViewerLaunchSpec",
    "build_launch_specs",
    "build_viewer_command",
    "latest_chart_status",
    "main",
)


if __name__ == "__main__":
    raise SystemExit(main())
