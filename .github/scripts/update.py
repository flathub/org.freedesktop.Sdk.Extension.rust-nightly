from ruamel.yaml import YAML
import toml
import requests

URL = "https://static.rust-lang.org/dist/channel-rust-nightly.toml"
MANIFEST_NAME = "org.freedesktop.Sdk.Extension.rust-nightly.yml"


def load_yaml(file_name):
    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 120
    with open(file_name, "r") as file:
        return yaml, yaml.load(file)


def save_yaml(file_name, data, yaml_instance):
    with open(file_name, "w") as file:
        yaml_instance.dump(data, file)


def fetch_data(url):
    response = requests.get(url)
    response.raise_for_status()
    return response


def update_source(source, new_data, file_size):
    source.update(url=new_data["url"], sha256=new_data["hash"], size=file_size)


def validate_sources(sources, suffixes):
    for arch, source in sources.items():
        if "only-arches" in source:
            assert (
                arch == source["only-arches"][0]
            ), f"Mismatch in 'only-arches' for {arch}: {source['only-arches']}"
        else:
            assert arch == "rust-src"

        assert source["url"].endswith(
            suffixes[arch]
        ), f"URL for {arch} does not end with {suffixes[arch]}: {source['url']}"


def main():
    yaml, manifest = load_yaml(MANIFEST_NAME)

    sources = {
        "aarch64": manifest["modules"][0]["sources"][0],
        "x86_64": manifest["modules"][0]["sources"][1],
        "rust-src": manifest["modules"][0]["sources"][2],
    }

    suffixes = {
        "aarch64": "rust-nightly-aarch64-unknown-linux-gnu.tar.gz",
        "x86_64": "rust-nightly-x86_64-unknown-linux-gnu.tar.gz",
        "rust-src": "rust-src-nightly.tar.gz",
    }

    validate_sources(sources, suffixes)

    nightly_data = toml.loads(fetch_data(URL).text)

    for arch, source in sources.items():
        if arch == "rust-src":
            new_data = nightly_data["pkg"]["rust-src"]["target"]["*"]
        else:
            new_data = nightly_data["pkg"]["rust"]["target"][
                f"{arch}-unknown-linux-gnu"
            ]

        response = fetch_data(new_data["url"])
        update_source(source, new_data, len(response.content))

    validate_sources(sources, suffixes)

    save_yaml(MANIFEST_NAME, manifest, yaml)


if __name__ == "__main__":
    main()
