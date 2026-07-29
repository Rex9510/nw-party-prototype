select id, kind, length(file_url) orig, length(thumbnail_url) thumb
from activity_attachments
where kind='photo';
