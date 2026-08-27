#!/bin/bash
export SSHPASS='Farai@#$1234'
PORT=9419
HOST="pungwebreweries.havano.online"
USER="root"

echo "Connecting to $HOST as $USER..."
sshpass -e ssh -o StrictHostKeyChecking=no -p $PORT $USER@$HOST << 'EOF'
    BENCH_DIR=$(find /home -maxdepth 3 -name 'frappe-bench' -type d 2>/dev/null | head -n 1)
    if [ -z "$BENCH_DIR" ]; then
        BENCH_DIR=$(find /opt -maxdepth 3 -name 'frappe-bench' -type d 2>/dev/null | head -n 1)
    fi
    
    if [ -z "$BENCH_DIR" ]; then
        echo "frappe-bench directory not found!"
        exit 1
    fi
    
    echo "Using bench directory: $BENCH_DIR"
    cd $BENCH_DIR
    
    echo "Clearing cache..."
    bench clear-cache
    
    echo "Checking supervisor..."
    if command -v supervisorctl &> /dev/null; then
        echo "Supervisor is installed. Checking status..."
        supervisorctl status
        echo "Restarting supervisor services..."
        supervisorctl restart all
    else
        echo "Supervisor not found."
    fi
    
    echo "Checking systemd services..."
    if command -v systemctl &> /dev/null; then
        systemctl list-units | grep frappe
        echo "Restarting frappe systemd services if any..."
        systemctl restart frappe* || true
    fi
    
    echo "Touching restart.txt (gunicorn reload)..."
    touch config/restart.txt || true
    
    echo "Done."
EOF
