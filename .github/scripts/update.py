import argparse
import logging
import textwrap
from typing import Any

import requests
import toml
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.error import YAMLError

log = logging.getLogger(__name__)

DEFAULT_CHANNEL_URL = "https://static.rust-lang.org/dist/channel-rust-nightly.toml"
DEFAULT_MANIFEST_NAME = "org.freedesktop.Sdk.Extension.rust-nightly.yml"

SUPPORTED_CHANNEL_MANIFEST_VERSION = "2"

yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.width = 2**31


def load_yaml(file_name: str) -> tuple[YAML, dict[str, Any]] | None:
    try:
        with open(file_name) as file:
            data: dict[str, Any] = yaml.load(file)
            return yaml, data
    except OSError as err:
        log.error("Failed to read manifest %r: %s", file_name, err)
    except YAMLError as err:
        log.error("Failed to parse manifest %r: %s", file_name, err)
    return None


def save_yaml(file_name: str, data: dict[str, Any], yaml_instance: YAML) -> bool:
    try:
        with open(file_name, "w") as file:
            yaml_instance.dump(data, file)
        return True
    except OSError as err:
        log.error("Failed to write manifest %r: %s", file_name, err)
    except YAMLError as err:
        log.error("Failed to dump manifest %r: %s", file_name, err)
    return False


def fetch(url: str, *, stream: bool = False) -> requests.Response | None:
    try:
        response = requests.get(url, stream=stream)  # noqa: S113
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as err:
        log.error("Error fetching %r: %s", url, err)
    return None


def get_size(url: str) -> int | None:
    response = fetch(url, stream=True)
    if response is None:
        return None
    size = response.headers.get("Content-Length")
    if size is None:
        log.error("Missing Content-Length header for %r", url)
        return None
    return int(size)


def get_sources(
    manifest: dict[str, Any],
    arches: list[str],
) -> dict[str, CommentedMap] | None:
    try:
        sources: dict[str, CommentedMap] = {
            arch: manifest["modules"][0]["sources"][i] for i, arch in enumerate(arches)
        }
        sources["rust-src"] = manifest["modules"][0]["sources"][len(arches)]
        return sources
    except (KeyError, IndexError, TypeError) as err:
        log.error("Unexpected manifest structure: %s", err)
    return None


def update_source(
    source: CommentedMap,
    new_data: dict[str, str | bool],
    *,
    update_size: bool = False,
) -> bool:
    source["url"] = new_data["url"]
    source["sha256"] = new_data["hash"]
    if update_size:
        size = get_size(str(new_data["url"]))
        if size is None:
            return False
        source["size"] = size
    elif "size" in source:
        del source["size"]
    return True


def validate_sources(
    sources: dict[str, CommentedMap],
    suffixes: dict[str, str],
) -> bool:
    for arch, source in sources.items():
        if "only-arches" in source:
            if arch != source["only-arches"][0]:
                log.error(
                    "Mismatch in 'only-arches' for %r: %s",
                    arch,
                    source["only-arches"],
                )
                return False
        elif arch != "rust-src":
            log.error(
                "Expected 'only-arches' key for arch %r or arch to be 'rust-src'",
                arch,
            )
            return False
        if not source["url"].endswith(suffixes[arch]):
            log.error(
                "URL for %r does not end with expected suffix %r: %s",
                arch,
                suffixes[arch],
                source["url"],
            )
            return False
    return True


def build_suffixes(arches: list[str]) -> dict[str, str]:
    suffixes: dict[str, str] = {
        arch: f"rust-nightly-{arch}-unknown-linux-gnu.tar.gz" for arch in arches
    }
    suffixes["rust-src"] = "rust-src-nightly.tar.gz"
    return suffixes


def fetch_nightly_data(url: str) -> dict[str, Any] | None:
    response = fetch(url)
    if response is None:
        return None
    try:
        data = toml.loads(response.text)
    except toml.TomlDecodeError as err:
        log.error("Failed to parse nightly manifest TOML: %s", err)
        return None
    version = data.get("manifest-version")
    if version != SUPPORTED_CHANNEL_MANIFEST_VERSION:
        log.error(
            "Unknown channel manifest version %r, expected %r",
            version,
            SUPPORTED_CHANNEL_MANIFEST_VERSION,
        )
        return None
    return data


def get_arch_data(
    nightly_data: dict[str, Any],
    arch: str,
) -> dict[str, str | bool] | None:
    data: dict[str, str | bool] | None = None
    try:
        if arch == "rust-src":
            # for mypy
            data = nightly_data["pkg"]["rust-src"]["target"]["*"]
            return data  # noqa: RET504
        # for mypy
        data = nightly_data["pkg"]["rust"]["target"][f"{arch}-unknown-linux-gnu"]
        return data  # noqa: RET504
    except KeyError as err:
        log.error("Missing key in nightly manifest for arch %r: %s", arch, err)
    return None


def parse_args() -> argparse.Namespace:
    description = textwrap.dedent("""\
        A script to update rust sources in Flatpak manifests
    """)
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--extra-data-mode",
        action="store_true",
        help="Populate size in manifest (default: %(default)s)",
    )
    parser.add_argument(
        "--arch",
        dest="arches",
        metavar="",
        type=lambda s: s.split(","),
        default=["aarch64", "x86_64"],
        help="Comma-separated target architectures to update (default: %(default)s)",
    )
    parser.add_argument(
        "--manifest",
        default=DEFAULT_MANIFEST_NAME,
        metavar="",
        type=str,
        help="Path to the Flatpak manifest YAML (default: %(default)s)",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_CHANNEL_URL,
        metavar="",
        type=str,
        help="URL to channel TOML manifest (default: %(default)s)",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    args = parse_args()

    result = load_yaml(args.manifest)
    if result is None:
        return 1
    yaml_instance, manifest = result

    sources = get_sources(manifest, args.arches)
    if sources is None:
        return 1

    suffixes = build_suffixes(args.arches)

    if not validate_sources(sources, suffixes):
        return 1

    nightly_data = fetch_nightly_data(args.url)
    if nightly_data is None:
        return 1

    for arch, source in sources.items():
        arch_data = get_arch_data(nightly_data, arch)
        if arch_data is None:
            return 1
        if not update_source(source, arch_data, update_size=args.extra_data_mode):
            return 1

    if not validate_sources(sources, suffixes):
        return 1

    if not save_yaml(args.manifest, manifest, yaml_instance):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
