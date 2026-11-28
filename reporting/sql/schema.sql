PRAGMA foreign_keys = ON;

CREATE TABLE dim_doctor (
    doctor_id INTEGER PRIMARY KEY,
    doctor_name TEXT NOT NULL UNIQUE,
    department TEXT NOT NULL
);

CREATE TABLE dim_date (
    date_key TEXT PRIMARY KEY NOT NULL,
    year INTEGER NOT NULL,
    month_number INTEGER NOT NULL
        CHECK (month_number BETWEEN 1 AND 12),
    month_name TEXT NOT NULL,
    quarter TEXT NOT NULL
        CHECK (quarter IN ('Q1', 'Q2', 'Q3', 'Q4')),
    day_of_week TEXT NOT NULL,
    is_weekend INTEGER NOT NULL
        CHECK (is_weekend IN (0, 1))
);

CREATE TABLE dim_time (
    time_key TEXT PRIMARY KEY NOT NULL,
    hour INTEGER NOT NULL
        CHECK (hour BETWEEN 9 AND 17),
    minute INTEGER NOT NULL
        CHECK (minute IN (0, 30)),
    time_slot TEXT NOT NULL
        CHECK (
            time_slot IN (
                'Morning',
                'Afternoon',
                'Evening'
            )
        )
);

CREATE TABLE fact_appointments (
    appointment_id TEXT PRIMARY KEY NOT NULL,

    doctor_id INTEGER NOT NULL,

    appointment_date TEXT NOT NULL
        CHECK (
            appointment_date BETWEEN
            '2025-01-01' AND '2025-12-31'
        ),

    booking_date TEXT NOT NULL,

    appointment_time TEXT NOT NULL,

    status TEXT NOT NULL
        CHECK (status IN ('Booked', 'Cancelled')),

    lead_time_days INTEGER NOT NULL
        CHECK (lead_time_days BETWEEN 0 AND 30),

    CHECK (booking_date <= appointment_date),

    CHECK (
        julianday(appointment_date) IS NOT NULL
        AND julianday(booking_date) IS NOT NULL
        AND julianday(appointment_date)
            - julianday(booking_date) = lead_time_days
    ),

    FOREIGN KEY (doctor_id)
        REFERENCES dim_doctor(doctor_id),

    FOREIGN KEY (appointment_date)
        REFERENCES dim_date(date_key),

    FOREIGN KEY (booking_date)
        REFERENCES dim_date(date_key),

    FOREIGN KEY (appointment_time)
        REFERENCES dim_time(time_key)
);

CREATE UNIQUE INDEX uq_fact_active_slot
ON fact_appointments (
    doctor_id,
    appointment_date,
    appointment_time
)
WHERE status = 'Booked';
