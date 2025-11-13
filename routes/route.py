from flask import Blueprint, redirect, url_for, session

bp = Blueprint('main', __name__)

@bp.route('/home')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return f'Bienvenido, {session["user"]}'