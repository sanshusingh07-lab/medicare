-- MediCare+ PostgreSQL schema
-- First create the database if it does not exist:
--   createdb -U postgres medicare
-- Then run: psql -U postgres -d medicare -f database.sql

CREATE TABLE IF NOT EXISTS users (
  user_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(120) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  age INTEGER,
  gender VARCHAR(30),
  blood_group VARCHAR(10),
  allergies TEXT,
  phone VARCHAR(30),
  photo_path VARCHAR(255),
  emergency_contact_name VARCHAR(120),
  emergency_contact_number VARCHAR(30),
  notifications_enabled BOOLEAN DEFAULT TRUE,
  voice_enabled BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS medicines (
  medicine_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  medicine_name VARCHAR(120) NOT NULL,
  medicine_type VARCHAR(30) NOT NULL,
  dosage VARCHAR(80) NOT NULL,
  frequency VARCHAR(80) NOT NULL,
  time TIME NOT NULL,
  start_date DATE,
  end_date DATE,
  meal_instruction VARCHAR(80),
  quantity INTEGER DEFAULT 0,
  refill_threshold INTEGER DEFAULT 3,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS medicine_history (
  history_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  medicine_id INTEGER NOT NULL REFERENCES medicines(medicine_id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  scheduled_time TIMESTAMP NOT NULL,
  status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'taken', 'missed', 'skipped')),
  taken_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS appointments (
  appointment_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  doctor_name VARCHAR(120) NOT NULL,
  specialization VARCHAR(120),
  appointment_date DATE NOT NULL,
  appointment_time TIME NOT NULL,
  clinic_name VARCHAR(160),
  purpose TEXT,
  notes TEXT,
  status VARCHAR(20) DEFAULT 'upcoming' CHECK (status IN ('upcoming', 'completed', 'cancelled'))
);

CREATE TABLE IF NOT EXISTS reports (
  report_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  report_name VARCHAR(160) NOT NULL,
  category VARCHAR(80) NOT NULL,
  file_path VARCHAR(255) NOT NULL,
  report_date DATE,
  doctor_hospital VARCHAR(160),
  description TEXT,
  upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prescriptions (
  prescription_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  doctor_name VARCHAR(120) NOT NULL,
  prescription_date DATE,
  clinic_name VARCHAR(160),
  file_path VARCHAR(255) NOT NULL,
  notes TEXT,
  upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS medicine_interactions (
  interaction_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  medicine_one VARCHAR(120) NOT NULL,
  medicine_two VARCHAR(120) NOT NULL,
  warning TEXT NOT NULL,
  severity VARCHAR(30) DEFAULT 'moderate'
);

CREATE TABLE IF NOT EXISTS notifications (
  notification_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  title VARCHAR(160) NOT NULL,
  message TEXT NOT NULL,
  type VARCHAR(40) DEFAULT 'info',
  is_read BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_medicines_user ON medicines(user_id);
CREATE INDEX IF NOT EXISTS idx_medicine_history_user ON medicine_history(user_id);
CREATE INDEX IF NOT EXISTS idx_appointments_user ON appointments(user_id);
CREATE INDEX IF NOT EXISTS idx_reports_user ON reports(user_id);
CREATE INDEX IF NOT EXISTS idx_prescriptions_user ON prescriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
