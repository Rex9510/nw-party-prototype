select count(*) c, sum(length(photo_urls)) s
from members
where status='active' and length(photo_urls)>100;
