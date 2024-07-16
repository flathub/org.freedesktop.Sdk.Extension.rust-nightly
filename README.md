# Rust Nightly SDK

If you're using a CI, you can use this image which is updated automatically


This image contains `org.gnome.Sdk//3.34` & `org.freedesktop.Sdk//19.08`
```
docker.io/bilelmoussaoui/rust-nightly:latest
```

This image contains `org.gnome.Sdk//master` & `org.freedesktop.Sdk//master`
```
docker.io/bilelmoussaoui/rust-nightly:master
```

# Usage

The path where rust and cargo binaries are located needs to be exported
during build. This can be done by setting `append-path` in
`build-options` for the specified module.

```yaml
sdk-extensions:
  - org.freedesktop.Sdk.Extension.rust-nightly

modules:
  - name: foo
    build-options:
      append-path: /usr/lib/sdk/rust-nightly/extra/sdk/rust-nightly/bin
```
