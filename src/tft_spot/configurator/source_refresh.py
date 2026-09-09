from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from tft_spot.configurator.repository import (
    ConfigurationRepository,
    ConfiguratorDataError,
)

Runner = Callable[..., subprocess.CompletedProcess[str]]


class SourceRefreshError(RuntimeError):
    pass


@dataclass(frozen=True)
class SourceRefreshResult:
    set_number: int
    composition_count: int
    added_source_ids: tuple[str, ...]
    removed_source_ids: tuple[str, ...]
    reconciled_source_ids: tuple[str, ...]
    removed_configuration_source_ids: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "setNumber": self.set_number,
            "compositionCount": self.composition_count,
            "addedSourceIds": list(self.added_source_ids),
            "removedSourceIds": list(self.removed_source_ids),
            "reconciledSourceIds": list(self.reconciled_source_ids),
            "removedConfigurationSourceIds": list(
                self.removed_configuration_source_ids
            ),
        }


def refresh_tft_academy(
    root: Path,
    repository: ConfigurationRepository,
    *,
    runner: Runner = subprocess.run,
) -> SourceRefreshResult:
    """Download, validate, reconcile, and atomically install one source snapshot."""
    root = root.resolve()
    try:
        set_number = repository.snapshot_set_number()
        previous_source_ids = _source_ids(repository)
    except ConfiguratorDataError as error:
        raise SourceRefreshError(
            f"Could not read the active TFT Academy snapshot: {error}"
        ) from error

    try:
        with tempfile.TemporaryDirectory(
            prefix=".tft-spot-refresh-",
            dir=root,
        ) as temporary:
            staging_root = Path(temporary)
            staged_data = staging_root / "data"
            command = [
                sys.executable,
                str(root / "scripts" / "download_tft_academy.py"),
                "--set",
                str(set_number),
                "--data-dir",
                str(staged_data),
            ]
            try:
                completed = runner(
                    command,
                    cwd=root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except OSError as error:
                raise SourceRefreshError(
                    f"Could not start TFT Academy downloader: {error}"
                ) from error
            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout).strip()
                if len(detail) > 2000:
                    detail = detail[-2000:]
                raise SourceRefreshError(
                    "TFT Academy download failed" + (f": {detail}" if detail else "")
                )

            staged_repository = ConfigurationRepository(staging_root)
            refreshed_set_number = staged_repository.snapshot_set_number()
            if refreshed_set_number != set_number:
                raise SourceRefreshError(
                    "Downloaded snapshot set does not match the active snapshot"
                )
            refreshed_source_ids = _source_ids(staged_repository)

            snapshot = staged_repository.load_snapshot()

            # Validate all raw guide references before touching live data.
            for source_id in refreshed_source_ids:
                staged_repository.get_workspace(source_id, snapshot=snapshot)

            live_curated = root / "data" / "curated"
            staged_curated = staged_data / "curated"
            if live_curated.exists():
                shutil.copytree(live_curated, staged_curated)

            staged_repository = ConfigurationRepository(staging_root)
            previous_set = set(previous_source_ids)
            refreshed_set = set(refreshed_source_ids)
            added_source_ids = tuple(
                source_id
                for source_id in refreshed_source_ids
                if source_id not in previous_set
            )
            removed_source_ids = tuple(
                source_id
                for source_id in previous_source_ids
                if source_id not in refreshed_set
            )
            deleted_configurations = staged_repository.delete_configurations(
                set_number=set_number,
                source_ids=set(removed_source_ids),
            )
            reconciled = staged_repository.reconcile_configurations(
                ready_source_ids=set(added_source_ids),
                snapshot=snapshot,
            )

            _install_directories(
                staging_root,
                (
                    (
                        "raw",
                        staged_data / "raw" / "tft_academy",
                        root / "data" / "raw" / "tft_academy",
                    ),
                    (
                        "assets",
                        staged_data / "assets",
                        root / "data" / "assets",
                    ),
                    (
                        "curated",
                        staged_data / "curated" / f"set-{set_number}" / "compositions",
                        root
                        / "data"
                        / "curated"
                        / f"set-{set_number}"
                        / "compositions",
                    ),
                ),
            )
    except SourceRefreshError:
        raise
    except (ConfiguratorDataError, OSError, ValueError) as error:
        raise SourceRefreshError(
            f"Could not refresh TFT Academy data: {error}"
        ) from error

    return SourceRefreshResult(
        set_number=set_number,
        composition_count=len(refreshed_source_ids),
        added_source_ids=added_source_ids,
        removed_source_ids=removed_source_ids,
        reconciled_source_ids=tuple(
            configuration.source_id for configuration in reconciled
        ),
        removed_configuration_source_ids=tuple(deleted_configurations),
    )


def _source_ids(repository: ConfigurationRepository) -> tuple[str, ...]:
    source_ids = tuple(
        str(composition["sourceId"]) for composition in repository.list_compositions()
    )
    if len(source_ids) != len(set(source_ids)):
        raise SourceRefreshError("Composition index contains duplicate sourceIds")
    return source_ids


def _install_directories(
    staging_root: Path,
    replacements: tuple[tuple[str, Path, Path], ...],
) -> None:
    backup_root = staging_root / "previous"
    discarded_root = staging_root / "discarded"
    installed: list[tuple[str, Path, Path]] = []
    try:
        for label, staged, live in replacements:
            if not staged.is_dir():
                raise SourceRefreshError(
                    f"Downloaded snapshot is missing the {label} directory"
                )
            backup = backup_root / label
            backup.parent.mkdir(parents=True, exist_ok=True)
            live.parent.mkdir(parents=True, exist_ok=True)
            if live.exists():
                live.replace(backup)
            try:
                staged.replace(live)
            except OSError:
                if backup.exists():
                    backup.replace(live)
                raise
            installed.append((label, live, backup))
    except (OSError, SourceRefreshError) as error:
        for label, live, backup in reversed(installed):
            if live.exists():
                discarded = discarded_root / label
                discarded.parent.mkdir(parents=True, exist_ok=True)
                live.replace(discarded)
            if backup.exists():
                backup.replace(live)
        if isinstance(error, SourceRefreshError):
            raise
        raise SourceRefreshError(
            f"Could not install refreshed TFT Academy snapshot: {error}"
        ) from error
