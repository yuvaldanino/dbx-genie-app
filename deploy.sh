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

# 3. Restore Lakebase postgres resource (bundle deploy strips it every time)
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
APP_JSON=$(databricks apps get "$APP_NAME" --profile vm -o json)
SP_APP_ID=$(echo "$APP_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['service_principal_client_id'])")
WAREHOUSE_ID=$(echo "$APP_JSON" | python3 -c "
import sys,json
r=json.load(sys.stdin).get('resources',[])
print(next((x['sql_warehouse']['id'] for x in r if 'sql_warehouse' in x), ''))
")
echo "  Service principal: $SP_APP_ID"
echo "  Warehouse: $WAREHOUSE_ID"

# NOTE: payload built via json.dumps — the old hand-rolled JSON escaped backticks
# as \` (invalid JSON), so the CLI rejected every grant silently for months.
run_sql() {
  local sql="$1"
  local payload result state
  payload=$(python3 -c 'import json,sys; print(json.dumps({"statement": sys.argv[1], "warehouse_id": sys.argv[2], "wait_timeout": "30s"}))' "$sql" "$WAREHOUSE_ID")
  result=$(databricks api post /api/2.0/sql/statements --profile vm --json "$payload" 2>&1)
  state=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',{}).get('state','UNKNOWN'))" 2>/dev/null || echo "ERROR")
  if [ "$state" = "SUCCEEDED" ]; then
    echo "  OK: $sql"
  else
    echo "  FAILED ($state): $sql"
    echo "$result" | head -3
    return 1
  fi
}

GRANTS_OK=1
run_sql "GRANT USE CATALOG, USE SCHEMA, SELECT ON CATALOG ${CATALOG} TO \`${SP_APP_ID}\`" || GRANTS_OK=0
run_sql "GRANT MODIFY ON SCHEMA ${CATALOG}.${SCHEMA} TO \`${SP_APP_ID}\`" || GRANTS_OK=0
run_sql "GRANT READ VOLUME, WRITE VOLUME ON VOLUME ${CATALOG}.${SCHEMA}.${VOLUME} TO \`${SP_APP_ID}\`" || GRANTS_OK=0
if [ "$GRANTS_OK" = "1" ]; then
  echo "UC permissions granted."
else
  echo "⚠️  Some UC grants FAILED — SQL re-execution/recompute will break. Fix before relying on the app."
fi

# 5. Deploy app
echo ""
echo "--- Deploying app ---"
databricks apps deploy "$APP_NAME" --profile vm
echo ""
echo "=== Deployment complete! ==="
echo "App URL: https://${APP_NAME}-7474655921234161.aws.databricksapps.com"
echo ""
echo "⚠️  Run this in the Lakebase SQL editor after deploy:"
echo "    GRANT app_rw TO \"677d1641-521c-4df6-91f4-dacea8be74e7\";"
