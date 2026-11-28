CREATE INDEX IF NOT EXISTS idx_fact_appointment_date
ON fact_appointments (appointment_date);

CREATE INDEX IF NOT EXISTS idx_fact_doctor_date
ON fact_appointments (doctor_id, appointment_date);

CREATE INDEX IF NOT EXISTS idx_fact_status_date
ON fact_appointments (status, appointment_date);

CREATE INDEX IF NOT EXISTS idx_fact_booking_date
ON fact_appointments (booking_date);

CREATE INDEX IF NOT EXISTS idx_fact_appointment_time
ON fact_appointments (appointment_time);
