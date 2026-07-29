select id, name, length(photo_urls) plen, branch_id
from members
where status='active' and length(photo_urls) > 100
order by plen desc
limit 10;
