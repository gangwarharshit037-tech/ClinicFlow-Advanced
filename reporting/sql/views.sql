CREATE VIEW IF NOT EXISTS vw_appointments AS
SELECT
    f.appointment_id,
    f.appointment_date,
    f.appointment_time,
    d.doctor_name AS doctor,
    d.department,
    f.status,
    f.booking_date,
    f.lead_time_days,
    dt.year,
    dt.month_number,
    dt.month_name,
    dt.quarter,
    dt.day_of_week,
    dt.is_weekend,
    t.time_slot
FROM fact_appointments AS f
JOIN dim_doctor AS d
    ON f.doctor_id = d.doctor_id
JOIN dim_date AS dt
    ON f.appointment_date = dt.date_key
JOIN dim_time AS t
    ON f.appointment_time = t.time_key;


CREATE VIEW IF NOT EXISTS vw_daily_summary AS
SELECT
    dt.date_key AS appointment_date,
    COUNT(f.appointment_id) AS total_appointments,
    SUM(CASE WHEN f.status = 'Booked'
        THEN 1 ELSE 0 END) AS booked,
    SUM(CASE WHEN f.status = 'Cancelled'
        THEN 1 ELSE 0 END) AS cancelled,
    ROUND(
        100.0 * SUM(CASE WHEN f.status = 'Cancelled'
            THEN 1 ELSE 0 END)
        / NULLIF(COUNT(f.appointment_id), 0),
        2
    ) AS cancellation_rate
FROM dim_date AS dt
LEFT JOIN fact_appointments AS f
    ON dt.date_key = f.appointment_date
WHERE dt.year = 2025
GROUP BY dt.date_key;


CREATE VIEW IF NOT EXISTS vw_monthly_summary AS
SELECT
    year,
    month_number,
    month_name,
    COUNT(*) AS total_appointments,
    SUM(CASE WHEN status = 'Booked'
        THEN 1 ELSE 0 END) AS booked,
    SUM(CASE WHEN status = 'Cancelled'
        THEN 1 ELSE 0 END) AS cancelled,
    ROUND(
        100.0 * SUM(CASE WHEN status = 'Cancelled'
            THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        2
    ) AS cancellation_rate,
    ROUND(AVG(lead_time_days), 2)
        AS avg_lead_time_days
FROM vw_appointments
GROUP BY year, month_number, month_name;


CREATE VIEW IF NOT EXISTS vw_doctor_summary AS
SELECT
    doctor,
    department,
    COUNT(*) AS total_appointments,
    SUM(CASE WHEN status = 'Booked'
        THEN 1 ELSE 0 END) AS booked,
    SUM(CASE WHEN status = 'Cancelled'
        THEN 1 ELSE 0 END) AS cancelled,
    ROUND(
        100.0 * SUM(CASE WHEN status = 'Cancelled'
            THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        2
    ) AS cancellation_rate,
    ROUND(AVG(lead_time_days), 2)
        AS avg_lead_time_days
FROM vw_appointments
GROUP BY doctor, department;


CREATE VIEW IF NOT EXISTS vw_time_summary AS
SELECT
    appointment_time,
    time_slot,
    COUNT(*) AS total_appointments,
    SUM(CASE WHEN status = 'Booked'
        THEN 1 ELSE 0 END) AS booked,
    SUM(CASE WHEN status = 'Cancelled'
        THEN 1 ELSE 0 END) AS cancelled
FROM vw_appointments
GROUP BY appointment_time, time_slot;


CREATE VIEW IF NOT EXISTS vw_lead_time_summary AS
SELECT
    CASE
        WHEN lead_time_days = 0 THEN 'Same Day'
        WHEN lead_time_days <= 7 THEN '1-7 Days'
        WHEN lead_time_days <= 14 THEN '8-14 Days'
        WHEN lead_time_days <= 21 THEN '15-21 Days'
        ELSE '22-30 Days'
    END AS lead_time_group,
    CASE
        WHEN lead_time_days = 0 THEN 1
        WHEN lead_time_days <= 7 THEN 2
        WHEN lead_time_days <= 14 THEN 3
        WHEN lead_time_days <= 21 THEN 4
        ELSE 5
    END AS sort_order,
    COUNT(*) AS total_appointments,
    SUM(CASE WHEN status = 'Booked'
        THEN 1 ELSE 0 END) AS booked,
    SUM(CASE WHEN status = 'Cancelled'
        THEN 1 ELSE 0 END) AS cancelled,
    ROUND(
        100.0 * SUM(CASE WHEN status = 'Cancelled'
            THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        2
    ) AS cancellation_rate
FROM vw_appointments
GROUP BY lead_time_group, sort_order;
