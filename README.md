Here is small telegram bot that send requests to OpenAI engine to handle Bible poems with Kroneslov algorythm.

# Nginx configuration
Suppose we have preconfigured DNS-records for subdomain `korneslov` as subdoain fo `veda.wiki`.

```
dnf install nginx certbot python3-certbot-nginx
```

Create subdomain config for nginx `/etc/nginx/conf.d/korneslov.conf`:
```
server {
    listen 80;
    server_name korneslov.veda.wiki;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
```

Restart nginx and check:
```
service nginx restart
ping korneslov.veda.wiki
```

Get SSL-certificate for subdomain:
```
certbot --nginx -d korneslov.veda.wiki
```
Check from any external side:
```
curl -I https://korneslov.veda.wiki/
```


# Tribute config
Go to  tribute.tg - to Tribute Admin Console and set "Webhook URL" as https://korneslov.veda.wiki/tribute_webhook


# App initial install
```
cd /opt/korneslov
python3 -m venv .venv
source .venv/bin/activate
sudo dnf install gcc python3-devel libffi-devel openssl-devel
pip install --upgrade pip
pip install -r requirements.txt
```


# Run app
Set USE_TRIBUTE = False

Ar first run manually:
```
cd /opt/korneslov
./run.sh
```

From separate console run:
```
./run-webhook.sh
```
No need to run it if `USE_TRIBUTE = False`. Only after tribute configuring.


# systems configs
Create new `/etc/systemd/system/korneslov-bot.service`:
```
[Unit]
Description=Korneslov Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/korneslov
ExecStart=/bin/bash /opt/korneslov/run.sh
Restart=always
User=root
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```
Also `/etc/systemd/system/korneslov-webhook.service`:
```
[Unit]
Description=Korneslov Tribute Webhook Flask Service
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/korneslov
ExecStart=/bin/bash /opt/korneslov/run-webhook.sh
Restart=always
User=root
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```
Run them:
```
systemctl daemon-reload
systemctl enable korneslov-bot.service
systemctl enable korneslov-webhook.service
systemctl start korneslov-bot.service
systemctl start korneslov-webhook.service
```
Check:
```
systemctl status korneslov-bot.service
systemctl status korneslov-webhook.service
journalctl -u korneslov-bot.service -f
journalctl -u korneslov-webhook.service -f
```


