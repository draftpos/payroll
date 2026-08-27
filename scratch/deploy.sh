#!/bin/bash
export SSHPASS='Farai@#$1234'
PORT=9419
HOST="pungwebreweries.havano.online"

for user in ubuntu root frappe ashley havano; do
    echo "Trying $user@$HOST:$PORT..."
    if sshpass -e ssh -o StrictHostKeyChecking=no -p $PORT $user@$HOST "echo 'SUCCESS'"; then
        echo "Connected as $user"
        sshpass -e ssh -o StrictHostKeyChecking=no -p $PORT $user@$HOST << 'EOF'
            if [ -d "/home/frappe/frappe-bench" ]; then
                BENCH_DIR="/home/frappe/frappe-bench"
            elif [ -d "/opt/frappe/frappe-bench" ]; then
                BENCH_DIR="/opt/frappe/frappe-bench"
            elif [ -d "/home/ubuntu/frappe-bench" ]; then
                BENCH_DIR="/home/ubuntu/frappe-bench"
            else
                BENCH_DIR=$(find /home -maxdepth 3 -name 'frappe-bench' -type d 2>/dev/null | head -n 1)
            fi
            
            if [ -z "$BENCH_DIR" ]; then
                echo "frappe-bench directory not found!"
                exit 1
            fi
            
            echo "Using bench directory: $BENCH_DIR"
            cd $BENCH_DIR
            
            echo "Pulling latest changes for havano_zim_payroll..."
            if [ -d "apps/havano_zim_payroll" ]; then
                cd apps/havano_zim_payroll
                git pull
                cd ../..
            else
                bench get-app havano_zim_payroll
            fi
            
            echo "Migrating sites..."
            bench --site all migrate
            
            echo "Restarting services..."
            bench restart
EOF
        exit 0
    fi
done
echo "Failed to connect with any standard username."
exit 1
