from flask import Flask, render_template, request, redirect, url_for, session
from routes.route import bp as main_bp

app = Flask(__name__)
app.secret_key = 'cambia-esta-secret'  # Cambia esta clave por una segura

app.register_blueprint(main_bp)

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        # Ejemplo: credenciales estáticas. Cambia a tu lógica real (BD, etc.)
        if username == 'admin' and password == 'admin':
            session['user'] = username
            return redirect(url_for('main.home'))
        else:
            error = 'Credenciales inválidas. Intenta nuevamente.'
            return render_template('view/login.html', error=error)
    return render_template('view/login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)