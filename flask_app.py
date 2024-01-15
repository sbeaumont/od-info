import os
import sys
import logging
import flask
from flask import Flask, g, request, render_template, session
from flask_login import LoginManager, login_user, login_required
from forms import LoginForm
from facade.user import load_user_by_id, load_user_by_name, User

from config import feature_toggles, OP_CENTER_URL, load_secrets
from facade.odinfo import ODInfoFacade

if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask('od-info', template_folder=template_folder, static_folder=static_folder)
else:
    app = Flask('od-info')

app.logger.setLevel(logging.DEBUG)
app.secret_key = load_secrets()['secret_key']

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = u"Please login"


@login_manager.user_loader
def load_user(user_id):
    print('Loading user {}'.format(user_id))
    print(session.get('od_user', None))
    if 'od_user' not in session:
        print("Loading new user")
        session['od_user'] = load_user_by_id(user_id).to_json()
    user = User.from_json(session['od_user'])
    print(user, user.get_id(), str(user_id))
    if user and (user.get_id() == str(user_id)):
        print("Returning", user)
        return user
    else:
        return None


def facade() -> ODInfoFacade:
    _facade = getattr(g, '_facade', None)
    if not _facade:
        _facade = g._facade = ODInfoFacade()
    return _facade


@app.route('/', methods=['GET', 'POST'])
@app.route('/dominfo/', methods=['GET', 'POST'])
@login_required
def overview():
    if request.args.get('update'):
        facade().update_dom_index()
    elif request.args.get('update_all'):
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
    dom_list, nw_deltas = facade().dom_list()
    return render_template(
        'overview.html',
        feature_toggles=feature_toggles,
        doms=dom_list,
        nw_deltas=nw_deltas,
        ages=facade().all_doms_ops_age())


@app.route('/dominfo/<domcode>')
@app.route('/dominfo/<domcode>/<update>')
@login_required
def dominfo(domcode: int, update=None):
    if update == 'update':
        facade().update_ops(domcode)
    dom_name = facade().name_for_dom_code(domcode)
    return render_template(
        'dominfo.html',
        feature_toggles=feature_toggles,
        dominion=facade().dominion(domcode),
        domname=dom_name,
        domcode=domcode,
        dom=facade().dom_status(domcode),
        castle=facade().castle(domcode),
        barracks=facade().barracks(domcode),
        nw_history=facade().nw_history(domcode),
        op_center_url=OP_CENTER_URL)


@app.route('/towncrier')
@login_required
def towncrier():
    if request.args.get('update'):
        facade().update_town_crier()
    return render_template('towncrier.html',
                           feature_toggles=feature_toggles,
                           towncrier=facade().get_town_crier())


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
                           doms=facade().doms_with_ratios(),
                           ages=facade().all_doms_ops_age())


@app.route('/military', defaults={'versus_op': 0})
@app.route('/military/<versus_op>')
@login_required
def military(versus_op: int = 0):
    dom_list = facade().all_doms_as_objects()[:20]
    return render_template('military.html',
                           feature_toggles=feature_toggles,
                           doms=dom_list,
                           ages=facade().all_doms_ops_age(),
                           top_op=facade().top_op(dom_list),
                           versus_op=int(versus_op))


@app.route('/realmies')
@login_required
def realmies():
    return render_template('realmies.html',
                           feature_toggles=feature_toggles,
                           realmies=facade().realmies())


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
