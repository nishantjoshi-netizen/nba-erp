from flask import Flask, render_template, request, redirect, session
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = 'secret123'

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        role TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS marks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll INTEGER,
        CO1 REAL, CO2 REAL, CO3 REAL,
        CO4 REAL, CO5 REAL, CO6 REAL)''')

    conn.commit()
    conn.close()

init_db()

# ---------------- LOGIN ----------------
@app.route('/', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pwd = request.form['password']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (user,pwd))
        data = c.fetchone()
        conn.close()

        if data:
            session['user'] = user
            session['role'] = data[3]
            return redirect('/dashboard')
        else:
            return "Invalid Login"

    return render_template('login.html')

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    return render_template('dashboard.html')

# ---------------- UPLOAD ----------------
@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    df = pd.read_csv(file)

    conn = sqlite3.connect('database.db')
    df.to_sql('marks', conn, if_exists='replace', index=False)
    conn.close()

    return "Marks Imported Successfully"

# ---------------- CO ----------------
@app.route('/co')
def co():
    conn = sqlite3.connect('database.db')
    df = pd.read_sql("SELECT * FROM marks", conn)
    conn.close()

    if df.empty:
        return "No data available. Upload marks first."

    result = {}
    for col in ['CO1','CO2','CO3','CO4','CO5','CO6']:
        result[col] = (df[col] >= 50).mean()*100

    return pd.DataFrame(list(result.items()), columns=['CO','Attainment']).to_html()

# ---------------- PO ----------------
CO_PO_MAP = {
    'CO1':[1,0,2,0,1],
    'CO2':[2,1,0,1,0],
    'CO3':[1,1,1,0,2],
    'CO4':[0,2,1,1,1],
    'CO5':[1,0,1,2,1],
    'CO6':[2,1,1,0,1]
}

@app.route('/po')
def po():
    conn = sqlite3.connect('database.db')
    df = pd.read_sql("SELECT * FROM marks", conn)
    conn.close()

    co_att = {}
    for col in CO_PO_MAP.keys():
        co_att[col] = (df[col] >= 50).mean()*100

    po = [0]*5
    for co, weights in CO_PO_MAP.items():
        for i in range(5):
            po[i] += co_att[co]*weights[i]

    return pd.DataFrame({
        'PO':[f'PO{i+1}' for i in range(5)],
        'Attainment':po
    }).to_html()

# ---------------- GRAPH ----------------
@app.route('/graph')
def graph():
    conn = sqlite3.connect('database.db')
    df = pd.read_sql("SELECT * FROM marks", conn)
    conn.close()

    cols = ['CO1','CO2','CO3','CO4','CO5','CO6']
    values = [(df[c] >= 50).mean()*100 for c in cols]

    plt.bar(cols, values)
    plt.savefig("static/graph.png")
    plt.close()

    return '<img src="/static/graph.png">'

# ---------------- PDF ----------------
@app.route('/report')
def report():
    doc = SimpleDocTemplate("report.pdf")
    styles = getSampleStyleSheet()

    elements = []
    elements.append(Paragraph("NBA ERP Report", styles['Title']))
    elements.append(Spacer(1,20))
    elements.append(Paragraph("CO & PO Attainment Included", styles['Normal']))

    doc.build(elements)

    return "Report Generated (check folder)"

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)
