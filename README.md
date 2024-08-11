# This extension should not be used for packaging purposes

# Usage

The path where rust and cargo binaries are located needs to be exported
during build. This can be done by setting `append-path` in
`build-options` for the specified module.

```yaml
id: org.example.your_app
...
sdk-extensions:
  - org.freedesktop.Sdk.Extension.rust-nightly

modules:
  - name: foo
    build-options:
      append-path: /usr/lib/sdk/rust-nightly/extra/sdk/rust-nightly/bin
```
