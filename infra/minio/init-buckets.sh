#!/bin/sh
set -eu
mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null
mc mb --ignore-existing local/geo-quarantine local/geo-clean
mc anonymous set none local/geo-quarantine
mc anonymous set none local/geo-clean
mc admin user add local "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" >/dev/null
mc admin policy create local geo-api-policy /init/policy.json
mc admin policy attach local geo-api-policy --user "$MINIO_ACCESS_KEY"
