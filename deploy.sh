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

# 3. Grant app service principal UC permissions
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

run_sql "GRANT USE_CATALOG ON CATALOG ${CATALOG} TO \\\`${SP_APP_ID}\\\`"
run_sql "GRANT USE_SCHEMA, SELECT, MODIFY ON SCHEMA ${CATALOG}.${SCHEMA} TO \\\`${SP_APP_ID}\\\`"
run_sql "GRANT READ_VOLUME, WRITE_VOLUME ON VOLUME ${CATALOG}.${SCHEMA}.${VOLUME} TO \\\`${SP_APP_ID}\\\`"
echo "UC permissions granted."

# 4. Run setup job (generates data, creates tables, creates Genie Space)
echo ""
echo "--- Running setup job ---"
databricks bundle run setup_job -t "$TARGET"
echo "Setup job complete."

# 5. Grant app SP access to Genie Space
echo ""
echo "--- Granting Genie Space permissions ---"
SPACE_ID=$(python3 -c "
import json
state = json.load(open('state.json'))
print(state['space_id'])
" 2>/dev/null || echo "")

if [ -n "$SPACE_ID" ]; then
  databricks api patch "/api/2.0/permissions/genie/${SPACE_ID}" --json "{
    \"access_control_list\": [{
      \"service_principal_name\": \"${SP_APP_ID}\",
      \"permission_level\": \"CAN_MANAGE\"
    }]
  }" > /dev/null 2>&1 && echo "  Genie Space ${SPACE_ID}: OK" || echo "  WARN: Could not set Genie Space permissions"
else
  echo "  WARN: No space_id found in state.json, skipping"
fi

# 6. Start the app
echo ""
echo "--- Starting app ---"
databricks bundle run genieapp -t "$TARGET"
echo ""
echo "=== Deployment complete! ==="
