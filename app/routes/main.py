from flask import Blueprint, render_template, redirect, url_for
from datetime import datetime


main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    current_year = datetime.now().year
    return render_template('index.html', year=current_year)

@main_bp.route('/about')
def about():
    return render_template('about.html')