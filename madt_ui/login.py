from quart import Blueprint, request, render_template, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user
import os

login_manager = LoginManager()
login_manager.login_view = "login.login"

login_bp = Blueprint('login', __name__)


class User(UserMixin):
    def get_id(self):
        return 'DEFAULT_USER'


default_user = User()


@login_manager.user_loader
def load_user(user_id):
    if user_id != 'DEFAULT_USER':
        return None

    return default_user


def public_endpoint(function):
    function.is_public = True
    return function


@login_bp.route('/login', methods=["GET", "POST"])
@public_endpoint
async def login():

    data = await request.form

    if data.get('username') == 'demo' and \
            data.get('password') == os.environ['SSH_PWD']:

        login_user(default_user)

        return redirect(url_for('list_labs'))

    else:
        return await render_template('login.html')
