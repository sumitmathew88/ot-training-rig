FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# OPC UA servers stay on loopback inside the container (not published).
ENV OTLAB_OPC_BIND=127.0.0.1
# Per-user tags/config persist here. Mount a Render disk at /data to make it
# survive redeploys; without a disk it still works but resets on each deploy.
ENV OTLAB_DATA_DIR=/data
ENV PORT=8800
EXPOSE 8800

# One worker only - see gunicorn.conf.py.
CMD ["gunicorn", "-c", "gunicorn.conf.py", "run_platform:app"]
