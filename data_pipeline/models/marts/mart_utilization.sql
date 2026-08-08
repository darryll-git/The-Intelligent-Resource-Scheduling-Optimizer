with staff as (
    select * from {{ ref('stg_staff') }}
),
shifts as (
    select * from {{ ref('stg_shifts') }}
)
select
    st.staff_id,
    st.first_name,
    st.last_name,
    count(sh.id) as total_shifts,
    count(case when sh.shift_type = 'Night' then 1 end) as total_night_shifts,
    -- basic utilization metrics
    count(sh.id) * 8 as total_hours_worked
from staff st
left join shifts sh on st.staff_id = sh.staff_id
group by 1, 2, 3
