#!/bin/bash
set -euo pipefail

TARGET="${1:-dev}"
CATALOG="${2:-yd_launchpad_final_classic_catalog}"
SCHEMA="${3:-genie_app}"
VOLUME="raw_data"
APP_NAME="genieapp-${TARGET}"

echo "=== Deploying GenieApp to target: $TARGET ==="

# 1. Build frontend
echo ""
echo "--- Building frontend ---"
bun run --bun node_modules/.bin/vite build
echo "Frontend built."

# 2. Deploy bundle
echo ""
echo "--- Deploying bundle ---"
databricks bundle deploy -t "$TARGET"
echo "Bundle deployed."

# 3. Restore Lakebase postgres resource (bundle deploy strips it)
echo ""
echo "--- Restoring Lakebase resource ---"
.venv/bin/python -c "
from databricks.sdk import WorkspaceClient
w = WorkspaceClient(profile='vm')
app = w.api_client.do('GET', '/api/2.0/apps/${APP_NAME}')
resources = app.get('resources', [])
if not any(r.get('postgres') for r in resources):
    resources.append({
        'name': 'database',
        'postgres': {
            'branch': 'projects/genie-app/branches/production',
            'database': 'projects/genie-app/branches/production/databases/db-q2cq-zfogvc320i',
            'permission': 'CAN_CONNECT_AND_CREATE'
        }
    })
    w.api_client.do('PATCH', '/api/2.0/apps/${APP_NAME}', body={'resources': resources})
    print('  Postgres resource restored')
else:
    print('  Postgres resource already present')
"

# 4. Grant app service principal UC permissions
echo ""
echo "--- Granting app permissions ---"
APP_JSON=$(databricks apps get "$APP_NAME" -o json)
SP_APP_ID=$(echo "$APP_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['service_principal_client_id'])")
WAREHOUSE_ID=$(echo "$APP_JSON" | python3 -c "
import sys,json
r=json.load(sys.stdin).get('resources',[])
print(next((x['sql_warehouse']['id'] for x in r if 'sql_warehouse' in x), ''))
")
echo "  Service principal: $SP_APP_ID"
echo "  Warehouse: $WAREHOUSE_ID"

run_sql() {
  local sql="$1"
  local result
  result=$(databricks api post /api/2.0/sql/statements --json "{
    \"statement\": \"${sql}\",
    \"warehouse_id\": \"${WAREHOUSE_ID}\",
    \"wait_timeout\": \"30s\"
  }" 2>&1)
  local state
  state=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',{}).get('state','UNKNOWN'))" 2>/dev/null || echo "ERROR")
  if [ "$state" = "SUCCEEDED" ]; then
    echo "  OK: $sql"
  else
    echo "  WARN ($state): $sql"
  fi
}

run_sql "GRANT USE_CATALOG ON CATALOG ${CATALOG} TO \\\`${SP_APP_ID}\\\`" || true
run_sql "GRANT USE_SCHEMA, SELECT, MODIFY ON SCHEMA ${CATALOG}.${SCHEMA} TO \\\`${SP_APP_ID}\\\`" || true
run_sql "GRANT READ_VOLUME, WRITE_VOLUME ON VOLUME ${CATALOG}.${SCHEMA}.${VOLUME} TO \\\`${SP_APP_ID}\\\`" || true
echo "UC permissions granted (or already exist)."

# 5. Deploy app
echo ""
echo "--- Deploying app ---"
databricks apps deploy "$APP_NAME" --profile vm
echo ""
echo "=== Deployment complete! ==="
echo "App URL: https://${APP_NAME}-7474655921234161.aws.databricksapps.com"
echo ""
echo "⚠️  IMPORTANT: Run this in the Lakebase SQL editor after deploy:"
echo "    GRANT ALL ON ALL TABLES IN SCHEMA public TO \"677d1641-521c-4df6-91f4-dacea8be74e7\";"
