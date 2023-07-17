from flask import Flask, g, request
from flask import render_template
from app.facade import ODInfoFacade


app = Flask(__name__)


def facade() -> ODInfoFacade:
    _facade = getattr(g, '_facade', None)
    if not _facade:
        _facade = g._facade = ODInfoFacade()
    return _facade


@app.route('/', methods=['GET', 'POST'])
@app.route('/dominfo/')
def overview():
    if request.args.get('update'):
        facade().update_dom_index()
    if request.method == 'POST':
        for k, v in request.form.items():
            if k.startswith('role.'):
                prefix, dom, old_role = k.split('.')
                if old_role != v:
                    print(f"Dominion {dom} changed {old_role} to {v}")
                    facade().update_role(dom, v)
    dom_list, nw_deltas = facade().dom_list()
    return render_template('overview.html', doms=dom_list, nw_deltas=nw_deltas)


@app.route('/dominfo/<domcode>')
@app.route('/dominfo/<domcode>/<update>')
def dominfo(domcode: int, update=None):
    if update == 'update':
        facade().update_ops(domcode)
    dom_name = facade().name_for_dom_code(domcode)
    return render_template('dominfo.html',
                           domname=dom_name,
                           domcode=domcode,
                           dom=facade().dom_status(domcode),
                           castle=facade().castle(domcode),
                           barracks=facade().barracks(domcode),
                           nw_history=facade().nw_history(domcode))


@app.route('/towncrier')
def towncrier():
    if request.args.get('update'):
        facade().update_town_crier()
    return render_template('towncrier.html', towncrier=facade().get_town_crier())


@app.route('/nwtracker/<send>')
@app.route('/nwtracker')
def nw_tracker(send=None):
    result_of_send = ''
    if send == 'send':
        result_of_send = facade().send_top_bot_nw_to_discord()
    return render_template('nwtracker.html', top_nw=facade().get_top_bot_nw(), bot_nw=facade().get_top_bot_nw(False), result_of_send=result_of_send)


@app.teardown_appcontext
def teardown_app(exception):
    facade = getattr(g, '_facade', None)
    if facade:
        facade.teardown()

