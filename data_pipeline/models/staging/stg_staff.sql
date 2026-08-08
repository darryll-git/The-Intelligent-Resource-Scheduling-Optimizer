with raw_staff as (
    select * from {{ source('public', 'dim_staff') }}
)
select
    staff_id,
    first_name,
    last_name,
    is_active,
    created_at
from raw_staff
