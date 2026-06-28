import os

# CRITICAL: exactly one worker. The simulation is a single stateful process
# that binds OPC UA ports; multiple workers would collide and fork state.
workers = 1
threads = int(os.environ.get("WEB_THREADS", "8"))
worker_class = "gthread"
timeout = 120
bind = f"0.0.0.0:{os.environ.get('PORT', '8800')}"
preload_app = False
accesslog = "-"
errorlog = "-"
