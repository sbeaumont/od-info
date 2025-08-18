"""
Main entrypoint for the application.

- Uses the ODInfo facade object for all queries and actions.
- Knows the routing, the templates to use, which facade calls to make and which data to pass to a template.
- Initializes Flask plugins: Flask_SQLAlchemy, Flask_Login

"""

import os
import sys
import logging
import flask
from flask import Flask, g, request, render_template, session
from flask_login import LoginManager, login_user, login_required
from flask_sqlalchemy import SQLAlchemy

from odinfo.timeutils import current_od_time
from odinfoweb.forms import LoginForm

from odinfo.domain.models import Base
from odinfoweb.user import load_user_by_id, load_user_by_name, User

from odinfo.config import feature_toggles, OP_CENTER_URL, load_secrets, check_dirs_and_configs
from odinfo.facade.odinfo import ODInfoFacade
from odinfo.facade.graphs import nw_history_graph, land_history_graph
from odinfo.exceptions import ODInfoException

# ---------------------------------------------------------------------- Flask

print("Checking directories and config files...")
problems = check_dirs_and_configs()
if problems:
    sys.exit('\n'.join(problems))
else:
    print("Config files OK")

# ---------------------------------------------------------------------- Flask

if getattr(sys, 'frozen', False):
    # When app is built with pyinstaller
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    if not os.path.exists(template_folder):
        sys.exit(f"ERROR: PyInstaller bundle missing required templates folder at: {template_folder}")
    
    static_folder = os.path.join(sys._MEIPASS, 'static')
    # Static folder is optional, but if it doesn't exist, set to None
    if not os.path.exists(static_folder):
        static_folder = None
        print(f"WARNING: No static folder found in PyInstaller bundle at: {static_folder}")
    
    app = Flask('od-info', template_folder=template_folder, static_folder=static_folder)
else:
    # Regular Flask startup
    template_folder = './odinfoweb/templates'
    if not os.path.exists(template_folder):
        sys.exit(f"ERROR: Templates folder not found at: {template_folder}")
    
    static_folder = './odinfoweb/static'
    if not os.path.exists(static_folder):
        static_folder = None
        print(f"WARNING: No static folder found at: {static_folder}")
    
    app = Flask('od-info', template_folder=template_folder, static_folder=static_folder)

app.logger.setLevel(logging.DEBUG)

# ---------------------------------------------------------------------- flask_SQLAlchemy

db = SQLAlchemy(model_class=Base, session_options={"autoflush": False})
# The lib adds an "instance" folder to the URL so I have to take that into account.
db_url = load_secrets()['database_name']

print("Database URL:", db_url)
if db_url.startswith('sqlite:'):
    print("Note that the Flask_SQLAlchemy library inserts an 'instance' subdir into a sqlite Database URL.")

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_size": 20,
    "max_overflow": 10,
    "pool_timeout": 10,
    "pool_recycle": 280
}

db.init_app(app)
with app.app_context():
    db.create_all()

# ---------------------------------------------------------------------- flask_login

app.secret_key = load_secrets()['secret_key']
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = u"Please login"


@login_manager.user_loader
def load_user(user_id):
    if 'od_user' not in session:
        session['od_user'] = load_user_by_id(user_id).to_json()
    user = User.from_json(session['od_user'])
    if user and (user.get_id() == str(user_id)):
        return user
    else:
        return None


# ---------------------------------------------------------------------- Facade Singleton

def facade() -> ODInfoFacade:
    _facade = getattr(g, '_facade', None)
    if not _facade:
        _facade = g._facade = ODInfoFacade(db)
    return _facade


# ---------------------------------------------------------------------- Error Handlers

@app.errorhandler(ODInfoException)
def handle_odinfo_error(error):
    """Handle ODInfo-specific errors gracefully."""
    import traceback
    error_traceback = traceback.format_exc()
    
    # Try to render the appropriate template with error info
    # Use the referrer to determine which page to show
    template = 'odinfo-base.html'
    if request.endpoint:
        # Map endpoints to their templates
        template_map = {
            'overview': 'overview.html',
            'towncrier': 'towncrier.html',
            'stats': 'stats.html',
            'nw_tracker': 'nwtracker.html',
            'economy': 'economy.html',
            'ratios': 'ratios.html',
            'military': 'military.html',
            'realmies': 'realmies.html',
            'stealables': 'stealables.html',
        }
        template = template_map.get(request.endpoint, 'odinfo-base.html')
    
    return render_template(template,
                          feature_toggles=feature_toggles,
                          error=error,
                          error_traceback=error_traceback), 500


@app.errorhandler(Exception)
def handle_general_error(error):
    """Handle all other errors gracefully."""
    # In debug mode, let Flask/Werkzeug handle it for better debugging
    if app.debug:
        raise
    
    import traceback
    error_traceback = traceback.format_exc()
    
    # Wrap the error in ODInfoException for consistent handling
    wrapped_error = ODInfoException(
        message=f"{error.__class__.__name__}: {str(error)}",
        details={'original_error': str(error)}
    )
    wrapped_error.__cause__ = error
    
    # Try to render the appropriate template with error info
    template = 'odinfo-base.html'
    if request.endpoint:
        # Map endpoints to their templates
        template_map = {
            'overview': 'overview.html',
            'towncrier': 'towncrier.html',
            'stats': 'stats.html',
            'nw_tracker': 'nwtracker.html',
            'economy': 'economy.html',
            'ratios': 'ratios.html',
            'military': 'military.html',
            'realmies': 'realmies.html',
            'stealables': 'stealables.html',
        }
        template = template_map.get(request.endpoint, 'odinfo-base.html')
    
    return render_template(template,
                          feature_toggles=feature_toggles,
                          error=wrapped_error,
                          error_traceback=error_traceback), 500


