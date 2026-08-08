with raw_shifts as (
    select * from {{ source('public', 'fact_shifts') }}
)
select
    id,
    staff_id,
    shift_date,
    shift_type,
    is_locked,
    created_at
from raw_shifts
