#!/bin/bash
# Lakebase pool soak test — 75 minutes, 60s cadence.
# Verifies the new token-refresh pool stays healthy past the real OAuth token TTL.

set -u

TOKEN=$(databricks auth token --profile vm 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
APP=https://genieapp-dev-7474655921234161.aws.databricksapps.com
LOG=/tmp/genieapp-soak.log
SUMMARY=/tmp/genieapp-soak-summary.txt
SPACE_ID="01f144169528170cab22ee3e2a5803e4"  # Coca-Cola

echo "Soak test started $(date)" | tee "$LOG"
echo "App: $APP" | tee -a "$LOG"

TOTAL=75
FAILS=0
MAX_LATENCY=0

check_chat() {
  local label=$1
  echo "--- chat spot-check ($label) ---" | tee -a "$LOG"
  local start_resp
  start_resp=$(curl -sL -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    --max-time 15 "$APP/api/chat/start" \
    -d "{\"question\":\"How many distinct product names are there?\",\"space_id\":\"$SPACE_ID\",\"ephemeral\":true}")
  local conv msg
  conv=$(echo "$start_resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('conversation_id',''))" 2>/dev/null)
  msg=$(echo "$start_resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('message_id',''))" 2>/dev/null)
  if [ -z "$conv" ] || [ -z "$msg" ]; then
    echo "    chat START failed: $start_resp" | tee -a "$LOG"
    return 1
  fi
  echo "    started conv=$conv msg=$msg" | tee -a "$LOG"
  for j in $(seq 1 30); do
    local poll
    poll=$(curl -sL -H "Authorization: Bearer $TOKEN" --max-time 10 \
      "$APP/api/chat/$conv/$msg/status?space_id=$SPACE_ID")
    if echo "$poll" | grep -q '"is_complete":true'; then break; fi
    sleep 2
  done
  local result_code result_body
  result_body=$(curl -sL -w "\n__HTTP__:%{http_code}" -H "Authorization: Bearer $TOKEN" --max-time 30 \
    "$APP/api/chat/$conv/$msg/result?space_id=$SPACE_ID")
  result_code=$(echo "$result_body" | grep -oE '__HTTP__:[0-9]+' | cut -d: -f2)
  if [ "$result_code" = "200" ]; then
    local rows
    rows=$(echo "$result_body" | sed '/__HTTP__/d' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('row_count',0))" 2>/dev/null)
    echo "    chat RESULT 200 rows=$rows" | tee -a "$LOG"
    return 0
  else
    echo "    chat RESULT FAILED code=$result_code" | tee -a "$LOG"
    return 1
  fi
}

for i in $(seq 1 $TOTAL); do
  TS=$(date +%H:%M:%S)
  H=$(curl -sL -w '%{http_code}|%{time_total}' -o /dev/null -H "Authorization: Bearer $TOKEN" --max-time 10 "$APP/api/users/me")
  H_CODE=${H%%|*}
  H_TIME=${H##*|}
  S_CODE=$(curl -sL -w '%{http_code}' -o /dev/null -H "Authorization: Bearer $TOKEN" --max-time 10 "$APP/api/spaces")
  S_COUNT=$(curl -sL -H "Authorization: Bearer $TOKEN" --max-time 10 "$APP/api/spaces" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else 0)" 2>/dev/null)
  C_CODE=$(curl -sL -w '%{http_code}' -o /dev/null -H "Authorization: Bearer $TOKEN" --max-time 10 "$APP/api/conversations")
  STATUS="OK"
  if [ "$H_CODE" != "200" ] || [ "$S_CODE" != "200" ] || [ "$C_CODE" != "200" ] || [ "$S_COUNT" -le 1 ]; then
    STATUS="FAIL"
    FAILS=$((FAILS+1))
  fi
  echo "$TS  iter=$i/$TOTAL  users=$H_CODE/${H_TIME}s  spaces=$S_CODE(n=$S_COUNT)  convs=$C_CODE  $STATUS" | tee -a "$LOG"
  if [ "$i" = "20" ] || [ "$i" = "70" ]; then
    if ! check_chat "iter=$i"; then FAILS=$((FAILS+1)); fi
  fi
  if [ $i -lt $TOTAL ]; then sleep 60; fi
done

echo "" | tee -a "$LOG"
echo "=== SUMMARY ===" | tee -a "$LOG" "$SUMMARY"
echo "Iterations: $TOTAL" | tee -a "$LOG" "$SUMMARY"
echo "Failures:   $FAILS" | tee -a "$LOG" "$SUMMARY"
echo "Finished:   $(date)" | tee -a "$LOG" "$SUMMARY"
if [ $FAILS -eq 0 ]; then
  echo "RESULT: PASS — pool survived full token TTL window" | tee -a "$LOG" "$SUMMARY"
  exit 0
else
  echo "RESULT: FAIL — $FAILS failed iterations, see $LOG" | tee -a "$LOG" "$SUMMARY"
  exit 1
fi
