# CropIQ

CropIQ is a full-stack farm management and yield optimization web application. Built to address real-world harvest and sales inefficiencies observed while working in harvesting and farmstand operations at the Mills Community Farm at Northeastern University Oakland, this tool was deployed and used by the farm to optimize harvest predictions, reduce crop waste, and improve sales efficiency.

---

## Features

* **Performance Dashboard:** Visualizes aggregate metrics including total cycles logged, unique crops, total units sold, and total units donated.
* **Smart Recommendations Engine:** Applies an EMA algorithm ($\alpha = 0.6$) to weighted historical data to calculate optimal planting quantities and flag operational warnings (e.g., high mortality, high donation rates).
* **Cycle Logging:** Logs crop lifecycle metrics including planting/harvest dates, seeds purchased, plants planted, mortality count, units harvested, sold, and donated.
* **Worker Sheet:** Printer-friendly operational data sheet for field workers to collect physical records before digital entry.
* **Cycle History:** Interface to inspect and delete past cycle logs with dynamic stat updates.

---

## Tech Stack

* **Frontend:** HTML5, CSS3 (Custom Variables, Flexbox, Grid), Vanilla JavaScript (Fetch API)
* **Backend:** Python, Flask, Flask-SQLAlchemy, Flask-CORS
* **Database:** SQLite (default development) / PostgreSQL supported via `DATABASE_URL`
* **Deployment:** Production-ready with `gunicorn` and `Procfile` support (Railway, Heroku)

---

## Repository Structure

```text
.
├── app.py              # Flask server, database models, and API endpoints
├── requirements.txt    # Python dependencies
├── Procfile            # Production process launch configuration
└── frontend/
    └── index.html      # Single Page Application (SPA) frontend

```

---

## Local Development Setup

### Prerequisites

* Python 3.8+
* `pip` package manager

### Installation Steps

1. Clone the repository:

```bash
git clone https://github.com/NP100m/cropiq.git
cd cropiq

```

2. Create and activate a virtual environment:

```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate

```

3. Install dependencies:

```bash
pip install -r requirements.txt

```

4. Run the development server:

```bash
python app.py

```

Access the web UI at `http://localhost:5000`.

---

## API Reference

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/dashboard` | Returns aggregate statistics and per-crop performance metrics |
| `GET` | `/api/cycles` | Returns array of all crop cycle records ordered by log date |
| `POST` | `/api/cycles` | Creates a new crop cycle log entry |
| `DELETE` | `/api/cycles/<id>` | Deletes a cycle record by ID |
| `GET` | `/api/recommendations` | Calculates target plant counts and warning flags per crop |

---

## Recommendation Logic

Target planting counts per crop are computed via Exponential Moving Average ($\alpha = 0.6$), giving higher weight to recent cycles:

$$\text{Recommended Target} = \left\lceil \frac{\text{EMA(Units Sold)}}{\text{EMA(Yield Rate)}} \right\rceil$$

### Warning Triggers

* **High Donation Rate:** Triggered when sell-through rate $< 0.50$
* **High Mortality:** Triggered when mortality rate $> 0.30$
* **Low Confidence Flag:** Triggered when total logged cycles $n < 3$
