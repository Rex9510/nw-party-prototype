select count(*) total,
       sum(case when org_level='branch' then 1 else 0 end) branch_lvl,
       sum(case when org_level='community' then 1 else 0 end) comm_lvl,
       sum(case when org_level='street' then 1 else 0 end) street_lvl,
       sum(case when community_id is not null then 1 else 0 end) has_comm,
       sum(case when street_id is not null then 1 else 0 end) has_street
from members;
