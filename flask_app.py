from flask import Flask, g, request
from flask import render_template
from calcapp.calcfacade import CalcFacade


app = Flask(__name__)


def get_facade() -> CalcFacade:
    facade = getattr(g, '_facade', None)
    if not facade:
        facade = g._facade = CalcFacade()
    return facade


@app.route('/', methods=['GET', 'POST'])
def overview():
    if request.args.get('update'):
        get_facade().update_dom_index()
    if request.method == 'POST':
        for k, v in request.form.items():
            if k.startswith('role.'):
                prefix, dom, old_role = k.split('.')
                if old_role != v:
                    print(f"Dominion {dom} changed {old_role} to {v}")
                    get_facade().update_role(dom, v)
    dom_list, nw_deltas = get_facade().dom_list()
    return render_template('overview.html', doms=dom_list, nw_deltas=nw_deltas)


@app.route('/dominfo/<domcode>')
def dominfo(domcode: int):
    dom_name = get_facade().name_for_dom_code(domcode)
    return render_template('dominfo.html', domname=dom_name, dom=get_facade().dom_status(domcode), castle=get_facade().castle(domcode))


@app.route('/towncrier')
def towncrier():
    if request.args.get('update'):
        get_facade().update_town_crier()
    return render_template('towncrier.html', towncrier=get_facade().get_town_crier())


@app.route('/nwtracker/<send>')
@app.route('/nwtracker')
def nw_tracker(send=None):
    result_of_send = ''
    if send == 'send':
        result_of_send = get_facade().send_top_bot_nw_to_discord()
    return render_template('nwtracker.html', top_nw=get_facade().get_top_bot_nw(), bot_nw=get_facade().get_top_bot_nw(False), result_of_send=result_of_send)


@app.teardown_appcontext
def teardown_app(exception):
    facade = getattr(g, '_facade', None)
    if facade:
        facade.teardown()

