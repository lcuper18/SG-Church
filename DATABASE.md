# Esquema de Base de Datos - SG Church

Este documento detalla el esquema completo de la base de datos PostgreSQL, incluyendo tablas, relaciones, índices y estrategias de optimización.

## Tabla de Contenidos

- [Estrategia Multi-Tenant](#estrategia-multi-tenant)
- [Schema Público](#schema-público)
- [Schema Per-Tenant](#schema-per-tenant)
- [Diagrama ER](#diagrama-er)
- [Índices y Optimizaciones](#índices-y-optimizaciones)
- [Migraciones](#migraciones)
- [Backup y Recuperación](#backup-y-recuperación)

---

## Estrategia Multi-Tenant

### Schema Isolation

Cada iglesia (tenant) obtiene su propio schema PostgreSQL:

```sql
-- Schema público: datos compartidos entre todos los tenants
CREATE SCHEMA public;

-- Schemas específicos por tenant (uno por iglesia)
CREATE SCHEMA church_abc123;
CREATE SCHEMA church_xyz789;
CREATE SCHEMA church_def456;
```

**Ventajas**:
- ✅ Aislamiento fuerte de datos
- ✅ Backups individuales por iglesia
- ✅ Posibilidad de migrar iglesias grandes a DB dedicada
- ✅ Queries más simples (no necesita filtrar por tenant_id en cada query)

**Consideraciones**:
- ⚠️ Migraciones deben aplicarse a todos los schemas
- ⚠️ Límite de ~1000 schemas por instancia PostgreSQL

### Tenant Context

```sql
-- Al inicio de cada request/transacción:
SET search_path TO church_abc123, public;

-- Todas las queries subsecuentes operan en ese schema
SELECT * FROM members; -- Automáticamente busca en church_abc123.members
```

---

## Schema Público

Contiene datos **compartidos** entre todos los tenants.

### Tabla: `tenants`

Registro maestro de todas las iglesias en la plataforma.

```sql
CREATE TABLE public.tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  schema_name TEXT NOT NULL UNIQUE,
  subdomain TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  phone TEXT,
  
  -- Configuración
  timezone TEXT DEFAULT 'America/New_York',
  currency TEXT DEFAULT 'USD',
  locale TEXT DEFAULT 'en-US',
  
  -- Integrations
  stripe_account_id TEXT UNIQUE,
  stripe_onboarding_completed BOOLEAN DEFAULT FALSE,
  
  -- Settings (JSONB for flexibility)
  settings JSONB DEFAULT '{}'::jsonb,
  
  -- Feature flags
  enabled_modules TEXT[] DEFAULT ARRAY['members', 'finance', 'donations'],
  
  -- Status
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'cancelled')),
  trial_ends_at TIMESTAMPTZ,
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  
  -- Constraints
  CONSTRAINT valid_subdomain CHECK (subdomain ~* '^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$')
);

-- Indexes
CREATE INDEX idx_tenants_subdomain ON public.tenants(subdomain);
CREATE INDEX idx_tenants_status ON public.tenants(status) WHERE status = 'active';

-- Trigger para updated_at
CREATE TRIGGER update_tenants_updated_at
  BEFORE UPDATE ON public.tenants
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();
```

**Ejemplo de `settings` JSONB**:
```json
{
  "fiscalYearStart": "2026-01-01",
  "serviceTimes": ["Sunday 9:00 AM", "Sunday 11:00 AM"],
  "emailSignature": "Blessings,\nFirst Baptist Church",
  "logoUrl": "https://...",
  "primaryColor": "#4F46E5",
  "features": {
    "smsEnabled": false,
    "recurringDonations": true
  }
}
```

### Tabla: `platform_users` (Super Admins)

Usuarios que administran la plataforma (no pertenecen a ningún tenant específico).

```sql
CREATE TABLE public.platform_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  name TEXT NOT NULL,
  role TEXT DEFAULT 'support' CHECK (role IN ('super_admin', 'support', 'developer')),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Schema Per-Tenant

Cada uno de estos modelos se replica en **cada schema de tenant** (`church_abc123`, `church_xyz789`, etc.).

### 👥 Módulo de Membresía

#### Tabla: `users`

Cuentas de usuario para acceder al sistema.

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT, -- NULL si usa OAuth únicamente
  name TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'MEMBER' 
    CHECK (role IN ('CHURCH_ADMIN', 'PASTOR', 'TREASURER', 'TEACHER', 'VOLUNTEER', 'MEMBER', 'GUEST')),
  
  -- Relación con miembro (puede ser NULL si es usuario sin perfil de miembro)
  member_id UUID UNIQUE REFERENCES members(id) ON DELETE SET NULL,
  
  -- OAuth
  oauth_provider TEXT, -- 'google', 'facebook', etc.
  oauth_provider_id TEXT,
  
  -- Status
  email_verified BOOLEAN DEFAULT FALSE,
  active BOOLEAN DEFAULT TRUE,
  last_login_at TIMESTAMPTZ,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_member_id ON users(member_id);
CREATE UNIQUE INDEX idx_users_oauth ON users(oauth_provider, oauth_provider_id) 
  WHERE oauth_provider IS NOT NULL;
```

#### Tabla: `members`

Perfiles de miembros de la iglesia.

```sql
CREATE TABLE members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Basic info
  first_name TEXT NOT NULL,
  middle_name TEXT,
  last_name TEXT NOT NULL,
  preferred_name TEXT, -- "Bob" instead of "Robert"
  
  -- Contact
  email TEXT,
  phone TEXT,
  phone_mobile TEXT,
  
  -- Demographics
  date_of_birth DATE,
  gender TEXT CHECK (gender IN ('male', 'female', 'other', 'prefer_not_to_say')),
  marital_status TEXT CHECK (marital_status IN ('single', 'married', 'divorced', 'widowed')),
  
  -- Address
  address_line1 TEXT,
  address_line2 TEXT,
  city TEXT,
  state TEXT,
  zip TEXT,
  country TEXT DEFAULT 'US',
  
  -- Family
  family_id UUID REFERENCES families(id) ON DELETE SET NULL,
  family_role TEXT CHECK (family_role IN ('head', 'spouse', 'child', 'other')),
  
  -- Church info
  member_status TEXT DEFAULT 'active' 
    CHECK (member_status IN ('visitor', 'attendee', 'member', 'inactive', 'deceased')),
  membership_date DATE,
  baptized BOOLEAN DEFAULT FALSE,
  
  -- Media
  photo_url TEXT,
  
  -- Custom fields (flexible storage)
  custom_fields JSONB DEFAULT '{}'::jsonb,
  
  -- Privacy
  directory_visible BOOLEAN DEFAULT TRUE, -- Show in member directory
  
  -- Notes (pastoral care)
  notes TEXT,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_members_last_name ON members(last_name, first_name);
CREATE INDEX idx_members_email ON members(email);
CREATE INDEX idx_members_phone ON members(phone);
CREATE INDEX idx_members_family ON members(family_id);
CREATE INDEX idx_members_status ON members(member_status);
CREATE INDEX idx_members_dob ON members(date_of_birth);

-- Full-text search
CREATE INDEX idx_members_search ON members USING GIN(
  to_tsvector('english', 
    coalesce(first_name, '') || ' ' || 
    coalesce(last_name, '') || ' ' || 
    coalesce(email, '')
  )
);
```

#### Tabla: `families`

Agrupación de miembros en unidades familiares.

```sql
CREATE TABLE families (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL, -- "The Smith Family"
  
  -- Primary contact (head of household)
  primary_contact_id UUID REFERENCES members(id) ON DELETE SET NULL,
  
  -- Address (shared by family, overrides individual member addresses)
  address_line1 TEXT,
  address_line2 TEXT,
  city TEXT,
  state TEXT,
  zip TEXT,
  country TEXT DEFAULT 'US',
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_families_name ON families(name);
```

#### Tabla: `member_tags`

Sistema de etiquetado flexible (grupos pequeños, ministerios, etc.).

```sql
CREATE TABLE tags (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  category TEXT, -- 'ministry', 'small_group', 'volunteer', etc.
  color TEXT DEFAULT '#6B7280',
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE member_tags (
  member_id UUID REFERENCES members(id) ON DELETE CASCADE,
  tag_id UUID REFERENCES tags(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (member_id, tag_id)
);

CREATE INDEX idx_member_tags_member ON member_tags(member_id);
CREATE INDEX idx_member_tags_tag ON member_tags(tag_id);
```

#### Tabla: `attendance`

Registro de asistencia a servicios y eventos.

```sql
CREATE TABLE attendance (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  member_id UUID REFERENCES members(id) ON DELETE CASCADE,
  event_id UUID REFERENCES events(id) ON DELETE CASCADE,
  check_in_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  check_in_method TEXT DEFAULT 'manual' 
    CHECK (check_in_method IN ('manual', 'qr_code', 'kiosk', 'app')),
  checked_in_by UUID REFERENCES users(id),
  notes TEXT,
  
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_attendance_member ON attendance(member_id, check_in_time DESC);
CREATE INDEX idx_attendance_event ON attendance(event_id);
CREATE INDEX idx_attendance_date ON attendance(check_in_time DESC);
```

---

### 💰 Módulo Financiero

#### Tabla: `accounts`

Plan de cuentas (Chart of Accounts) para contabilidad de doble entrada.

```sql
CREATE TABLE accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT NOT NULL UNIQUE, -- "1000", "2000", etc.
  name TEXT NOT NULL,
  type TEXT NOT NULL 
    CHECK (type IN ('ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE')),
  parent_account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
  
  -- Balance tracking
  balance NUMERIC(12, 2) DEFAULT 0.00,
  
  -- Classification
  is_system BOOLEAN DEFAULT FALSE, -- System accounts can't be deleted
  active BOOLEAN DEFAULT TRUE,
  
  description TEXT,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_accounts_code ON accounts(code);
CREATE INDEX idx_accounts_type ON accounts(type);
CREATE INDEX idx_accounts_parent ON accounts(parent_account_id);

-- Default accounts (created during tenant provisioning)
INSERT INTO accounts (code, name, type, is_system) VALUES
  ('1000', 'Bank Account', 'ASSET', TRUE),
  ('1100', 'Accounts Receivable', 'ASSET', TRUE),
  ('4000', 'Donation Revenue', 'REVENUE', TRUE),
  ('4100', 'Other Income', 'REVENUE', TRUE),
  ('5000', 'Salaries Expense', 'EXPENSE', TRUE),
  ('5100', 'Utilities Expense', 'EXPENSE', TRUE),
  ('5200', 'Maintenance Expense', 'EXPENSE', TRUE);
```

#### Tabla: `transactions`

Transacciones contables (doble entrada).

```sql
CREATE TABLE transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  date DATE NOT NULL DEFAULT CURRENT_DATE,
  description TEXT NOT NULL,
  reference TEXT, -- Check number, invoice number, etc.
  
  -- Auditing
  created_by UUID REFERENCES users(id) NOT NULL,
  approved_by UUID REFERENCES users(id),
  approved_at TIMESTAMPTZ,
  
  -- Status
  status TEXT DEFAULT 'pending' 
    CHECK (status IN ('pending', 'approved', 'void')),
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_transactions_date ON transactions(date DESC);
CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_transactions_created_by ON transactions(created_by);
```

#### Tabla: `transaction_lines`

Líneas de transacción (débitos y créditos).

```sql
CREATE TABLE transaction_lines (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  transaction_id UUID REFERENCES transactions(id) ON DELETE CASCADE,
  account_id UUID REFERENCES accounts(id) NOT NULL,
  
  -- Debit/Credit
  type TEXT NOT NULL CHECK (type IN ('DEBIT', 'CREDIT')),
  amount NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
  
  memo TEXT,
  
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_transaction_lines_transaction ON transaction_lines(transaction_id);
CREATE INDEX idx_transaction_lines_account ON transaction_lines(account_id);

-- Constraint: Each transaction must balance (SUM(debits) = SUM(credits))
CREATE FUNCTION check_transaction_balance() RETURNS TRIGGER AS $$
BEGIN
  IF (
    SELECT ABS(
      COALESCE(SUM(CASE WHEN type = 'DEBIT' THEN amount ELSE -amount END), 0)
    )
    FROM transaction_lines
    WHERE transaction_id = NEW.transaction_id
  ) > 0.01 THEN
    RAISE EXCEPTION 'Transaction does not balance';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER ensure_transaction_balance
  AFTER INSERT OR UPDATE ON transaction_lines
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION check_transaction_balance();
```

#### Tabla: `donations`

Donaciones recibidas.

```sql
CREATE TABLE donations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Donor
  member_id UUID REFERENCES members(id) ON DELETE SET NULL,
  donor_name TEXT, -- For anonymous/guest donations
  donor_email TEXT,
  
  -- Amount
  amount NUMERIC(10, 2) NOT NULL CHECK (amount > 0),
  currency TEXT DEFAULT 'USD',
  
  -- Type
  type TEXT DEFAULT 'one_time' 
    CHECK (type IN ('one_time', 'recurring')),
  frequency TEXT CHECK (frequency IN ('weekly', 'monthly', 'quarterly', 'annually')),
  
  -- Campaign (optional)
  campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
  
  -- Payment processing
  stripe_payment_intent_id TEXT UNIQUE,
  stripe_subscription_id TEXT,
  payment_method TEXT DEFAULT 'card' 
    CHECK (payment_method IN ('card', 'bank_transfer', 'cash', 'check', 'other')),
  check_number TEXT,
  
  -- Accounting
  transaction_id UUID REFERENCES transactions(id) UNIQUE,
  
  -- Tax receipt
  receipt_emailed BOOLEAN DEFAULT FALSE,
  receipt_emailed_at TIMESTAMPTZ,
  tax_deductible BOOLEAN DEFAULT TRUE,
  
  -- Status
  status TEXT DEFAULT 'completed' 
    CHECK (status IN ('pending', 'completed', 'failed', 'refunded')),
  
  notes TEXT,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_donations_member ON donations(member_id, created_at DESC);
CREATE INDEX idx_donations_date ON donations(created_at DESC);
CREATE INDEX idx_donations_campaign ON donations(campaign_id);
CREATE INDEX idx_donations_stripe_payment ON donations(stripe_payment_intent_id);
CREATE INDEX idx_donations_status ON donations(status);

-- Index for annual giving statements
CREATE INDEX idx_donations_annual ON donations(
  member_id, 
  EXTRACT(YEAR FROM created_at), 
  status
) WHERE status = 'completed';
```

#### Tabla: `campaigns`

Campañas de fundraising.

```sql
CREATE TABLE campaigns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  goal_amount NUMERIC(12, 2),
  start_date DATE,
  end_date DATE,
  active BOOLEAN DEFAULT TRUE,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_campaigns_active ON campaigns(active, end_date);
```

#### Tabla: `budgets`

Presupuestos anuales.

```sql
CREATE TABLE budgets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  fiscal_year INTEGER NOT NULL,
  account_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
  amount NUMERIC(12, 2) NOT NULL,
  
  notes TEXT,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE(fiscal_year, account_id)
);

CREATE INDEX idx_budgets_year ON budgets(fiscal_year);
CREATE INDEX idx_budgets_account ON budgets(account_id);
```

---

### 🎓 Módulo de Educación (LMS)

#### Tabla: `courses`

Cursos de estudio.

```sql
CREATE TABLE courses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  description TEXT,
  instructor_id UUID REFERENCES users(id) ON DELETE SET NULL,
  
  -- Content
  thumbnail_url TEXT,
  syllabus TEXT,
  
  -- Settings
  published BOOLEAN DEFAULT FALSE,
  enrollment_limit INTEGER,
  auto_enroll BOOLEAN DEFAULT FALSE, -- Auto-enroll all members
  
  -- Completion
  certificate_template_url TEXT,
  passing_score INTEGER DEFAULT 70, -- Percentage
  
  -- Ordering
  sort_order INTEGER DEFAULT 0,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_courses_instructor ON courses(instructor_id);
CREATE INDEX idx_courses_published ON courses(published, sort_order);
```

#### Tabla: `lessons`

Lecciones dentro de cursos.

```sql
CREATE TABLE lessons (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
  
  title TEXT NOT NULL,
  content TEXT, -- HTML/Markdown content
  
  -- Media
  video_url TEXT, -- YouTube, Vimeo, etc.
  video_duration INTEGER, -- seconds
  
  -- Files
  attachments JSONB DEFAULT '[]'::jsonb, -- [{name: "file.pdf", url: "https://..."}]
  
  -- Ordering
  sort_order INTEGER NOT NULL,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_lessons_course ON lessons(course_id, sort_order);
```

#### Tabla: `quizzes`

Evaluaciones por lección.

```sql
CREATE TABLE quizzes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lesson_id UUID REFERENCES lessons(id) ON DELETE CASCADE,
  
  title TEXT NOT NULL,
  description TEXT,
  
  -- Questions stored as JSONB
  questions JSONB NOT NULL,
  /* Format:
  [
    {
      "id": "q1",
      "type": "multiple_choice",
      "question": "What is 2+2?",
      "options": ["3", "4", "5"],
      "correct_answer": 1,
      "points": 10
    },
    {
      "id": "q2",
      "type": "true_false",
      "question": "The sky is blue",
      "correct_answer": true,
      "points": 5
    }
  ]
  */
  
  passing_score INTEGER DEFAULT 70,
  time_limit INTEGER, -- minutes (NULL = no limit)
  
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_quizzes_lesson ON quizzes(lesson_id);
```

#### Tabla: `course_enrollments`

Inscripciones de estudiantes en cursos.

```sql
CREATE TABLE course_enrollments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
  member_id UUID REFERENCES members(id) ON DELETE CASCADE,
  
  -- Progress
  progress INTEGER DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
  completed BOOLEAN DEFAULT FALSE,
  
  -- Completion
  enrolled_at TIMESTAMPTZ DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  
  -- Certificate
  certificate_issued BOOLEAN DEFAULT FALSE,
  certificate_url TEXT,
  
  UNIQUE(course_id, member_id)
);

CREATE INDEX idx_enrollments_course ON course_enrollments(course_id);
CREATE INDEX idx_enrollments_member ON course_enrollments(member_id);
CREATE INDEX idx_enrollments_completed ON course_enrollments(completed, completed_at);
```

#### Tabla: `lesson_progress`

Progreso por lección.

```sql
CREATE TABLE lesson_progress (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  enrollment_id UUID REFERENCES course_enrollments(id) ON DELETE CASCADE,
  lesson_id UUID REFERENCES lessons(id) ON DELETE CASCADE,
  
  completed BOOLEAN DEFAULT FALSE,
  completed_at TIMESTAMPTZ,
  
  -- Video tracking
  video_progress INTEGER DEFAULT 0, -- seconds watched
  
  UNIQUE(enrollment_id, lesson_id)
);

CREATE INDEX idx_lesson_progress_enrollment ON lesson_progress(enrollment_id);
```

#### Tabla: `quiz_attempts`

Intentos de quiz por estudiantes.

```sql
CREATE TABLE quiz_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  quiz_id UUID REFERENCES quizzes(id) ON DELETE CASCADE,
  enrollment_id UUID REFERENCES course_enrollments(id) ON DELETE CASCADE,
  
  -- Answers (stored as JSONB)
  answers JSONB NOT NULL,
  /* Format:
  {
    "q1": 1,  // Selected option index
    "q2": true
  }
  */
  
  -- Results
  score INTEGER NOT NULL, -- Percentage
  passed BOOLEAN NOT NULL,
  
  -- Timing
  started_at TIMESTAMPTZ DEFAULT NOW(),
  submitted_at TIMESTAMPTZ DEFAULT NOW(),
  time_taken INTEGER -- seconds
);

CREATE INDEX idx_quiz_attempts_quiz ON quiz_attempts(quiz_id);
CREATE INDEX idx_quiz_attempts_enrollment ON quiz_attempts(enrollment_id);
```

#### Tabla: `learning_paths`

Rutas de aprendizaje (secuencias de cursos).

```sql
CREATE TABLE learning_paths (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  published BOOLEAN DEFAULT FALSE,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE learning_path_courses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  learning_path_id UUID REFERENCES learning_paths(id) ON DELETE CASCADE,
  course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
  
  sort_order INTEGER NOT NULL,
  prerequisite_course_id UUID REFERENCES courses(id) ON DELETE SET NULL,
  
  UNIQUE(learning_path_id, course_id)
);

CREATE INDEX idx_lp_courses_path ON learning_path_courses(learning_path_id, sort_order);
```

---

### ⛪ Módulo Sacramental

#### Tabla: `baptisms`

Registros de bautizos.

```sql
CREATE TABLE baptisms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  member_id UUID REFERENCES members(id) ON DELETE CASCADE UNIQUE,
  
  -- Event details
  date DATE NOT NULL,
  location TEXT,
  officiant TEXT, -- Pastor name
  
  -- Witnesses
  witnesses TEXT[], -- Array of witness names
  
  -- Certificate
  certificate_generated BOOLEAN DEFAULT FALSE,
  certificate_url TEXT,
  
  -- Photos
  photo_urls TEXT[], -- Array of photo URLs
  
  notes TEXT,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_baptisms_member ON baptisms(member_id);
CREATE INDEX idx_baptisms_date ON baptisms(date DESC);
```

#### Tabla: `sacraments` (Confirmaciones, Matrimonios, etc.)

```sql
CREATE TABLE sacraments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  type TEXT NOT NULL 
    CHECK (type IN ('confirmation', 'marriage', 'communion', 'ordination', 'other')),
  
  -- Participants (flexible for different sacrament types)
  member_ids UUID[], -- Array of member UUIDs
  
  date DATE NOT NULL,
  location TEXT,
  officiant TEXT,
  witnesses TEXT[],
  
  -- Documents
  certificate_url TEXT,
  photo_urls TEXT[],
  
  notes TEXT,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sacraments_type ON sacraments(type, date DESC);
CREATE INDEX idx_sacraments_date ON sacraments(date DESC);
CREATE INDEX idx_sacraments_members ON sacraments USING GIN(member_ids);
```

---

### 📅 Módulo de Eventos

#### Tabla: `events`

Servicios, eventos, reuniones.

```sql
CREATE TABLE events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  title TEXT NOT NULL,
  description TEXT,
  
  -- Type
  type TEXT DEFAULT 'service' 
    CHECK (type IN ('service', 'meeting', 'social', 'class', 'other')),
  
  -- Date/Time
  start_time TIMESTAMPTZ NOT NULL,
  end_time TIMESTAMPTZ NOT NULL,
  all_day BOOLEAN DEFAULT FALSE,
  
  -- Location
  location TEXT,
  
  -- Recurrence
  recurring BOOLEAN DEFAULT FALSE,
  recurrence_rule TEXT, -- iCal RRULE format
  parent_event_id UUID REFERENCES events(id) ON DELETE CASCADE,
  
  -- Registration
  registration_enabled BOOLEAN DEFAULT FALSE,
  registration_limit INTEGER,
  registration_deadline TIMESTAMPTZ,
  
  -- Visibility
  public BOOLEAN DEFAULT FALSE,
  
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_events_start_time ON events(start_time DESC);
CREATE INDEX idx_events_type ON events(type, start_time);
CREATE INDEX idx_events_public ON events(public) WHERE public = TRUE;
```

#### Tabla: `event_registrations`

Registro de miembros a eventos.

```sql
CREATE TABLE event_registrations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id UUID REFERENCES events(id) ON DELETE CASCADE,
  member_id UUID REFERENCES members(id) ON DELETE CASCADE,
  
  status TEXT DEFAULT 'registered' 
    CHECK (status IN ('registered', 'attended', 'cancelled', 'no_show')),
  
  registered_at TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE(event_id, member_id)
);

CREATE INDEX idx_event_reg_event ON event_registrations(event_id);
CREATE INDEX idx_event_reg_member ON event_registrations(member_id);
```

---

### 🔔 Módulo de Comunicaciones

#### Tabla: `email_logs`

Log de emails enviados.

```sql
CREATE TABLE email_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  recipient_email TEXT NOT NULL,
  recipient_member_id UUID REFERENCES members(id) ON DELETE SET NULL,
  
  subject TEXT NOT NULL,
  template TEXT, -- Template name
  
  -- Delivery
  status TEXT DEFAULT 'queued' 
    CHECK (status IN ('queued', 'sent', 'delivered', 'failed', 'bounced')),
  external_id TEXT, -- Resend/SendGrid message ID
  
  -- Tracking
  opened BOOLEAN DEFAULT FALSE,
  opened_at TIMESTAMPTZ,
  clicked BOOLEAN DEFAULT FALSE,
  clicked_at TIMESTAMPTZ,
  
  -- Errors
  error_message TEXT,
  
  sent_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_email_logs_recipient ON email_logs(recipient_email);
CREATE INDEX idx_email_logs_member ON email_logs(recipient_member_id);
CREATE INDEX idx_email_logs_status ON email_logs(status, sent_at DESC);
```

#### Tabla: `sms_logs`

Log de SMS enviados.

```sql
CREATE TABLE sms_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  recipient_phone TEXT NOT NULL,
  recipient_member_id UUID REFERENCES members(id) ON DELETE SET NULL,
  
  message TEXT NOT NULL,
  
  -- Delivery
  status TEXT DEFAULT 'queued' 
    CHECK (status IN ('queued', 'sent', 'delivered', 'failed')),
  external_id TEXT, -- Twilio message SID
  
  error_message TEXT,
  
  sent_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sms_logs_recipient ON sms_logs(recipient_phone);
CREATE INDEX idx_sms_logs_member ON sms_logs(recipient_member_id);
```

---

### 📝 Auditoría y Logs

#### Tabla: `audit_logs`

Registro de todas las acciones críticas.

```sql
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Who
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  user_email TEXT,
  
  -- What
  action TEXT NOT NULL, -- 'CREATE', 'UPDATE', 'DELETE'
  entity TEXT NOT NULL, -- 'Member', 'Donation', 'Transaction'
  entity_id UUID,
  
  -- Changes (JSON snapshot)
  old_values JSONB,
  new_values JSONB,
  
  -- Context
  ip_address INET,
  user_agent TEXT,
  
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_entity ON audit_logs(entity, entity_id, created_at DESC);
CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);

-- Partition by month for performance (optional, for high-volume)
-- CREATE TABLE audit_logs_2026_01 PARTITION OF audit_logs
--   FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
```

---

## Diagrama ER

```
┌──────────┐         ┌──────────┐
│ TENANTS  │         │ PLATFORM │
│ (public) │         │  USERS   │
└──────────┘         └──────────┘
     │
     │ has many (via schema_name)
     │
     ▼
┌────────────────────────────────────────────────┐
│           PER-TENANT SCHEMA                    │
├────────────────────────────────────────────────┤
│                                                │
│  ┌──────┐    ┌─────────┐    ┌──────────┐     │
│  │USERS │───▶│ MEMBERS │◀───│ FAMILIES │     │
│  └──────┘    └────┬────┘    └──────────┘     │
│                   │                            │
│        ┌──────────┼──────────┬───────────┐    │
│        │          │          │           │    │
│        ▼          ▼          ▼           ▼    │
│   ┌─────────┐ ┌──────┐  ┌────────┐ ┌────────┐│
│   │DONATIONS│ │BAPTISMS  │ATTENDANCE COURSE  ││
│   └────┬────┘ └──────┘  └────────┘ │ENROLLM │││
│        │                            └────────┘││
│        │                                       ││
│        ▼                                       ││
│   ┌──────────────┐                            ││
│   │ TRANSACTIONS │                            ││
│   └──────┬───────┘                            ││
│          │                                     ││
│          ▼                                     ││
│   ┌───────────────┐                           ││
│   │TRANSACTION    │                           ││
│   │LINES          │                           ││
│   └───────┬───────┘                           ││
│           │                                    ││
│           ▼                                    ││
│   ┌──────────┐                                ││
│   │ ACCOUNTS │                                ││
│   └──────────┘                                ││
│                                                │
└────────────────────────────────────────────────┘
```

---

## Índices y Optimizaciones

### Estrategia de Indexación

#### 1. Índices Primarios (Ya incluidos arriba)
- Primary keys (UUID): Búsquedas directas
- Foreign keys: JOINs eficientes
- Unique constraints: Validación de unicidad

#### 2. Índices de Búsqueda
```sql
-- Búsqueda de miembros por nombre
CREATE INDEX idx_members_last_name ON members(last_name, first_name);

-- Full-text search en miembros
CREATE INDEX idx_members_fts ON members USING GIN(
  to_tsvector('english', first_name || ' ' || last_name || ' ' || coalesce(email, ''))
);

-- Búsqueda de donaciones por rango de fechas
CREATE INDEX idx_donations_date_range ON donations(created_at DESC);
```

#### 3. Índices Parciales (Partial Indexes)
```sql
-- Solo indexar miembros activos (más común en queries)
CREATE INDEX idx_members_active ON members(member_status, last_name)
  WHERE member_status IN ('member', 'attendee');

-- Solo transacciones aprobadas
CREATE INDEX idx_transactions_approved ON transactions(date DESC)
  WHERE status = 'approved';
```

#### 4. Índices Compuestos
```sql
-- Reporte de donaciones anuales por miembro
CREATE INDEX idx_donations_annual_report ON donations(
  member_id,
  EXTRACT(YEAR FROM created_at),
  created_at DESC
) WHERE status = 'completed';

-- Asistencia por miembro y fecha
CREATE INDEX idx_attendance_member_date ON attendance(
  member_id,
  check_in_time DESC
);
```

### Query Optimization Tips

#### Usar EXPLAIN ANALYZE
```sql
EXPLAIN ANALYZE
SELECT m.*, COUNT(d.id) as donation_count
FROM members m
LEFT JOIN donations d ON d.member_id = m.id
WHERE m.member_status = 'member'
GROUP BY m.id;
```

#### Evitar N+1 Queries (Use JOINs o Prisma includes)
```typescript
// BAD: N+1
const members = await db.member.findMany()
for (const member of members) {
  member.donations = await db.donation.findMany({
    where: { memberId: member.id }
  })
}

// GOOD: Single query
const members = await db.member.findMany({
  include: { donations: true }
})
```

#### Paginación con Cursor
```typescript
// Más eficiente que OFFSET para grandes datasets
const members = await db.member.findMany({
  take: 50,
  skip: 1,
  cursor: { id: lastSeenId },
  orderBy: { lastName: 'asc' }
})
```

---

## Migraciones

### Prisma Migrations

#### Crear nueva migración
```bash
pnpm db:migrate:create --name add_learning_paths
```

#### Aplicar migraciones a un schema específico
```typescript
// scripts/migrate-tenant.ts
import { execSync } from 'child_process'

async function migrateTenant(schemaName: string) {
  process.env.DATABASE_URL = `${BASE_URL}?schema=${schemaName}`
  
  execSync('pnpm prisma migrate deploy', {
    stdio: 'inherit',
    env: process.env
  })
}

// Migrar todos los tenants
const tenants = await db.tenant.findMany()
for (const tenant of tenants) {
  await migrateTenant(tenant.schemaName)
}
```

#### Rollback (Manual)
```sql
-- Prisma no tiene rollback automático
-- Crear migración manual que revierte cambios
BEGIN;
  -- Revert changes
  DROP TABLE IF EXISTS new_table CASCADE;
  -- ... más cambios
COMMIT;
```

---

## Backup y Recuperación

### Backup Automático Diario

```bash
#!/bin/bash
# scripts/backup-database.sh

DATE=$(date +%Y-%m-%d)
BACKUP_DIR="/backups"

# Backup schema público
pg_dump -h $DB_HOST -U $DB_USER -n public \
  -F c -f "$BACKUP_DIR/public_$DATE.dump"

# Backup cada tenant schema
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -t -c \
  "SELECT schema_name FROM public.tenants" | \
while read schema; do
  echo "Backing up $schema..."
  pg_dump -h $DB_HOST -U $DB_USER -n $schema \
    -F c -f "$BACKUP_DIR/${schema}_$DATE.dump"
done

# Comprimir y subir a S3
tar -czf "$BACKUP_DIR/backup_$DATE.tar.gz" $BACKUP_DIR/*.dump
aws s3 cp "$BACKUP_DIR/backup_$DATE.tar.gz" s3://sg-church-backups/

# Limpiar backups antiguos (retener 30 días)
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

### Restaurar Tenant Específico

```bash
# Restaurar solo un tenant
pg_restore -h $DB_HOST -U $DB_USER -d $DB_NAME \
  --schema=church_abc123 \
  /backups/church_abc123_2026-02-15.dump
```

### Point-in-Time Recovery (PITR)

Si usas AWS RDS o similar:
```bash
# Configurar en RDS
aws rds modify-db-instance \
  --db-instance-identifier sg-church-prod \
  --backup-retention-period 30 \
  --preferred-backup-window "03:00-04:00"

# Restaurar a punto específico
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier sg-church-prod \
  --target-db-instance-identifier sg-church-restored \
  --restore-time 2026-02-15T10:30:00Z
```

---

## Consideraciones de Performance

### Connection Pooling

```typescript
// lib/db.ts con PgBouncer
import { PrismaClient } from '@prisma/client'

const globalForPrisma = global as unknown as { prisma: PrismaClient }

export const db = globalForPrisma.prisma || new PrismaClient({
  datasources: {
    db: {
      url: process.env.DATABASE_URL + '?pgbouncer=true&connection_limit=1'
    }
  }
})

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = db
```

### Vacuum y Analyze

```sql
-- Ejecutar semanalmente (cron job)
VACUUM ANALYZE;

-- Para schema específico
VACUUM ANALYZE church_abc123.members;
```

### Monitoring Queries Lentas

```sql
-- Habilitar pg_stat_statements
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Ver queries más lentas
SELECT
  query,
  calls,
  total_exec_time,
  mean_exec_time,
  max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;
```

---

**Siguiente**: Ver [ROADMAP.md](./ROADMAP.md) para plan de implementación.
