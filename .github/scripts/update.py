from ruamel.yaml import YAML
import toml
import requests
import sys

url = "https://static.rust-lang.org/dist/channel-rust-nightly.toml"
MANIFEST_NAME = "org.freedesktop.Sdk.Extension.rust-nightly.yml"


def check():
    assert rust_aarch64.get("only-arches")[0] == "aarch64", rust_aarch64.get(
        "only-arches"
    )[0]
    assert rust_aarch64.get("url").endswith(
        "rust-nightly-aarch64-unknown-linux-gnu.tar.gz"
    ), rust_aarch64.get("url")
    assert rust_x86_64.get("only-arches")[0] == "x86_64", rust_x86_64.get(
        "only-arches"
    )[0]
    assert rust_x86_64.get("url").endswith(
        "rust-nightly-x86_64-unknown-linux-gnu.tar.gz"
    ), rust_x86_64.get("url")
    assert rust_src.get("url").endswith("rust-src-nightly.tar.gz"), rust_src.get("url")


yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.width = 120
with open(MANIFEST_NAME) as file:
    l = yaml.load(file)

    rust_aarch64 = l["modules"][0]["sources"][0]
    rust_x86_64 = l["modules"][0]["sources"][1]
    rust_src = l["modules"][0]["sources"][2]

    check()

    r = requests.get(url)
    if r.status_code == 200:
        data = toml.loads(r.text)

    new_aarch64_url = data["pkg"]["rust"]["target"]["aarch64-unknown-linux-gnu"].get(
        "url"
    )
    new_aarch64_hash = data["pkg"]["rust"]["target"]["aarch64-unknown-linux-gnu"].get(
        "hash"
    )
    new_x86_64_url = data["pkg"]["rust"]["target"]["x86_64-unknown-linux-gnu"].get(
        "url"
    )
    new_x86_64_hash = data["pkg"]["rust"]["target"]["x86_64-unknown-linux-gnu"].get(
        "hash"
    )
    new_rust_src_url = data["pkg"]["rust-src"]["target"]["*"].get("url")
    new_rust_src_hash = data["pkg"]["rust-src"]["target"]["*"].get("hash")

    r = requests.get(new_aarch64_url)
    if r.status_code == 200:
        aarch64_file_size = len(r.content)

    r = requests.get(new_x86_64_url)
    if r.status_code == 200:
        x86_64_file_size = len(r.content)

    r = requests.get(new_rust_src_url)
    if r.status_code == 200:
        rust_src_file_size = len(r.content)

    rust_aarch64.update(
        url=new_aarch64_url, sha256=new_aarch64_hash, size=aarch64_file_size
    )
    rust_x86_64.update(
        url=new_x86_64_url, sha256=new_x86_64_hash, size=x86_64_file_size
    )
    rust_src.update(
        url=new_rust_src_url, sha256=new_rust_src_hash, size=rust_src_file_size
    )

    check()

    with open(MANIFEST_NAME, "w") as out_file:
        yaml.dump(l, out_file)
