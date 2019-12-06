# beetmove-telemetry
Scripts to upload the mobile telemetry under https://maven.mozilla.org/

# Example of usage
```bash
$ cp config_example.json script_config.json
$ < update script_config with actual credentials > ...
$ pip install -U -r requirements.txt
$ VERSION='22.0.0'; python script.py --release-url "https://github.com/mozilla/glean/releases/download/v$VERSION/glean-v$VERSION.zip" \
                                     --script-config script_config.json \
                                     --bucket maven-production \
                                     --version "$VERSION"
```
