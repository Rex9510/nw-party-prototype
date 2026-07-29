select id, kind, file_size, sort,
    substr(file_url, 1, 50) preview,
    length(file_url) len
from activity_attachments
where activity_id = 16
order by kind, sort;
