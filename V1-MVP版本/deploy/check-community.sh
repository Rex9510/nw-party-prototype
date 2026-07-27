#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
echo "--- 南岭社区 现状 ---"
sqlite3 -header -column "$DB" "SELECT id, name, street_id FROM communities WHERE name LIKE '%南岭%';"
echo
echo "--- 该社区下的支部 ---"
sqlite3 -header -column "$DB" "SELECT id, name, community_id FROM branches WHERE community_id IN (SELECT id FROM communities WHERE name LIKE '%南岭%');"
echo
echo "--- 该社区下支部的成员（不论 status）---"
sqlite3 -header -column "$DB" "
SELECT m.id, m.name, m.status, m.branch_id, b.name AS branch
FROM members m
LEFT JOIN branches b ON b.id = m.branch_id
WHERE b.community_id IN (SELECT id FROM communities WHERE name LIKE '%南岭%')
ORDER BY m.branch_id, m.id;
"
echo
echo "--- 该社区下支部的 users ---"
sqlite3 -header -column "$DB" "
SELECT u.id, u.phone, u.name, u.role, u.branch_id
FROM users u
WHERE u.branch_id IN (SELECT id FROM branches WHERE community_id IN (SELECT id FROM communities WHERE name LIKE '%南岭%'));
"
echo
echo "--- 该社区下的活动（不论 status）---"
sqlite3 -header -column "$DB" "
SELECT a.id, a.theme, a.organizer_branch_id, a.status
FROM activities a
WHERE a.community_id IN (SELECT id FROM communities WHERE name LIKE '%南岭%');
"
