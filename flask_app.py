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
def analytics():
    if request.method == 'POST':
        for k, v in request.form.items():
            dom, old_role = k.split('.')
            if old_role != v:
                print(f"Dominion {dom} changed {old_role} to {v}")
                get_facade().update_role(dom, v)
    return render_template('analytics.html', ctx=get_facade().dom_list())


@app.route('/dominfo/<domcode>')
def dominfo(domcode: int):
    return render_template('dominfo.html', dom=get_facade().dom_status(domcode), castle=get_facade().castle(domcode))


@app.teardown_appcontext
def teardown_app(exception):
    facade = getattr(g, '_facade', None)
    if facade:
        facade.teardown()

