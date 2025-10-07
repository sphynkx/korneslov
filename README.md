Here is a Telegram bot designed for semantic/syntactic/analytical analysis of Old Testament texts using the author's original methodology __"Korneslov"__.

An admin panel has also been created for the bot. See [rootster repositoy](https://github.com/sphynkx/rootster) for details.


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


## Bot Install
In Telegram go to [@BotFather](https://t.me/BotFather), send command `/newbot`. Input something for bot name and username (username must ends on "Bot" or "_bot"). After that BotFather creates new token. Place this token to `.env` as `TELEGRAM_BOT_TOKEN` param.

Find recently created bot (search it in form @username_bot) and restart it. Then you'll see bot's keyboard - bot will ready to work.

Also get API key for OpenAI and set it to `.env` as `OPENAI_API_KEY` param.


## Payments config
You need to register billing providers for bot. Go to [@BotFather](https://t.me/BotFather), run `/mybots`, choose your bot, next - press `Payments` button. You got the list of available providers. Configure some of them following provided recommendations and get provider's token. Then put token(s) into `config.py` to `TGPAYMENT_PROVIDERS` variable (`provider_token`). Set currency that will use with this provider (`currency`) - as currency code accordingly to ISO 4217. Also set country code (`country`) and provider name (`name`). Set exchange rate (`exchange_rate`): bot uses an internal payment value and you may configure your own course for requests payment. Basically you may choose some of currency as payment unit and recompute `exchange_rate` for all other providers as course to this base currency.


# Run App
At first run manually:
```
cd /opt/korneslov
./run.sh
```


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

Run it:
```
systemctl daemon-reload
systemctl enable korneslov-bot.service
systemctl start korneslov-bot.service
```
Check:
```
systemctl status korneslov-bot.service
journalctl -u korneslov-bot.service -f
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


## Admin panel
Optional but useful. Go to [rootster repositoy](https://github.com/sphynkx/rootster) and follow instructions. Set the same DB settings as for bot.


# Usage
Run bot in your Telegram client. If everything is OK you'll see keyboardwith buttons.

**Note**: bot works only after the payment has been charged.

Switch to necessary language, go to `Korneslov` menu, then the `Masoret` (for now the rest are not implemented). Next choose request level (`For fun`, `Details` or `Academic`). Type you request about some **Old Testament**'s book, chapter and verses in format like:
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

