#!/bin/bash
# tek ilçe: prep + önhesap
cd /home/claude/evk
k=$1
{ echo "== $k prep $(date +%T)"; python3 prep2.py $k 2>&1 | grep -E "buildings|eşleşmedi|Traceback|Error" ; echo "== $k pre $(date +%T)"; node --max-old-space-size=3000 precompute2.js $k 2>&1 | grep -E "done|Error|sample"; echo "== $k END $(date +%T)"; } >> run_prov.log 2>&1
