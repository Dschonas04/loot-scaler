#!/usr/bin/env bash
# Fetches into libs/ what the build needs but the repository must not carry:
# the Minecraft server jar from Mojang and the Fabric API modules the mod
# compiles against, from the Fabric maven. Used by CI and for a fresh clone.
#
#   tools/fetch-libs.sh
set -euo pipefail
cd "$(dirname "$0")/.."

mc="$(sed -n 's/^minecraft_version=//p' gradle.properties)"
api="$(sed -n 's/^fabric_api_version=//p' gradle.properties)"
modules="$(sed -n 's/^fabric_api_modules=//p' gradle.properties)"
mkdir -p libs
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

# Since 1.18 the server jar is a bundle; the classes themselves are in
# META-INF/versions/<version>/server-<version>.jar.
if [ ! -f libs/server.jar ]; then
  echo "Minecraft $mc"
  version_url="$(curl -fsSL https://piston-meta.mojang.com/mc/game/version_manifest_v2.json |
    python3 -c "import json,sys; print(next(v['url'] for v in json.load(sys.stdin)['versions'] if v['id']=='$mc'))")"
  server_url="$(curl -fsSL "$version_url" | python3 -c "import json,sys; print(json.load(sys.stdin)['downloads']['server']['url'])")"
  curl -fsSL "$server_url" -o "$work/bundle.jar"
  python3 - "$work/bundle.jar" "$mc" <<'PY'
import sys, zipfile, shutil
bundle, mc = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(bundle) as z, z.open(f"META-INF/versions/{mc}/server-{mc}.jar") as src, open("libs/server.jar", "wb") as dst:
    shutil.copyfileobj(src, dst)
PY
fi

if [ -n "$modules" ]; then
  echo "Fabric API $api: $modules"
  curl -fsSL "https://maven.fabricmc.net/net/fabricmc/fabric-api/fabric-api/$api/fabric-api-$api.jar" -o "$work/api.jar"
  python3 - "$work/api.jar" $modules <<'PY'
import sys, zipfile
api, wanted = sys.argv[1], sys.argv[2:]
with zipfile.ZipFile(api) as z:
    for name in z.namelist():
        if not name.startswith("META-INF/jars/"):
            continue
        fname = name.rsplit("/", 1)[1]
        for module in wanted:
            if fname.startswith(module + "-"):
                with open(f"libs/{module}.jar", "wb") as dst:
                    dst.write(z.read(name))
                print("  libs/" + module + ".jar")
PY
fi
ls -l libs
