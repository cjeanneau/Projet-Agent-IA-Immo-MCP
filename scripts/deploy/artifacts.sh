#!/bin/bash
# scripts/upload_data.sh
SERVER="${1:?Usage: $0 user@host}"

ssh "$SERVER" "mkdir -p ~/immo-mcp/data ~/immo-mcp/model/deploy"
scp data/bpe_insee.duckdb "$SERVER:~/immo-mcp/data/"
scp model/deploy/best_model3.pkl "$SERVER:~/immo-mcp/model/deploy/"
echo "Done."