# ---------------------------------------------------------------------- Flask Routes

@app.route('/', methods=['GET', 'POST'])
@app.route('/dominfo/', methods=['GET', 'POST'])
@login_required
def overview():
    if request.args.get('update'):
        facade().update_dom_index()
        facade().update_all()
        facade().update_realmies()
    if request.method == 'POST':
        for k, v in request.form.items():
            if k.startswith('role.'):
                prefix, dom, old_role = k.split('.')
                if old_role != v:
                    facade().update_role(dom, v)
            elif k.startswith('name.'):
                prefix, dom, old_name = k.split('.')
                if old_name != v:
                    facade().update_player(dom, v)
    return render_template(
        'overview.html',
        feature_toggles=feature_toggles,
        doms=facade().dom_list(),
        nw_deltas=facade().nw_deltas(),
        ages=facade().all_doms_ops_age(),
        current_time=current_od_time(as_str=True))


@app.route('/dominfo/<domcode>')
@app.route('/dominfo/<domcode>/<update>')
@login_required
def dominfo(domcode: int, update=None):
    if update == 'update':
        facade().update_ops(domcode)
    nw_history = facade().nw_history(domcode)
    dominion = facade().dominion(domcode)
    return render_template(
        'dominfo.html',
        feature_toggles=feature_toggles,
        dominion=dominion,
        military=facade().military(dominion),
        ratios=facade().ratios(dominion),
        ops_age=facade().ops_age(dominion),
        nw_history_graph=nw_history_graph(nw_history),
        land_history_graph=land_history_graph(nw_history),
        op_center_url=OP_CENTER_URL)


@app.route('/towncrier')
@login_required
def towncrier():
    if request.args.get('update'):
        facade().update_town_crier()
    return render_template('towncrier.html',
                           feature_toggles=feature_toggles,
                           towncrier=facade().get_town_crier())


@app.route('/stats')
@login_required
def stats():
    if request.args.get('update'):
        facade().update_town_crier()
    return render_template('stats.html',
                           feature_toggles=feature_toggles,
                           stats=facade().award_stats())


@app.route('/nwtracker/<send>')
@app.route('/nwtracker')
@login_required
def nw_tracker(send=None):
    result_of_send = ''
    if send == 'send':
        result_of_send = facade().send_top_bot_nw_to_discord()
    return render_template('nwtracker.html',
                           feature_toggles=feature_toggles,
                           top_nw=facade().get_top_bot_nw(filter_zeroes=True),
                           bot_nw=facade().get_top_bot_nw(top=False, filter_zeroes=True),
                           unchanged_nw=facade().get_unchanged_nw(),
                           result_of_send=result_of_send)


@app.route('/economy')
@login_required
def economy():
    return render_template('economy.html',
                           feature_toggles=feature_toggles,
                           economy=facade().economy())


@app.route('/ratios')
@login_required
def ratios():
    return render_template('ratios.html',
                           feature_toggles=feature_toggles,
                           doms=facade().ratio_list())


@app.route('/military', defaults={'versus_op': 0})
@app.route('/military/<int:versus_op>')
@login_required
def military(versus_op: int = 0):
    dom_list = facade().military_list(versus_op=versus_op, top=1000)
    return render_template('military.html',
                           feature_toggles=feature_toggles,
                           doms=dom_list,
                           ages=facade().all_doms_ops_age(),
                           top_op=facade().top_op(dom_list),
                           versus_op=versus_op,
                           current_day=facade().current_tick.day)


@app.route('/realmies')
@login_required
def realmies():
    return render_template('realmies.html',
                           feature_toggles=feature_toggles,
                           realmies=facade().realmies_with_blops_info())


@app.route('/stealables')
@login_required
def stealables():
    return render_template('stealables.html',
                           feature_toggles=feature_toggles,
                           stealables = facade().stealables(),
                           ages=facade().all_doms_ops_age())


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if (request.method == 'POST') and form.validate():
        user = load_user_by_name(form.username.data)
        if user:
            if user.password == form.password.data:
                print("Authenticated", user.name)
                user._authenticated = True
                session['od_user'] = user.to_json()
                login_user(user)
            else:
                print("Could not authenticate", user.name)
        else:
            print("Could find user with name", form.username.data)

        flask.flash('Logged in successfully.')

        next = flask.request.args.get('next')
        # url_has_allowed_host_and_scheme should check if the url is safe
        # for redirects, meaning it matches the request host.
        # See Django's url_has_allowed_host_and_scheme for an example.
        # if not url_has_allowed_host_and_scheme(next, request.host):
        #     return flask.abort(400)

        return flask.redirect(next or flask.url_for('overview'))
    return flask.render_template('login.html', form=form)


@app.teardown_appcontext
def teardown_app(exception):
    facade = getattr(g, '_facade', None)
    if facade:
        facade.teardown()


if __name__ == '__main__':
    print("Starting Server...")
    app.run()
