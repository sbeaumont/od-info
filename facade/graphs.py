from matplotlib.figure import Figure
import base64
from io import BytesIO
from datetime import datetime


def land_history_graph(dom_history):
    return dom_history_graph(dom_history, 'land')


def nw_history_graph(dom_history):
    return dom_history_graph(dom_history, 'networth')


def dom_history_graph(dom_history, yaxis: str):
    def conv_ts(ts):
        # return datetime.fromisoformat(ts).strftime('%Y-%m-%d %H:%M')
        return datetime.fromisoformat(ts)
    converted = {conv_ts(h['timestamp']): h[yaxis] for h in dom_history}
    x = list(converted.keys())
    x.sort()
    y = [converted[e] for e in x]
    fig = Figure()
    plt = fig.subplots()
    fig.autofmt_xdate()
    plt.plot(x, y)
    fig.suptitle(f"{yaxis.capitalize()} over Time")
    buf = BytesIO()
    fig.savefig(buf, format="png")
    # Embed the result in the html output.
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    return f"<img src='data:image/png;base64,{data}'/>"
