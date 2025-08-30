Here is small telegram bot that send requests to OpenAI engine to handle Bible poems with unique author's __Korneslov__ algorythm.



# Nginx Configuration
Suppose we have preconfigured DNS-records for subdomain `korneslov` as subdomain for `veda.wiki`.

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



# Install Process

## App Initial
```
cd /opt
git clone https://github.com/sphynkx/korneslov
cd /opt/korneslov
python3 -m venv .venv
source .venv/bin/activate
sudo dnf install gcc python3-devel libffi-devel openssl-devel
pip install --upgrade pip
pip install -r install/requirements.txt
deactivate
```

If you have access to private repo:
```
cd /opt/korneslov
git clone https://github.com/sphynkx/masoret texts
```
Create configuration file `.env` and set appropriate params there:
```
cp /opt/korneslov/install/.env-sample /opt/korneslov/.env

```


## DB Install
If MySQL is not installed:
```
dnf install mysql-server
systemctl enable --now mysqld
```
Copy from sample and modify `install/conf_db.sql` - set password for DB-user:
```
cd /opt/korneslov/install
cp conf_db.sql-sample conf_db.sql
```
Create and configure DB:
```
mysql -u root -p < app.sql
mysql -u root -p < conf_db.sql
mysql -u root -p korneslov < books.sql
service mysqld restart
```


## Tribute Config
Go to  [Tribute](https://tribute.tg/) - to Tribute Admin Console and set "Webhook URL" as https://korneslov.veda.wiki/tribute_webhook



## Bot Install
In Telegram go to [@BotFather](https://t.me/BotFather), send command `/newbot`. Input something for bot name and username (username must ends on "Bot" or "_bot"). After that BotFather creates new token. Place this token to `.env` as `TELEGRAM_BOT_TOKEN` param.

Find recently created bot (search it in form @username_bot) and restart it. Then you'll see bot's keyboard - bot will ready to work.

Also get API key for OpenAI and set it to `.env` as `OPENAI_API_KEY` param.



# Run App
Set `USE_TRIBUTE = False`.

At first run manually:
```
cd /opt/korneslov
./run.sh
```

From separate console run:
```
./run-webhook.sh
```
No need to run it if `USE_TRIBUTE = False`. Only after tribute configuring.



# Systems Configs

## Services Configuration
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


## External Proxy Configuration.
Only for cases then OpenAI prohibit connection from some ranges of IP (for example, reject some regions).

On some external server install some simple proxy server (replace ******** with your password, dont use '!' sign):
```
dnf install 3proxy
```
Edit /etc/3proxy.conf:
```
nscache 65536
timeouts 1 5 30 60 180 1800 15 60
daemon
log /var/log/3proxy/3proxy.log
logformat "- +_L%t.%. %N.%p %E %U %C:%c %R:%r %O %I %h %T"
rotate 30

users proxyuser:CL:********
auth strong
allow proxyuser IP_OF_SERVER_WITH_BOT

internal EXT_IP_OF_PROXY_SERVER
external EXT_IP_OF_PROXY_SERVER
socks -p1080
```
Start:
```
systemctl start 3proxy
systemctl enable 3proxy
```

Also open port 1080 in firewall:
```
sudo firewall-cmd --add-port=1080/tcp --permanent
sudo firewall-cmd --reload
```

Return to server with application, check connection:
```
curl -x socks5h://proxyuser:********@EXT_IP_OF_PROXY_SERVER:1080 https://api.ipify.org
```
If response is EXT_IP_OF_PROXY_SERVER then everything is OK.

Set variable `ALL_PROXY` in the `.env` with proxy parameters.


# Usage
Run bot in your Telegram client. If everything is OK you'll see keyboardwith buttons. Switch to necessary language, go to `Korneslov` menu, then the `Masoret` (for now the rest are not implemented). Next choose request level (`For fun`, `Details` or `Academic`). Type you request about some **Old Testament**'s book, chapter and verses in format like:
```
genesis 1 1
gen 1 2
exodus 2 3,4-6,8-10,12
1 samuel 2 3
```

Book name, chapter and verses block must separate by space symbol. Inside of verses block do not place spaces.

As of book names. Type book names in the same language that you choose recently. You may use common abbreviations and synonyms.

Press `Enter` of `Send` button and wait some minutes (request performs slow). Finally you receive some messages with analyzed texts.

About levels. The method involves issuing material divided into several parts (**0**, **1**, **2** and **3**), containing different types of information and the degree of its study. By choosing a level, you choose to issue a certain set of parts.

* **Part 0** - the text of a poem or poems (displayed at all levels).
* **Part 1** - detailed information on each word
* **Part 2** - a list of words with the meanings of basic roots
* **Part 3** - chains of basic meanings

Different levels include the following parts:

* **For fun** - parts **0** and **3**
* **Details** - parts **0**, **2** and **3**
* **Academic** - parts **0**, **1**, **2** and **3**

