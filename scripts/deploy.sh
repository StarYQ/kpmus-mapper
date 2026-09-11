#!/usr/bin/env bash
# Rsync the repo to the app box and rebuild/restart the container there.
# Run from the repo root: bash scripts/deploy.sh
set -euo pipefail
cd "$(dirname "$0")/.."

KEY=~/.ssh/id_ed25519_pmus-kalshi-mapper
APP_IP=$(terraform -chdir=terraform output -raw app_ip)
DB_HOST=$(terraform -chdir=terraform output -raw db_endpoint | cut -d: -f1)
DB_PASS=$(sed -n 's/^db_password *= *"\(.*\)"/\1/p' terraform/terraform.tfvars)
if [ -z "$DB_PASS" ]; then
    echo "deploy: no db_password in terraform/terraform.tfvars" >&2
    exit 1
fi
DATABASE_URL="postgresql+psycopg://mapper:${DB_PASS}@${DB_HOST}:5432/mapper"

rsync -az --delete \
    -e "ssh -i $KEY -o StrictHostKeyChecking=no" \
    --exclude .git --exclude .venv --exclude venv --exclude node_modules \
    --exclude web/dist --exclude terraform --exclude __pycache__ --exclude '*.pyc' \
    --exclude docs \
    ./ "ec2-user@$APP_IP:pmus-kalshi-mapper/"

# Keys: keys.json names the PEM files by laptop paths. The container mounts keys/ at /app/keys,
# so ship both PEMs next to keys.json and point the box copy at them. Nothing touches a temp file.
KALSHI_PEM=$(python3 -c "import json; print(json.load(open('keys/keys.json'))['kalshi']['private_key_path'])")
PMUS_PEM=$(python3 -c "import json; print(json.load(open('keys/keys.json'))['polymarket_public']['prod']['private_key_path'])")
scp -q -i "$KEY" -o StrictHostKeyChecking=no "$KALSHI_PEM" "ec2-user@$APP_IP:pmus-kalshi-mapper/keys/kalshi.pem"
scp -q -i "$KEY" -o StrictHostKeyChecking=no "$PMUS_PEM" "ec2-user@$APP_IP:pmus-kalshi-mapper/keys/pmus.pem"
python3 -c "import json; d = json.load(open('keys/keys.json')); d['kalshi']['private_key_path'] = '/app/keys/kalshi.pem'; d['polymarket_public']['prod']['private_key_path'] = '/app/keys/pmus.pem'; print(json.dumps(d, indent=2))" \
    | ssh -i "$KEY" -o StrictHostKeyChecking=no "ec2-user@$APP_IP" "cat > pmus-kalshi-mapper/keys/keys.json && chmod 600 pmus-kalshi-mapper/keys/keys.json pmus-kalshi-mapper/keys/kalshi.pem pmus-kalshi-mapper/keys/pmus.pem"

ssh -i "$KEY" -o StrictHostKeyChecking=no "ec2-user@$APP_IP" \
    "cd pmus-kalshi-mapper && DATABASE_URL='$DATABASE_URL' INIT_DB_ARGS='${INIT_DB_ARGS:-}' bash scripts/remote_deploy.sh"

# gunicorn needs a few seconds after the container starts; poll instead of failing on the first try.
for _ in $(seq 1 15); do
    if curl -sf "http://$APP_IP/health"; then echo; echo "up: http://$APP_IP/"; exit 0; fi
    sleep 2
done
echo "deploy: container started but /health did not answer within 30 s" >&2
exit 1
