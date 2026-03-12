from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os
import math

app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app)

# Database config -- uses DATABASE_URL env var on Railway, falls back to local SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///cropiq.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ─── MODEL ───────────────────────────────────────────────────────────────────

class Cycle(db.Model):
    __tablename__ = 'cycles'
    id            = db.Column(db.Integer, primary_key=True)
    crop          = db.Column(db.String(100), nullable=False)
    planted_date  = db.Column(db.String(20))
    harvested_date= db.Column(db.String(20))
    days          = db.Column(db.Integer)
    bought        = db.Column(db.Integer, default=0)
    planted       = db.Column(db.Integer, default=0)
    died          = db.Column(db.Integer, default=0)
    harvested     = db.Column(db.Integer, default=0)
    sold          = db.Column(db.Integer, default=0)
    donated       = db.Column(db.Integer, default=0)
    logged_at     = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':             self.id,
            'crop':           self.crop,
            'planted_date':   self.planted_date,
            'harvested_date': self.harvested_date,
            'days':           self.days,
            'bought':         self.bought,
            'planted':        self.planted,
            'died':           self.died,
            'harvested':      self.harvested,
            'sold':           self.sold,
            'donated':        self.donated,
            'logged_at':      self.logged_at.isoformat()
        }

# ─── ALGORITHM ───────────────────────────────────────────────────────────────

def ema(values, alpha=0.6):
    """Exponential moving average -- weights recent cycles more heavily."""
    if not values:
        return 0
    result = values[0]
    for v in values[1:]:
        result = alpha * v + (1 - alpha) * result
    return result

def compute_stats(crop_cycles):
    n = len(crop_cycles)

    sell_throughs  = [c.sold / c.harvested if c.harvested > 0 else 0 for c in crop_cycles]
    mortality_rates= [c.died / c.planted   if c.planted   > 0 else 0 for c in crop_cycles]
    yield_rates    = [c.harvested / c.planted if c.planted > 0 else 0 for c in crop_cycles]
    sold_vals      = [c.sold for c in crop_cycles]
    days_vals      = [c.days for c in crop_cycles if c.days]

    sell_through  = ema(sell_throughs)
    mortality     = ema(mortality_rates)
    yield_rate    = ema(yield_rates)
    avg_sold      = ema(sold_vals)
    avg_days      = round(sum(days_vals) / len(days_vals)) if days_vals else None

    safe_yield   = yield_rate if yield_rate > 0 else 0.5
    recommended  = math.ceil(avg_sold / safe_yield)

    confidence = 'high' if n >= 4 else 'medium' if n >= 2 else 'low'

    warnings = []
    if sell_through < 0.5:
        warnings.append('High donation rate — consider reducing planting target')
    if mortality > 0.3:
        warnings.append('High plant mortality — improve conditions or add buffer')
    if n < 3:
        warnings.append('Log more cycles for higher accuracy')

    return {
        'cycles':        n,
        'sell_through':  round(sell_through, 4),
        'mortality_rate':round(mortality, 4),
        'yield_rate':    round(yield_rate, 4),
        'avg_sold':      round(avg_sold, 1),
        'avg_cycle_days':avg_days,
        'recommended':   recommended,
        'confidence':    confidence,
        'warnings':      warnings
    }

# ─── ROUTES ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('frontend', 'index.html', max_age=0)

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('frontend', path)

@app.route('/api/cycles', methods=['GET'])
def get_cycles():
    cycles = Cycle.query.order_by(Cycle.logged_at.desc()).all()
    return jsonify([c.to_dict() for c in cycles])

@app.route('/api/cycles', methods=['POST'])
def add_cycle():
    d = request.get_json()
    planted_date   = d.get('planted_date')
    harvested_date = d.get('harvested_date')

    days = None
    if planted_date and harvested_date:
        try:
            p = datetime.strptime(planted_date, '%Y-%m-%d')
            h = datetime.strptime(harvested_date, '%Y-%m-%d')
            days = (h - p).days
        except:
            pass

    cycle = Cycle(
        crop           = d.get('crop', '').strip(),
        planted_date   = planted_date,
        harvested_date = harvested_date,
        days           = days,
        bought         = int(d.get('bought', 0)),
        planted        = int(d.get('planted', 0)),
        died           = int(d.get('died', 0)),
        harvested      = int(d.get('harvested', 0)),
        sold           = int(d.get('sold', 0)),
        donated        = int(d.get('donated', 0))
    )
    db.session.add(cycle)
    db.session.commit()
    return jsonify(cycle.to_dict()), 201

@app.route('/api/cycles/<int:cycle_id>', methods=['DELETE'])
def delete_cycle(cycle_id):
    cycle = Cycle.query.get_or_404(cycle_id)
    db.session.delete(cycle)
    db.session.commit()
    return jsonify({'deleted': cycle_id})

@app.route('/api/recommendations', methods=['GET'])
def get_recommendations():
    all_cycles = Cycle.query.order_by(Cycle.logged_at.asc()).all()
    crop_map = {}
    for c in all_cycles:
        crop_map.setdefault(c.crop, []).append(c)
    results = {}
    for crop, cycles in crop_map.items():
        results[crop] = compute_stats(cycles)
    return jsonify(results)

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    all_cycles = Cycle.query.all()
    total_sold    = sum(c.sold    for c in all_cycles)
    total_donated = sum(c.donated for c in all_cycles)
    unique_crops  = len(set(c.crop for c in all_cycles))
    crop_map = {}
    for c in all_cycles:
        crop_map.setdefault(c.crop, []).append(c)
    crop_stats = {crop: compute_stats(cycs) for crop, cycs in crop_map.items()}
    return jsonify({
        'total_cycles':  len(all_cycles),
        'unique_crops':  unique_crops,
        'total_sold':    total_sold,
        'total_donated': total_donated,
        'crop_stats':    crop_stats
    })

# ─── INIT ────────────────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)