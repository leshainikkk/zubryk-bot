import json
import importlib.metadata
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import requests
from dotenv import set_key
import telebot
from telebot import types

from zubryk.config import BOT_TOKEN


def main():
    os.chdir(ROOT)
    runtime=ROOT/".runtime"
    runtime.mkdir(exist_ok=True)
    port=int(os.environ.get("PORT","8088"))
    children=[]
    files=[]

    def start(name,command):
        log=(runtime/f"{name}.log").open("w")
        files.append(log)
        process=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.PIPE if name=="tunnel" else subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        children.append(process)
        return process

    def cleanup(*_):
        for child in children:
            if child.poll() is None: child.terminate()
        for child in children:
            try: child.wait(timeout=5)
            except subprocess.TimeoutExpired:child.kill()
        for file in files:file.close()

    signal.signal(signal.SIGTERM,lambda *_: sys.exit(0))
    signal.signal(signal.SIGINT,lambda *_: sys.exit(0))
    try:
        api=start("api",[sys.executable,"web.py"])
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            if api.poll() is not None:raise RuntimeError("API stopped; see .runtime/api.log")
            try:
                if requests.get(f"http://127.0.0.1:{port}/api/health",timeout=2).status_code==200:break
            except requests.RequestException:pass
            time.sleep(.5)
        else:raise RuntimeError("API health check failed")
        provider=os.environ.get("TUNNEL_PROVIDER","cloudflare")
        if provider=="localhostrun":
            command=["/usr/bin/ssh","-T","-o","StrictHostKeyChecking=accept-new",
                     "-o",f"UserKnownHostsFile={runtime/'known_hosts'}","-o","IdentitiesOnly=yes",
                     "-o","IdentityFile=/dev/null","-o","PreferredAuthentications=none",
                     "-o","PasswordAuthentication=no","-o","ServerAliveInterval=30",
                     "-o","ExitOnForwardFailure=yes","-R",f"80:127.0.0.1:{port}","nokey@localhost.run"]
            pattern=r"https://[a-z0-9-]+\.lhr\.life"
        elif provider=="cloudflare":
            cloud=os.environ.get("CLOUDFLARED_BIN","/opt/homebrew/bin/cloudflared")
            command=[cloud,"tunnel","--no-autoupdate","--protocol","http2","--url",f"http://127.0.0.1:{port}"]
            pattern=r"https://[a-z0-9-]+\.trycloudflare\.com"
        else:
            raise RuntimeError("Unknown TUNNEL_PROVIDER")
        tunnel=start("tunnel",command)
        deadline=time.monotonic()+45
        url=None
        while time.monotonic()<deadline:
            if tunnel.poll() is not None:raise RuntimeError("Tunnel stopped; see .runtime/tunnel.log")
            matches=re.findall(pattern,(runtime/"tunnel.log").read_text())
            if matches:url=matches[-1];break
            time.sleep(.5)
        if not url:raise RuntimeError("Tunnel provider did not return an HTTPS URL")
        set_key(ROOT/".env","MINI_APP_URL",url)
        (runtime/"mini_app_url").write_text(url)
        client=telebot.TeleBot(BOT_TOKEN)
        me=client.get_me()
        client.set_chat_menu_button(menu_button=types.MenuButtonWebApp(type="web_app",text="Зубрик",web_app=types.WebAppInfo(url)))
        client.set_my_commands([types.BotCommand("start","Начать и открыть главное меню"),types.BotCommand("app","Открыть приложение"),types.BotCommand("test","Повторить изученные слова"),types.BotCommand("help","Как устроен Зубрик"),types.BotCommand("support","Поддержка")])
        polling=start("bot",[sys.executable,"bot.py"])
        info={"pid":os.getpid(),"apiPid":api.pid,"botPid":polling.pid,"tunnelPid":tunnel.pid,"url":url,"botUsername":me.username,"port":port,"provider":provider,"python":sys.executable,"telegramLibrary":importlib.metadata.version("pyTelegramBotAPI")}
        (runtime/"preview.json").write_text(json.dumps(info,ensure_ascii=False,indent=2)+"\n")
        print(json.dumps(info,ensure_ascii=False),flush=True)
        while True:
            time.sleep(2)
            if tunnel.poll() is not None:
                print("Tunnel connection closed; reconnecting",flush=True)
                children.remove(tunnel)
                if tunnel.stdin:tunnel.stdin.close()
                time.sleep(3)
                tunnel=start("tunnel",command)
                deadline=time.monotonic()+45
                while time.monotonic()<deadline:
                    matches=re.findall(pattern,(runtime/"tunnel.log").read_text())
                    if matches:
                        latest=matches[-1]
                        client.set_chat_menu_button(menu_button=types.MenuButtonWebApp(type="web_app",text="Зубрик",web_app=types.WebAppInfo(latest)))
                        set_key(ROOT/".env","MINI_APP_URL",latest)
                        (runtime/"mini_app_url").write_text(latest)
                        url=latest
                        info.update(url=url,tunnelPid=tunnel.pid)
                        (runtime/"preview.json").write_text(json.dumps(info,ensure_ascii=False,indent=2)+"\n")
                        print("Tunnel reconnected: "+url,flush=True)
                        break
                    if tunnel.poll() is not None:break
                    time.sleep(.5)
                if tunnel.poll() is not None:
                    continue
            if provider=="localhostrun":
                provisioned=re.findall(r"(?m)^([a-z0-9-]+\.lhr\.life) tunneled with tls termination, https://\1",(runtime/"tunnel.log").read_text())
                latest="https://"+provisioned[-1] if provisioned else url
                if latest!=url:
                    client.set_chat_menu_button(menu_button=types.MenuButtonWebApp(type="web_app",text="Зубрик",web_app=types.WebAppInfo(latest)))
                    set_key(ROOT/".env","MINI_APP_URL",latest)
                    (runtime/"mini_app_url").write_text(latest)
                    url=latest
                    info["url"]=url
                    (runtime/"preview.json").write_text(json.dumps(info,ensure_ascii=False,indent=2)+"\n")
                    print("Preview URL refreshed: "+url,flush=True)
            for child in (api,polling):
                if child.poll() is not None:raise RuntimeError(f"Preview child {child.pid} stopped")
    except Exception as exc:
        message=str(exc).replace(BOT_TOKEN,"[redacted]")
        print(f"Preview failed: {type(exc).__name__}: {message}",file=sys.stderr,flush=True)
        raise SystemExit(1)
    finally:
        cleanup()


if __name__=="__main__":
    main()
