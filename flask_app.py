from flask import Flask, g, request
from flask import render_template
import logging

from config import OP_CENTER_URL
from facade.odinfo import ODInfoFacade


app = Flask('od-info')
app.logger.setLevel(logging.DEBUG)


def facade() -> ODInfoFacade:
    _facade = getattr(g, '_facade', None)
    if not _facade:
        _facade = g._facade = ODInfoFacade()
    return _facade


@app.route('/', methods=['GET', 'POST'])
@app.route('/dominfo/', methods=['GET', 'POST'])
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
        doms=dom_list,
        nw_deltas=nw_deltas,
        ages=facade().all_doms_ops_age())


@app.route('/dominfo/<domcode>')
@app.route('/dominfo/<domcode>/<update>')
def dominfo(domcode: int, update=None):
    if update == 'update':
        facade().update_ops(domcode)
    dom_name = facade().name_for_dom_code(domcode)
    return render_template(
        'dominfo.html',
        dominion=facade().dominion(domcode),
        domname=dom_name,
        domcode=domcode,
        dom=facade().dom_status(domcode),
        castle=facade().castle(domcode),
        barracks=facade().barracks(domcode),
        nw_history=facade().nw_history(domcode),
        op_center_url=OP_CENTER_URL)


@app.route('/towncrier')
def towncrier():
    if request.args.get('update'):
        facade().update_town_crier()
    return render_template('towncrier.html',
                           towncrier=facade().get_town_crier())


@app.route('/nwtracker/<send>')
@app.route('/nwtracker')
def nw_tracker(send=None):
    result_of_send = ''
    if send == 'send':
        result_of_send = facade().send_top_bot_nw_to_discord()
    return render_template('nwtracker.html',
                           top_nw=facade().get_top_bot_nw(filter_zeroes=True),
                           bot_nw=facade().get_top_bot_nw(top=False, filter_zeroes=True),
                           unchanged_nw=facade().get_unchanged_nw(),
                           result_of_send=result_of_send)


@app.route('/economy')
def economy():
    return render_template('economy.html',
                           economy=facade().economy())


@app.route('/ratios')
def ratios():
    return render_template('ratios.html',
                           doms=facade().doms_with_ratios(),
                           ages=facade().all_doms_ops_age())


@app.route('/military', defaults={'versus_op': 0})
@app.route('/military/<versus_op>')
def military(versus_op: int = 0):
    dom_list = facade().all_doms_as_objects()
    return render_template('military.html',
                           doms=dom_list,
                           ages=facade().all_doms_ops_age(),
                           top_op=facade().top_op(dom_list),
                           versus_op=int(versus_op))


@app.route('/realmies')
def realmies():
    return render_template('realmies.html',
                           realmies=facade().realmies())


@app.teardown_appcontext
def teardown_app(exception):
    facade = getattr(g, '_facade', None)
    if facade:
        facade.teardown()

