select id, name, length(photo_urls) plen, length(identities) ilen, length(roles) rlen, branch_id
from members
where status='active' and id between 80 and 105
order by id;
