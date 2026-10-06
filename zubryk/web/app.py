import hashlib
import json
import logging
from datetime import datetime, timedelta

from flask import Flask, abort, g, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from zubryk import storage as db
from zubryk.catalog import WORD_GROUPS
from zubryk.config import BOT_USERNAME, ENABLE_PREVIEW, ROOT, TIMEZONE
from zubryk.storage.exams import get_attempts, save_attempt
from zubryk.storage.statistics import DAY_LABELS, dashboard
from zubryk.sources import public_sources
from .auth import require_telegram, validate_init_data
from .content import load_content, public_question
from .limits import RateLimiter

log=logging.getLogger("zubryk.api")


def create_app():
    app=Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"]=32768
    limiter=RateLimiter()
    app.before_request(limiter.check)
    try:
        rules, topics, questions=load_content()
        content_error=False
    except (ValueError, KeyError, TypeError, OSError):
        log.error("Учебный контент не прошёл проверку структуры")
        rules,topics,questions={},{},{}
        content_error=True
    version=hashlib.sha256(json.dumps(questions,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:16]

    def require_content():
        if content_error:
            abort(503,description="Учебные материалы временно недоступны")

    def attempts():
        header=request.headers.get("Authorization", "")
        if not header:
            return {}
        try:
            user=validate_init_data(header[4:] if header.startswith("tma ") else "")
        except (ValueError,TypeError):
            abort(401)
        return get_attempts(user["id"],version)

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"]="nosniff"
        response.headers["Referrer-Policy"]="no-referrer"
        response.headers["Permissions-Policy"]="camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"]=(
            "default-src 'self'; script-src 'self' https://telegram.org; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' https: data:; "
            "connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'self'; "
            "frame-ancestors https://web.telegram.org https://*.telegram.org"
        )
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"]="no-store"
        return response

    @app.errorhandler(Exception)
    def error(exc):
        if isinstance(exc,HTTPException):
            return jsonify(error=exc.name.lower().replace(" ","_"),message=exc.description),exc.code
        log.error("API request failed: %s",type(exc).__name__)
        return jsonify(error="server_error",message="Не удалось загрузить данные. Попробуйте ещё раз"),503

    @app.get("/api/health")
    def health():
        conn=db.db_connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            return jsonify(status="ok",contentReady=not content_error,words=sum(len(x["words"]) for x in WORD_GROUPS.values()),topics=len(WORD_GROUPS))
        finally:
            db.db_release(conn)

    @app.get("/api/dashboard")
    @require_telegram
    def get_dashboard():
        data=dashboard(g.user_id,g.telegram_user)
        if data is None:
            return jsonify(error="profile_not_found",message="Сначала создайте профиль в боте",botUsername=BOT_USERNAME),404
        data["botUsername"]=BOT_USERNAME
        return jsonify(data)

    @app.get("/api/preview/dashboard")
    def preview_dashboard():
        if not ENABLE_PREVIEW:
            abort(404)
        today=datetime.now(TIMEZONE).date()
        dates=[today-timedelta(days=i) for i in range(6,-1,-1)]
        return jsonify(profile=None,preview=True,botUsername=BOT_USERNAME,timezone=str(TIMEZONE),
            week={"total":0,"days":[{"date":d.isoformat(),"label":DAY_LABELS[d.weekday()],"count":0,"isToday":d==today} for d in dates]},
            topics=[{"key":k,"name":v["name"],"total":len(v["words"]),"learned":0} for k,v in list(WORD_GROUPS.items())[:3]],
            leaders=[],dailyTimeChoices=[{"value":c,"label":l.replace("❌ ","")} for c,l in db.DAILY_TIME_CHOICES])

    @app.patch("/api/settings")
    @require_telegram
    def settings():
        user=db.get_user(g.user_id)
        if not user:
            abort(404,description="Сначала создайте профиль в боте")
        data=request.get_json(silent=True)
        if not isinstance(data,dict) or not data or set(data)-{"name","dailyTime"}:
            abort(400,description="Недопустимые настройки")
        name=data.get("name")
        code=data.get("dailyTime")
        if "name" in data and (not isinstance(name,str) or not 1<=len(name.strip())<=64 or any(ord(c)<32 for c in name)):
            abort(400,description="Имя должно содержать от 1 до 64 символов")
        if "dailyTime" in data and (not isinstance(code,str) or code not in dict(db.DAILY_TIME_CHOICES)):
            abort(400,description="Выберите время из списка")
        if name is not None:
            db.set_name(g.user_id,name.strip())
        if code is not None:
            db.set_daily_time(g.user_id,code)
        return jsonify(dashboard(g.user_id,g.telegram_user))

    @app.get("/api/grammar")
    def grammar():
        require_content()
        query=request.args.get("q","").casefold().strip()[:200]
        category=request.args.get("category","")
        found=[r for r in rules.values() if (not category or r["category"]==category) and (not query or query in json.dumps(r,ensure_ascii=False).casefold())]
        return jsonify(items=sorted(found,key=lambda r:r.get("order",0)),categories=list(dict.fromkeys(r["category"] for r in rules.values())))

    @app.get("/api/content/sources")
    def sources():
        return jsonify(public_sources())

    @app.get("/api/grammar/<rule_id>")
    def grammar_rule(rule_id):
        require_content()
        if rule_id not in rules:
            abort(404)
        return jsonify(rules[rule_id])

    @app.get("/api/exam/topics")
    def exam_topics():
        require_content()
        query=request.args.get("q","").strip().casefold()[:200]
        result=[]
        for topic in topics.values():
            if query and query not in (topic["title"]+" "+topic["description"]).casefold():
                continue
            qs=[q for q in questions.values() if q["topicId"]==topic["id"]]
            result.append({**topic,"questionCount":len(qs),"variants":list(dict.fromkeys(q["variantId"] for q in qs))})
        return jsonify(items=result,notice="Авторские учебные упражнения. Официальные варианты ЦТ / ЦЭ ещё не добавлены.")

    @app.get("/api/exam/topics/<topic_id>/questions")
    def exam_questions(topic_id):
        require_content()
        if topic_id not in topics:
            abort(404)
        variant=request.args.get("variant")
        qs=[q for q in questions.values() if q["topicId"]==topic_id]
        variants=list(dict.fromkeys(q["variantId"] for q in qs))
        if variant and variant not in variants:
            abort(400,description="Вариант недоступен")
        history=attempts()
        result=[]
        for q in qs:
            if variant and variant!=q["variantId"]:
                continue
            item=public_question(q)
            if q["id"] in history:
                item["attempt"]={**history[q["id"]],"correctAnswers":q["correctAnswers"],"explanation":q.get("explanation","")}
            result.append(item)
        return jsonify(topic=topics[topic_id],items=result,variants=variants)

    @app.post("/api/exam/questions/<question_id>/check")
    def check_answer(question_id):
        require_content()
        q=questions.get(question_id)
        if not q:
            abort(404)
        data=request.get_json(silent=True)
        if not isinstance(data,dict) or set(data)-{"answers","preview"}:
            abort(400,description="Неверный формат ответа")
        answers=data.get("answers")
        if not isinstance(answers,list) or not answers or any(not isinstance(a,str) for a in answers) or len(set(answers))!=len(answers):
            abort(400,description="Выберите ответ")
        if not set(answers)<={o["id"] for o in q["options"]} or (q["type"]=="single" and len(answers)!=1):
            abort(400,description="Недопустимые варианты ответа")
        correct=set(answers)==set(q["correctAnswers"])
        if data.get("preview") is True and not request.headers.get("Authorization"):
            if not ENABLE_PREVIEW:
                abort(401)
        else:
            header=request.headers.get("Authorization","")
            try:
                user=validate_init_data(header[4:] if header.startswith("tma ") else "")
            except (ValueError,TypeError):
                abort(401)
            if not db.get_user(user["id"]):
                abort(404,description="Сначала создайте профиль в боте")
            stored=save_attempt(user["id"],q["id"],version,answers,correct)
            if sorted(answers)!=stored["answers"]:
                return jsonify(error="already_answered",message="Это задание уже проверено",**stored,
                               correctAnswers=q["correctAnswers"],explanation=q.get("explanation","")),409
            correct=stored["correct"]
        return jsonify(correct=correct,answers=answers,correctAnswers=q["correctAnswers"],explanation=q.get("explanation",""))

    @app.get("/")
    @app.get("/<path:path>")
    def frontend(path="index.html"):
        root=ROOT / "frontend/dist"
        if path.startswith(("api/","content/",".")):
            abort(404)
        return send_from_directory(root,path if (root/path).is_file() else "index.html")

    return app
