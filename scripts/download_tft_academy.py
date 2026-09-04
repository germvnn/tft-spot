from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data"
DEFAULT_BASE_URL = "https://tftacademy.com"
FILES_BASE_URL = "https://api.tftacademy.com/api/files"
USER_AGENT = "TFT-Spot/0.1 data snapshot"

RESOURCE_ENDPOINTS = {
    "augments.json": "/api/assets/augments?set={set_number}",
    "champions.json": "/api/assets/champions?set={set_number}",
    "items.json": "/api/assets/items?set={set_number}",
    "traits.json": "/api/assets/traits?set={set_number}",
}
ASSET_FIELDS = {
    "champions.json": (
        "champions",
        {
            "championIcon": "champions",
            "championSquareIcon": "champions",
            "championTileIcon": "champions",
            "abilityIcon": "champion_abilities",
        },
    ),
    "items.json": ("items", {"icon": "items"}),
    "augments.json": ("augments", {"icon": "augments"}),
    "traits.json": ("traits", {"icon": "traits"}),
}


class SnapshotError(RuntimeError):
    pass


@dataclass(frozen=True)
class HttpPayload:
    body: bytes
    status: int
    content_type: str
    final_url: str


@dataclass(frozen=True)
class AssetRequest:
    category: str
    entity_type: str
    entity_source_id: str
    entity_api_name: str
    field: str
    filename: str
    url: str


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def fetch(
    url: str,
    *,
    timeout: float,
    retries: int,
    accept: str = "*/*",
) -> HttpPayload:
    request = urllib.request.Request(
        url,
        headers={"Accept": accept, "User-Agent": USER_AGENT},
    )
    last_error: BaseException | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return HttpPayload(
                    body=response.read(),
                    status=getattr(response, "status", 200),
                    content_type=response.headers.get_content_type(),
                    final_url=response.geturl(),
                )
        except (TimeoutError, urllib.error.HTTPError, urllib.error.URLError) as error:
            last_error = error
            if attempt == retries:
                break
            time.sleep(2**attempt)
    raise SnapshotError(f"Could not download {url}: {last_error}")


def write_bytes(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f"{path.name}.part")
    temporary_path.write_bytes(body)
    temporary_path.replace(path)


