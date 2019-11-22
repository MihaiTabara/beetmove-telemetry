# beetmove-telemetry
Scripts to upload the mobile telemetry under https://maven.mozilla.org/

# Example of usage
```bash
$ cp config_example.json script_config.json
$ < update script_config with actual credentials > ...
$ pip install -r requirements.txt
$ python script.py  --release-url https://github.com/mozilla/glean/releases/download/v19.0.0/glean-v19.0.0.zip \
                    --script-config script_config.json \
                    --bucket {maven-staging,maven-production} \
                    --version 19.0.0
```
