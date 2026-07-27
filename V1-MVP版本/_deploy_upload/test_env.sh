#!/usr/bin/env bash
set -a
while IFS= read -r line; do
  [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
  [[ "$line" =~ ^[^=]+= ]] || continue
  export "$line"
done < /var/www/nwparty/.env
set +a

echo "After load:"
echo "  CORS_ORIGINS=[$CORS_ORIGINS]"
echo "  DATABASE_URL=[$DATABASE_URL]"
echo "  JWT_SECRET length=$(echo -n "$JWT_SECRET" | wc -c)"
echo "  UPLOAD_ALLOWED_TYPES=[$UPLOAD_ALLOWED_TYPES]"