#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db

echo "=== 1) 找 '南岭社区' 这个社区的 id ==="
sqlite3 "$DB" "
SELECT s.name AS street, c.id, c.name
FROM communities c
LEFT JOIN streets s ON s.id = c.street_id
WHERE c.name LIKE '%南岭%';
"

echo
echo "=== 2) 该社区下所有支部 ==="
sqlite3 "$DB" "
SELECT b.id, b.name, c.name AS community
FROM branches b
JOIN communities c ON c.id = b.community_id
WHERE c.name LIKE '%南岭%'
ORDER BY b.id;
"

echo
echo "=== 3) 找 '南岭社区第一支部' (含模糊匹配) ==="
sqlite3 "$DB" "
SELECT b.id, b.name, c.name AS community
FROM branches b
JOIN communities c ON c.id = b.community_id
WHERE (b.name LIKE '%第一支部%' OR b.name LIKE '%一支部%' OR b.name LIKE '%1支部%')
  AND c.name LIKE '%南岭%'
ORDER BY b.id;
"

echo
echo "=== 4) 该支部的全部党员（含 status）==="
BRANCH_ID=$(sqlite3 "$DB" "
SELECT b.id
FROM branches b
JOIN communities c ON c.id = b.community_id
WHERE (b.name LIKE '%第一支部%' OR b.name LIKE '%一支部%' OR b.name LIKE '%1支部%')
  AND c.name LIKE '%南岭%'
LIMIT 1;
")

if [ -z "$BRANCH_ID" ]; then
  echo "未找到该支部"
else
  echo "branch_id=$BRANCH_ID"
  echo
  sqlite3 -header -column "$DB" "
SELECT id, name, phone, status, join_date, branch_id, is_mobile_member
FROM members
WHERE branch_id = $BRANCH_ID
ORDER BY id;
"
fi

echo
echo "=== 5) 当前数据库里全部 member + branch 全貌（南岭社区下）==="
sqlite3 -header -column "$DB" "
SELECT m.id, m.name, m.phone, m.status, m.branch_id, b.name AS branch
FROM members m
LEFT JOIN branches b ON b.id = m.branch_id
LEFT JOIN communities c ON c.id = b.community_id
WHERE c.name LIKE '%南岭%'
ORDER BY m.branch_id, m.id;
"