def write_json(path: Path, payload: Any) -> None:
    body = (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode()
    write_bytes(path, body)


def require_content_type(
    payload: HttpPayload,
    expected_prefix: str,
    url: str,
) -> None:
    if not payload.content_type.startswith(expected_prefix):
        raise SnapshotError(
            f"Expected {expected_prefix!r} from {url}, got {payload.content_type!r}"
        )


def manifest_entry(
    *,
    url: str,
    filename: str,
    payload: HttpPayload,
    downloaded_at: str,
) -> dict[str, Any]:
    return {
        "url": url,
        "final_url": payload.final_url,
        "status": payload.status,
        "content_type": payload.content_type,
        "filename": filename,
        "size_bytes": len(payload.body),
        "sha256": hashlib.sha256(payload.body).hexdigest(),
        "downloaded_at": downloaded_at,
    }


def extract_composition_slugs(html: str, set_number: int) -> list[str]:
    pattern = re.compile(
        r"""href=["']/tierlist/comps/(set-"""
        + re.escape(str(set_number))
        + r"""-[^/"'?#]+)"""
    )
    return list(dict.fromkeys(pattern.findall(html)))


def unflatten_sveltekit_data(values: list[Any]) -> Any:
    if not values:
        raise SnapshotError("SvelteKit data array is empty")
    memo: dict[int, Any] = {}
    special = {
        -1: None,
        -2: None,
        -3: math.nan,
        -4: math.inf,
        -5: -math.inf,
        -6: -0.0,
    }

    def reference(value: Any) -> Any:
        if isinstance(value, bool) or not isinstance(value, int):
            return value
        if value < 0:
            return special.get(value)
        return hydrate(value)

    def hydrate(index: int) -> Any:
        if index in memo:
            return memo[index]
        if index >= len(values):
            raise SnapshotError(
                f"SvelteKit reference {index} exceeds data size {len(values)}"
            )
        value = values[index]
        if isinstance(value, dict):
            result: Any = {}
            memo[index] = result
            result.update({key: reference(item) for key, item in value.items()})
            return result
        if isinstance(value, list):
            if value and isinstance(value[0], str):
                tag = value[0]
                if tag == "Date":
                    result = value[1]
                elif tag == "BigInt":
                    result = int(value[1])
                elif tag == "Set":
                    result = [reference(item) for item in value[1:]]
                elif tag == "Map":
                    result = {
                        reference(value[position]): reference(value[position + 1])
                        for position in range(1, len(value), 2)
                    }
                else:
                    raise SnapshotError(f"Unsupported SvelteKit tag: {tag!r}")
                memo[index] = result
                return result
            result = []
            memo[index] = result
            result.extend(reference(item) for item in value)
            return result
        memo[index] = value
        return value

    return hydrate(0)


def extract_queried_guide(payload: dict[str, Any]) -> dict[str, Any]:
    for node in payload.get("nodes", []):
        if not isinstance(node, dict) or not isinstance(node.get("data"), list):
            continue
        decoded = unflatten_sveltekit_data(node["data"])
        if isinstance(decoded, dict):
            guide = decoded.get("queriedGuide")
            if isinstance(guide, dict):
                return guide
    raise SnapshotError("Could not find queriedGuide in SvelteKit response")


def download_raw_resources(
    *,
    data_dir: Path,
    base_url: str,
    listing_path: str,
    set_number: int,
    timeout: float,
    retries: int,
    downloaded_at: str,
) -> tuple[list[dict[str, Any]], str, str]:
    raw_dir = data_dir / "raw" / "tft_academy"
    raw_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    listing_url = urllib.parse.urljoin(base_url, listing_path)
    listing = fetch(
        listing_url,
        timeout=timeout,
        retries=retries,
        accept="text/html",
    )
    require_content_type(listing, "text/html", listing_url)
    write_bytes(raw_dir / "comps.html", listing.body)
    entries.append(
        manifest_entry(
            url=listing_url,
            filename="comps.html",
            payload=listing,
            downloaded_at=downloaded_at,
        )
    )
    for filename, endpoint_template in RESOURCE_ENDPOINTS.items():
        url = urllib.parse.urljoin(
            base_url,
            endpoint_template.format(set_number=set_number),
        )
        response = fetch(
            url,
            timeout=timeout,
            retries=retries,
            accept="application/json",
        )
        require_content_type(response, "application/json", url)
        json.loads(response.body)
        write_bytes(raw_dir / filename, response.body)
        entries.append(
            manifest_entry(
                url=url,
                filename=filename,
                payload=response,
                downloaded_at=downloaded_at,
            )
        )
    return entries, listing.body.decode("utf-8"), listing_url


def download_compositions(
    *,
    data_dir: Path,
    base_url: str,
    listing_url: str,
    listing_html: str,
    set_number: int,
    timeout: float,
    retries: int,
    downloaded_at: str,
) -> list[dict[str, Any]]:
    target_dir = data_dir / "raw" / "tft_academy" / "compositions"
    slugs = extract_composition_slugs(listing_html, set_number)
    if not slugs:
        raise SnapshotError(
            f"No Set {set_number} composition links found at {listing_url}"
        )
    entries: list[dict[str, Any]] = []
    seen_ids: dict[str, str] = {}
    for slug in slugs:
        url = urllib.parse.urljoin(
            base_url,
            f"/tierlist/comps/{slug}/__data.json",
        )
        response = fetch(
            url,
            timeout=timeout,
            retries=retries,
            accept="application/json",
        )
        require_content_type(response, "application/json", url)
        guide = extract_queried_guide(json.loads(response.body))
        source_id = str(guide["id"])
        response_slug = str(guide["compSlug"])
        if response_slug != slug:
            raise SnapshotError(f"Route {slug!r} returned {response_slug!r}")
        if source_id in seen_ids and seen_ids[source_id] != slug:
            raise SnapshotError(
                f"Source id {source_id!r} belongs to two composition routes"
            )
        seen_ids[source_id] = slug
        target = target_dir / f"{source_id}.json"
        write_bytes(target, response.body)
        entries.append(
            {
                "visible_name": str(
                    guide.get("title") or guide.get("metaTitle") or slug
                ),
                "backend_id": source_id,
                "slug": slug,
                "request_url": url,
                "response_file": target.relative_to(data_dir.parent).as_posix(),
                "status": response.status,
                "content_type": response.content_type,
                "size_bytes": len(response.body),
                "sha256": hashlib.sha256(response.body).hexdigest(),
            }
        )
    index = {
        "captured_at": downloaded_at,
        "source_page": listing_url,
        "hover_request_pattern": "GET /tierlist/comps/{slug}/__data.json",
        "set": set_number,
        "visible_name_to_backend_id": {
            entry["visible_name"]: entry["backend_id"] for entry in entries
        },
        "compositions": entries,
    }
    write_json(target_dir / "index.json", index)
    return entries


def build_asset_requests(data_dir: Path) -> list[AssetRequest]:
    raw_dir = data_dir / "raw" / "tft_academy"
    requests: list[AssetRequest] = []
    seen_targets: dict[tuple[str, str], str] = {}
    for resource_filename, (root_key, fields) in ASSET_FIELDS.items():
        resource = json.loads((raw_dir / resource_filename).read_text(encoding="utf-8"))
        for record in resource[root_key]:
            for field, category in fields.items():
                filename = record.get(field)
                if not filename:
                    continue
                if Path(filename).name != filename:
                    raise SnapshotError(f"Unsafe asset filename: {filename!r}")
                url = (
                    f"{FILES_BASE_URL}/{record['collectionId']}/"
                    f"{record['id']}/{filename}"
                )
                key = (category, filename)
                previous_url = seen_targets.get(key)
                if previous_url is not None:
                    if previous_url != url:
                        raise SnapshotError(
                            f"Asset collision for {category}/{filename}"
                        )
                    continue
                seen_targets[key] = url
                requests.append(
                    AssetRequest(
                        category=category,
                        entity_type=root_key.removesuffix("s"),
                        entity_source_id=str(record["id"]),
                        entity_api_name=str(record["apiName"]),
                        field=field,
                        filename=filename,
                        url=url,
                    )
                )
    return requests


def download_assets(
    *,
    data_dir: Path,
    timeout: float,
    retries: int,
    workers: int,
    downloaded_at: str,
) -> dict[str, Any]:
    assets_dir = data_dir / "assets"
    requests = build_asset_requests(data_dir)

    def download_one(asset: AssetRequest) -> dict[str, Any]:
        try:
            response = fetch(
                asset.url,
                timeout=timeout,
                retries=retries,
                accept="image/*",
            )
            require_content_type(response, "image/", asset.url)
            relative_path = Path(asset.category) / asset.filename
            write_bytes(assets_dir / relative_path, response.body)
            return {
                "ok": True,
                "entityType": asset.entity_type,
                "entitySourceId": asset.entity_source_id,
                "entityApiName": asset.entity_api_name,
                "field": asset.field,
                "sourceUrl": asset.url,
                "httpStatus": response.status,
                "contentType": response.content_type,
                "filename": asset.filename,
                "relativePath": relative_path.as_posix(),
                "sizeBytes": len(response.body),
                "sha256": hashlib.sha256(response.body).hexdigest(),
                "downloadedAt": downloaded_at,
            }
        except (OSError, SnapshotError) as error:
            return {
                "ok": False,
                "entityType": asset.entity_type,
                "entitySourceId": asset.entity_source_id,
                "entityApiName": asset.entity_api_name,
                "field": asset.field,
                "sourceUrl": asset.url,
                "error": str(error),
                "downloadedAt": downloaded_at,
            }

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for position, result in enumerate(
            executor.map(download_one, requests),
            start=1,
        ):
            results.append(result)
            if position % 100 == 0 or position == len(requests):
                print(f"Downloaded assets: {position}/{len(requests)}")
    assets = [
        {key: value for key, value in result.items() if key != "ok"}
        for result in results
        if result["ok"]
    ]
    failures = [
        {key: value for key, value in result.items() if key != "ok"}
        for result in results
        if not result["ok"]
    ]
    manifest = {
        "source": "TFT Academy",
        "filesBaseUrl": FILES_BASE_URL,
        "downloadedAt": downloaded_at,
        "assetCount": len(assets),
        "failureCount": len(failures),
        "assets": assets,
        "failures": failures,
    }
    write_json(assets_dir / "manifest.json", manifest)
    if failures:
        raise SnapshotError(
            f"{len(failures)} asset downloads failed; "
            f"see {assets_dir / 'manifest.json'}"
        )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download a complete TFT Academy data and asset snapshot."
    )
    parser.add_argument("--set", dest="set_number", type=int, default=18)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--listing-path", default="/tierlist/comps")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--skip-assets", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.set_number <= 0 or args.timeout <= 0 or args.workers <= 0:
        raise SystemExit("set, timeout and workers must be positive")
    if args.retries < 0:
        raise SystemExit("retries cannot be negative")
    data_dir = args.data_dir.resolve()
    base_url = args.base_url.rstrip("/") + "/"
    downloaded_at = utc_now()
    print(f"Downloading TFT Academy Set {args.set_number} to {data_dir}")
    resources, listing_html, listing_url = download_raw_resources(
        data_dir=data_dir,
        base_url=base_url,
        listing_path=args.listing_path,
        set_number=args.set_number,
        timeout=args.timeout,
        retries=args.retries,
        downloaded_at=downloaded_at,
    )
    compositions = download_compositions(
        data_dir=data_dir,
        base_url=base_url,
        listing_url=listing_url,
        listing_html=listing_html,
        set_number=args.set_number,
        timeout=args.timeout,
        retries=args.retries,
        downloaded_at=downloaded_at,
    )
    write_json(
        data_dir / "raw" / "tft_academy" / "manifest.json",
        {
            "source_page": listing_url,
            "downloaded_at": downloaded_at,
            "set": args.set_number,
            "composition_count": len(compositions),
            "resources": resources,
        },
    )
    print(f"Downloaded raw resources and {len(compositions)} compositions")
    if not args.skip_assets:
        asset_manifest = download_assets(
            data_dir=data_dir,
            timeout=args.timeout,
            retries=args.retries,
            workers=args.workers,
            downloaded_at=downloaded_at,
        )
        print(f"Downloaded {asset_manifest['assetCount']} UI assets")
    print("TFT Academy snapshot complete")


if __name__ == "__main__":
    main()
