#!/bin/bash
# Web-App für den eigenen Ort bauen und hochladen (kaiscribe-privat-n1, 05.11.2026) – Ersatz für deploy.yml (GitHub
# Pages gibt es für das private Repo im Gratis-Konto nicht). Läuft am Mac, im Repo-Hauptordner auf main:
#
#   tools/web_netcup_bauen.sh [--nur-bauen]
#
# Umgebung (aus ~/.hermes/.env, nie committen):
#   KAISCRIBE_WEB_ZIEL      rsync/SFTP-Ziel, z. B. hosting123@hosting123.netcup.net:kaiscribe.roentgen-am-kai.at/
#   KAISCRIBE_WEB_URL       öffentliche Adresse, z. B. https://kaiscribe.roentgen-am-kai.at/
#   KAISCRIBE_HTPASSWD      (optional) absoluter Server-Pfad einer .htpasswd → /download/ nur mit Passwort
#
# 1. Offline-Gates wie test.yml (Python-Teil) – rot = Abbruch
# 2. npm ci + Build mit KAISCRIBE_BASE=/ und VITE_EXE_DOWNLOAD=./download/rakscribe26.exe
# 3. SECURITY-Schritt WÖRTLICH aus .github/workflows/deploy.yml (kein Schlüsselmaterial im Bundle)
# 4. neueste rakscribe26.exe (angemeldet per gh, Prüfsumme = Release-Digest) nach dist/download/, robots.txt + .htaccess
#    (noindex, kein Verzeichnis-Listing, optional Passwort für /download/)
# 5. rsync nach KAISCRIBE_WEB_ZIEL, danach live prüfen: index.html referenziert dasselbe index-*.js wie dist/
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
[ -f ~/.hermes/.env ] && set -a && . ~/.hermes/.env && set +a
REPO=drpeterkalmar/RaKScribe26

echo "1/5 Offline-Gates"
for t in $(grep -oE 'python tests/offline/[a-z_]+\.py' .github/workflows/test.yml | awk '{print $2}'); do
  /usr/bin/python3 "$t" > /tmp/kaiscribe_gate.log 2>&1 || { tail -5 /tmp/kaiscribe_gate.log; echo "ROT: $t"; exit 1; }
done

echo "2/5 Build"
(cd web_app && npm ci --silent && KAISCRIBE_BASE=/ VITE_EXE_DOWNLOAD=./download/rakscribe26.exe npm run build)

echo "3/5 Schlüssel-Schutz (aus deploy.yml)"
/usr/bin/python3 - <<'EOF'
import subprocess, sys, yaml
wf = yaml.safe_load(open(".github/workflows/deploy.yml", encoding="utf-8"))
guard = next(s for s in wf["jobs"]["build-and-deploy"]["steps"] if s.get("name", "").startswith("SECURITY"))["run"]
sys.exit(subprocess.run(["bash", "-c", guard]).returncode)
EOF

echo "4/5 EXE + Server-Dateien"
mkdir -p web_app/dist/download
TAG=$(gh api "repos/$REPO/releases/latest" --jq .tag_name)
SOLL=$(gh api "repos/$REPO/releases/latest" --jq '.assets[]|select(.name=="rakscribe26.exe")|.digest')
gh release download "$TAG" -R "$REPO" -p rakscribe26.exe -D web_app/dist/download --clobber
IST="sha256:$(shasum -a 256 web_app/dist/download/rakscribe26.exe | cut -d' ' -f1)"
[ "$IST" = "$SOLL" ] || { echo "Prüfsumme der EXE falsch ($IST statt $SOLL)"; exit 1; }
printf 'User-agent: *\nDisallow: /\n' > web_app/dist/robots.txt
{
  echo 'Options -Indexes'
  echo 'Header set X-Robots-Tag "noindex, nofollow"'
  echo '<FilesMatch "\.(html)$">'
  echo '  Header set Cache-Control "no-cache"'
  echo '</FilesMatch>'
} > web_app/dist/.htaccess
if [ -n "${KAISCRIBE_HTPASSWD:-}" ]; then
  printf 'AuthType Basic\nAuthName "KaiScribe"\nAuthUserFile %s\nRequire valid-user\n' "$KAISCRIBE_HTPASSWD" \
    > web_app/dist/download/.htaccess
fi
echo "   KaiScribe $TAG ($SOLL)"
[ "${1:-}" = "--nur-bauen" ] && { echo "nur gebaut: web_app/dist"; exit 0; }

echo "5/5 Hochladen + live prüfen"
: "${KAISCRIBE_WEB_ZIEL:?KAISCRIBE_WEB_ZIEL fehlt in ~/.hermes/.env (netcup-Webspace noch nicht eingerichtet?)}"
: "${KAISCRIBE_WEB_URL:?KAISCRIBE_WEB_URL fehlt in ~/.hermes/.env}"
rsync -rlz --delete --exclude '.well-known' web_app/dist/ "$KAISCRIBE_WEB_ZIEL"
JS=$(grep -oE 'assets/index-[^"]+\.js' web_app/dist/index.html | head -1)
for i in $(seq 1 12); do
  curl -s "${KAISCRIBE_WEB_URL}?x=$RANDOM" | grep -q "$JS" && { echo "live: $KAISCRIBE_WEB_URL ($JS)"; exit 0; }
  sleep 10
done
echo "live NICHT bestätigt: $KAISCRIBE_WEB_URL referenziert $JS nicht"; exit 1
