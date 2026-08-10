#!/bin/bash
# Port 5042 instead of Flask's own 5000, which is taken too often to be a good default.
# Keep it in step with WEB_PORT in odinfo/config.py.
uv run python -m flask --app odinfoweb.flask_app run --port 5042