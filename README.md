# Pazhayangadi Health Region Survey & Outbreak Surveillance Management System

An enterprise-level, production-ready Pazhayangadi Health Region Survey System built using **Django 5**, **SQLite** (for development), **Bootstrap 5**, **Chart.js**, **Pandas**, **OpenPyXL**, **ReportLab**, and **Scikit-Learn**.

The system is designed for Conducting health surveys, collecting dynamic survey responses, managing system-wide reports, analyzing disease trends, detecting outbreaks, and monitoring public health indicators in compliance with role-based access control and row-level hierarchical scoping.

---

## 🏛️ System Hierarchy

The application strictly enforces a top-down hierarchy:

```text
HQ (Headquarters)
└── Center
    └── Subcenter
        └── Survey Conductors (ASHA, JHI, JPHN, MLSP)
```

- **HQ Admin**: Has global visibility across all Centers, Subcenters, Reports, and ML alerts. Configure settings, template builders, and Centers.
- **Center Admin**: Scoped strictly to subcenters and reports under their Center jurisdiction. Cannot view other Centers.
- **Subcenter Admin**: Can create, edit, activate/deactivate, and delete custom Dynamic Form templates. Scoped to see reports under their Subcenter.
- **Survey Conductors**: Work under a Subcenter. They can view available active forms, open dynamic templates, submit household surveys, and see their own logs.

---

## 🚀 Key Modules

1. **`accounts`**: Custom user management, authentication backend, Role-Based Access Control (RBAC), and security Audit Logs.
2. **`surveys`**: Primary household survey structures (house number, ward, panchayat, members count, pregnancy status, vaccine records, blood pressure, diabetes, cancer, and other chronic details).
3. **`forms_engine`**: Completely dynamic, drag-and-drop code-free form builder engine. Enables Subcenter admins to deploy new surveys on the fly.
4. **`reports`**: Implements a unified three-tier reporting view: `Form List ➔ Submission List ➔ Submission Details`. Supports CSV, Excel, and PDF downloads.
5. **`ml_engine`**: Machine Learning estimators:
   - **Trend Forecasts**: Linear Regression predicting future case count spikes.
   - **Outbreak Detection**: Statistical Z-Score anomaly checks flagging unexpected local cluster rates.
   - **Risk Profiling**: Compiles vulnerability points based on chronic factors and age.
   - **Clustering**: K-Means clustering grouping Wards into risk categories.

---

## 🛠️ Tech Stack

- **Backend Framework**: Django 5.x, Django REST Framework (DRF)
- **Database**: SQLite (Development) / PostgreSQL (Production-ready design)
- **Frontend layout**: Bootstrap 5, FontAwesome, Google Fonts (Outfit)
- **Data Visualizations**: Chart.js
- **Exports compilation**: Pandas, OpenPyXL (Excel), ReportLab (PDF)
- **Machine Learning**: Scikit-Learn, NumPy

---

## ⚙️ Installation & Setup

### 1. Install Dependencies
Make sure you have python installed. Navigate to the project root and run:
```bash
pip install django djangorestframework pandas openpyxl reportlab scikit-learn numpy matplotlib
```

### 2. Apply Migrations
Set up database structures:
```bash
python manage.py makemigrations accounts center subcenter forms_engine surveys
python manage.py migrate
```

### 3. Seed Mock Datasets
Populate the hierarchy, users, active templates, and 25 realistic mock household cases (with diverse medical histories):
```bash
python seed_data.py
```

### 4. Run Development Server
```bash
python manage.py runserver
```
Visit [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.

---

## 🔑 Seeded Test Accounts (Password: `admin123`)

| Username | Hierarchy Level | Role | Scope Visibility |
| :--- | :--- | :--- | :--- |
| `hq_admin` | HQ (Central) | Central Admin (Superuser) | State-wide dashboards, all reports, ML zone maps, outbreak alerts. |
| `center_admin` | Center | Center Admin | Scoped to *Pazhayangadi CHC* and its child subcenters. |
| `subcenter_admin` | Subcenter | Subcenter Admin | Scoped to *Pazhayangadi North Subcenter*. Can create/edit dynamic forms. |
| `conductor_asha` | Conductor | ASHA (under Vellanad) | Fills dynamic surveys under Pazhayangadi North Subcenter. |
| `conductor_jhi` | Conductor | JHI (under Vellanad) | Fills dynamic surveys under Pazhayangadi North Subcenter. |
| `conductor_jphn` | Conductor | JPHN (under Aryanad) | Fills dynamic surveys under Pazhayangadi South Subcenter. |

---

## 🧪 Verification
You can execute automated test cases covering model checks, RBAC restrictions, dynamic form rendering, and analytics scoping:
```bash
python manage.py test
```
