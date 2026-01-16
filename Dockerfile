# Dockerfile
# Thick-mode python-oracledb with Oracle Instant Client
#
# NOTE: Oracle Instant Client packages require accepting Oracle license terms.
# Download the Instant Client ZIP(s) manually and place them in ./instantclient:
#   - instantclient-basiclite-linux.x64-*.zip  (required)
# Optionally:
#   - instantclient-sqlplus-linux.x64-*.zip    (optional)
#
# Then build:
#   docker build -t flask-oracle-thick .

FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends libaio-dev unzip ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/oracle
WORKDIR /opt/oracle

COPY instantclient/*.zip /opt/oracle/

RUN set -eux; \
    unzip -q "/opt/oracle/"'instantclient-*.zip' -d /opt/oracle; \
    icdir="$(ls -d /opt/oracle/instantclient_* | head -n 1)"; \
    ln -s "$icdir" /opt/oracle/instantclient; \
    echo "/opt/oracle/instantclient" > /etc/ld.so.conf.d/oracle-instantclient.conf; \
    ldconfig

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py /app/
COPY dbconnection.py /app/
COPY config/ /app/config/

ENV PORT=5000
EXPOSE 5000

CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app", "--workers", "2", "--threads", "4", "--timeout", "120"]
