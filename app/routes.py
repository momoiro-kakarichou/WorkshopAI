from flask import render_template, Blueprint, send_from_directory
from app.constants import CARDS_ASSETS_URL

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/cards_assets/<path:filepath>')
def serve_cards_assets(filepath):
    return send_from_directory(CARDS_ASSETS_URL, filepath)