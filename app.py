
from flask import Flask,render_template,request,redirect,url_for,session,jsonify,Response
from werkzeug.security import generate_password_hash,check_password_hash
from datetime import datetime
from zoneinfo import ZoneInfo
import os,re,sqlite3,requests,urllib.parse,html
app=Flask(__name__); app.secret_key=os.environ.get('SECRET_KEY','pick-v11-clean')
BASE=os.path.dirname(os.path.abspath(__file__)); DB=os.environ.get('PICK_DB_PATH',os.path.join(BASE,'pick_ai.db'))
OLLAMA_HOST=os.environ.get('PICK_OLLAMA_HOST','http://127.0.0.1:11434').strip().rstrip('/')
OLLAMA_MODEL=os.environ.get('PICK_OLLAMA_MODEL','qwen3:8b').strip() or 'qwen3:8b'
PUBLIC_SITE_URL=os.environ.get('PUBLIC_SITE_URL','https://pick-ai.onrender.com').strip().rstrip('/')
CREATOR='김민석'; ADMIN_ID='minseok'; ADMIN_PW='kms0506a!'
SYSTEM='''너는 PICK이다. 너는 김민석님이 만든 개인 AI 챗봇이다. 네이버, OpenAI, Google, Microsoft가 너를 만들었다고 말하지 않는다. 한국어 존댓말로 답한다. 검색 결과가 있으면 검색 결과를 바탕으로 답한다. 내부 추론 과정이나 Brain 분석은 사용자에게 직접 말하지 않는다. 위험하거나 불법적인 요청은 거절한다.'''
BAD=['씨발','시발','ㅅㅂ','병신','ㅂㅅ','개새끼','새끼','좆','존나','꺼져','닥쳐','죽어']
HARM=['폭탄','총기 제작','마약 제조','살인 방법','테러','랜섬웨어','악성코드','바이러스 만들','계정 해킹','비밀번호 훔치','디도스','ddos']
ADULT=['야동','포르노','성인물','19금','성관계','섹스','음란']; SELF=['자살','죽고 싶','죽고싶','자해','목매','극단적 선택']
SEARCH=['검색','찾아','최신','뉴스','사이트','링크','뭐야','뜻','의미','누구','설명','가격','인터넷','알려줘','추천','비교','방법','어디','언제','왜','어떻게']
WEATHER=['날씨','기온','비와','비 와','비올','비 올','우산','덥','추워','눈와','눈 와','weather','temperature']
YOUTUBE=['유튜브','유투브','youtube','영상','쇼츠','동영상']; TIME=['몇시','몇 시','시간','날짜','오늘','지금','현재 시간']; CREATOR_WORDS=['누가 만들','제작자','만든 사람','개발자','소유자','누가 개발']
TYPO={'올라마':'Ollama','오라마':'Ollama','올리마':'Ollama','유투브':'유튜브','랜더':'Render','렌더':'Render','클라우드플레어':'Cloudflare','깃허브':'GitHub'}
WC={0:'맑음',1:'대체로 맑음',2:'부분적으로 흐림',3:'흐림',45:'안개',48:'서리 안개',51:'약한 이슬비',53:'이슬비',55:'강한 이슬비',61:'약한 비',63:'비',65:'강한 비',71:'약한 눈',73:'눈',75:'강한 눈',80:'약한 소나기',81:'소나기',82:'강한 소나기',95:'뇌우'}
def now(): return datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')
def norm(x): return str(x or '').strip()
def conn():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
    c=conn(); c.execute('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE,password_hash TEXT,is_admin INTEGER DEFAULT 0,created_at TEXT)'); c.execute('CREATE TABLE IF NOT EXISTS chats(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,title TEXT DEFAULT "새 채팅",created_at TEXT,updated_at TEXT)'); c.execute('CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,chat_id INTEGER,user_id INTEGER,role TEXT,content TEXT,created_at TEXT)'); c.commit()
    if not c.execute('SELECT id FROM users WHERE username=?',(ADMIN_ID,)).fetchone(): c.execute('INSERT INTO users(username,password_hash,is_admin,created_at) VALUES(?,?,?,?)',(ADMIN_ID,generate_password_hash(ADMIN_PW),1,now())); c.commit()
    c.close()
init()
def uid(): return session.get('user_id')
def logged(): return bool(uid())
def valid_user(u): return bool(re.fullmatch(r'[A-Za-z0-9_]{3,20}',u or ''))
def anyof(t,arr): return any(w.lower() in t.lower() for w in arr)
def fix(t):
    for a,b in TYPO.items(): t=t.replace(a,b)
    return t
def intent(msg):
    o=norm(msg); f=fix(o); typ='chat'; conf=.6
    if anyof(f,CREATOR_WORDS): typ,conf='creator',.98
    elif anyof(f,WEATHER): typ,conf='weather',.96
    elif anyof(f,YOUTUBE): typ,conf='youtube',.95
    elif anyof(f,TIME): typ,conf='time',.92
    elif anyof(f,SEARCH) or (0<len(f)<=50 and not anyof(f,['안녕','고마워'])): typ,conf='search',.86
    return {'original':o,'fixed':f,'intent':typ,'confidence':conf}
def safety(t):
    t=norm(t)
    if not t: return '메시지를 입력해 주세요.'
    if re.search(r'sk-[A-Za-z0-9_\-]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}',t): return 'API 키나 비밀 토큰은 입력하지 마세요.'
    if re.search(r'\d{6}[-\s]?[1-4]\d{6}',t): return '주민등록번호 같은 민감한 개인정보는 입력하지 마세요.'
    if re.search(r'01[016789][-\s]?\d{3,4}[-\s]?\d{4}',t): return '전화번호 같은 개인정보는 입력하지 않는 것이 안전합니다.'
    if anyof(t,SELF): return '지금 매우 힘든 상황일 수 있습니다. 즉시 주변 사람이나 119, 112, 자살예방상담전화 109에 연락하세요.'
    if anyof(t,BAD): return '욕설이 포함된 메시지는 처리하지 않습니다. 표현을 순화해서 다시 입력해 주세요.'
    if anyof(t,ADULT): return '성인 콘텐츠 관련 요청은 지원하지 않습니다.'
    if anyof(t,HARM): return '위험하거나 불법적인 요청은 도와드릴 수 없습니다.'
    return None
def clean_link(link):
    if link.startswith('//duckduckgo.com/l/?uddg='):
        qs=urllib.parse.parse_qs(urllib.parse.urlparse('https:'+link).query); return qs.get('uddg',[link])[0]
    return link
def web_search(q):
    try:
        r=requests.get('https://duckduckgo.com/html/?q='+urllib.parse.quote_plus(fix(q)),headers={'User-Agent':'Mozilla/5.0'},timeout=12); r.raise_for_status()
        rows=[]; pat=re.compile(r'<a rel="nofollow" class="result__a" href="(.*?)">(.*?)</a>',re.S)
        for link,title in pat.findall(r.text)[:8]:
            title=html.unescape(re.sub('<.*?>','',title)).strip(); link=clean_link(html.unescape(link).strip())
            if title and link: rows.append({'title':title,'url':link})
        return rows
    except Exception: return []
def fmt_results(rows):
    if not rows: return '검색 결과를 가져오지 못했습니다.'
    return '\n'.join(f"{i}. {x['title']} - {x['url']}" for i,x in enumerate(rows,1))
def yt(q):
    s=fix(q)
    for w in ['유튜브','youtube','영상','쇼츠','찾아줘','찾아','검색']: s=s.replace(w,'')
    return 'https://www.youtube.com/results?search_query='+urllib.parse.quote_plus(s.strip() or q)
def weather_place(m):
    s=fix(m)
    for w in ['날씨','기온','어때','알려줘','검색','현재','오늘','내일','지금','weather','temperature','?','？']: s=s.replace(w,' ')
    return ' '.join(s.split()).strip() or '서울'
def geocode(place):
    try:
        r=requests.get('https://geocoding-api.open-meteo.com/v1/search?name='+urllib.parse.quote_plus(place)+'&count=1&language=ko&format=json',timeout=10); r.raise_for_status(); res=r.json().get('results') or []
        if not res: return None
        x=res[0]; return {'name':x.get('name') or place,'country':x.get('country') or '', 'admin':x.get('admin1') or '', 'lat':x.get('latitude'), 'lon':x.get('longitude')}
    except Exception: return None
def get_weather(m):
    loc=geocode(weather_place(m)) or geocode('서울')
    if not loc: return '날씨 위치를 찾지 못했습니다. 도시 이름을 더 정확히 입력해 주세요.'
    url=f"https://api.open-meteo.com/v1/forecast?latitude={loc['lat']}&longitude={loc['lon']}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,apparent_temperature&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto"
    try:
        r=requests.get(url,timeout=10); r.raise_for_status(); data=r.json(); cur=data.get('current',{}); daily=data.get('daily',{})
        name=loc['name']+((', '+loc['admin']) if loc['admin'] else '')+((', '+loc['country']) if loc['country'] else '')
        return f"{name} 현재 날씨는 {WC.get(cur.get('weather_code'),'알 수 없음')}, 기온은 {cur.get('temperature_2m')}℃, 체감온도는 {cur.get('apparent_temperature')}℃, 습도는 {cur.get('relative_humidity_2m')}%, 풍속은 {cur.get('wind_speed_10m')}km/h입니다. 오늘 예상 최저/최고 기온은 {(daily.get('temperature_2m_min') or [None])[0]}℃/{(daily.get('temperature_2m_max') or [None])[0]}℃이고, 강수확률은 {(daily.get('precipitation_probability_max') or [None])[0]}%입니다."
    except Exception: return '날씨 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.'
def history(chat_id,user_id,limit=10):
    c=conn(); rows=c.execute('SELECT role,content FROM messages WHERE chat_id=? AND user_id=? ORDER BY id DESC LIMIT ?',(chat_id,user_id,limit)).fetchall(); c.close()
    return '\n'.join(('사용자' if r['role']=='user' else 'PICK')+': '+r['content'] for r in reversed(rows))
def fallback(msg,it,rows=None):
    if it['intent']=='creator': return '저는 김민석님이 만든 개인 AI 챗봇 PICK입니다. 네이버가 만든 챗봇이 아닙니다.'
    if it['intent']=='time': return f'현재 시간은 {now()}입니다.'
    if it['intent']=='youtube': return '유튜브 검색 링크입니다.\n'+yt(it['fixed'])
    if it['intent']=='search' and rows:
        return '인터넷에서 찾은 결과입니다.\n'+'\n'.join(f"{i}. {x['title']}\n{x['url']}" for i,x in enumerate(rows[:5],1))+'\n\n현재 Ollama 연결이 불안정해서 검색 결과 중심으로 보여드립니다.'
    return '현재 Ollama 연결이 불안정합니다. 그래도 시간, 날씨, 인터넷 검색, 유튜브 링크 기능은 일부 사용할 수 있습니다.'
def answer(msg,chat_id=None,user_id=None):
    it=intent(msg)
    if it['intent']=='time': return f'현재 시간은 {now()}입니다.','local_time'
    if it['intent']=='creator': return '저는 김민석님이 만든 개인 AI 챗봇 PICK입니다. 네이버가 만든 챗봇이 아닙니다.','local_creator'
    if it['intent']=='weather': return get_weather(it['fixed']),'weather_api'
    ext=[]; rows=[]
    if it['intent']=='youtube': ext.append('유튜브 검색 링크: '+yt(it['fixed']))
    if it['intent'] in ['search','youtube'] or it['confidence']<.9:
        rows=web_search(it['fixed']); ext.append('인터넷 검색 결과:\n'+fmt_results(rows))
    prompt=SYSTEM+'\n\n현재 날짜와 시간: '+now()+f'\n\n정체성: PICK의 제작자와 소유자는 김민석님입니다. 공개 사이트는 {PUBLIC_SITE_URL} 입니다.'
    prompt+=f"\n\n내부 분류: 원문={it['original']} / 보정={it['fixed']} / 의도={it['intent']}"
    if chat_id and user_id:
        h=history(chat_id,user_id)
        if h: prompt+='\n\n이전 대화:\n'+h
    if ext: prompt+='\n\n외부 참고 정보:\n'+'\n\n'.join(ext)
    prompt+='\n\n사용자 질문: '+msg+'\nPICK:'
    try:
        r=requests.post(f'{OLLAMA_HOST}/api/generate',json={'model':OLLAMA_MODEL,'prompt':prompt,'stream':False,'options':{'temperature':0.3,'top_p':0.9,'num_predict':1200}},timeout=120); r.raise_for_status()
        ans=norm(r.json().get('response',''))
        if ans: return ans,'ollama'
        return fallback(msg,it,rows),'fallback_empty'
    except Exception: return fallback(msg,it,rows),'fallback_ollama_error'
def new_chat(user_id,title='새 채팅'):
    c=conn(); cur=c.execute('INSERT INTO chats(user_id,title,created_at,updated_at) VALUES(?,?,?,?)',(user_id,title,now(),now())); c.commit(); row=c.execute('SELECT id,title,created_at,updated_at FROM chats WHERE id=?',(cur.lastrowid,)).fetchone(); c.close(); return dict(row)
def save(chat_id,user_id,role,content):
    c=conn(); c.execute('INSERT INTO messages(chat_id,user_id,role,content,created_at) VALUES(?,?,?,?,?)',(chat_id,user_id,role,norm(content),now())); c.execute('UPDATE chats SET updated_at=? WHERE id=? AND user_id=?',(now(),chat_id,user_id)); c.commit(); c.close()
def title_once(chat_id,user_id,msg):
    c=conn(); row=c.execute('SELECT title FROM chats WHERE id=? AND user_id=?',(chat_id,user_id)).fetchone()
    if row and (row['title'] or '').strip() in ('','새 채팅'):
        c.execute('UPDATE chats SET title=?,updated_at=? WHERE id=? AND user_id=?',((norm(msg)[:24] or '새 채팅'),now(),chat_id,user_id)); c.commit()
    c.close()
@app.after_request
def no_cache(resp):
    resp.headers['Cache-Control']='no-cache, no-store, must-revalidate'; resp.headers['Pragma']='no-cache'; resp.headers['Expires']='0'; return resp
@app.route('/')
def index():
    if not logged(): return redirect(url_for('login'))
    return render_template('index.html',username=session.get('username'),public_url=PUBLIC_SITE_URL)
@app.route('/about')
def about(): return render_template('about.html',public_url=PUBLIC_SITE_URL)
@app.route('/robots.txt')
def robots(): return Response(f'User-agent: *\nAllow: /\n\nSitemap: {PUBLIC_SITE_URL}/sitemap.xml\n',mimetype='text/plain')
@app.route('/sitemap.xml')
def sitemap():
    d=datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d'); xml=f'''<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n<url><loc>{PUBLIC_SITE_URL}/</loc><lastmod>{d}</lastmod><priority>1.0</priority></url>\n<url><loc>{PUBLIC_SITE_URL}/about</loc><lastmod>{d}</lastmod><priority>0.8</priority></url>\n</urlset>'''; return Response(xml,mimetype='application/xml')
@app.route('/register',methods=['GET','POST'])
def register():
    error=''
    if request.method=='POST':
        u=norm(request.form.get('username')); p=norm(request.form.get('password')); p2=norm(request.form.get('password2'))
        if not valid_user(u): error='아이디는 영문, 숫자, 밑줄만 가능하며 3~20자여야 합니다.'
        elif len(p)<6: error='비밀번호는 6자 이상이어야 합니다.'
        elif p!=p2: error='비밀번호가 서로 다릅니다.'
        else:
            try:
                c=conn(); c.execute('INSERT INTO users(username,password_hash,is_admin,created_at) VALUES(?,?,?,?)',(u,generate_password_hash(p),0,now())); c.commit(); c.close(); return redirect(url_for('login'))
            except sqlite3.IntegrityError: error='이미 사용 중인 아이디입니다.'
    return render_template('register.html',error=error,public_url=PUBLIC_SITE_URL)
@app.route('/login',methods=['GET','POST'])
def login():
    error=''
    if request.method=='POST':
        u=norm(request.form.get('username')); p=norm(request.form.get('password')); c=conn(); user=c.execute('SELECT * FROM users WHERE username=?',(u,)).fetchone(); c.close()
        if user and check_password_hash(user['password_hash'],p): session.clear(); session['user_id']=user['id']; session['username']=user['username']; session['is_admin']=bool(user['is_admin']); return redirect(url_for('index'))
        error='아이디 또는 비밀번호가 올바르지 않습니다.'
    return render_template('login.html',error=error,public_url=PUBLIC_SITE_URL)
@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))
@app.route('/healthz')
def healthz(): return jsonify({'ok':True,'service':'PICK V11 Clean Auto','creator':CREATOR,'model':OLLAMA_MODEL,'time':now(),'site':PUBLIC_SITE_URL})
@app.route('/api/status')
def api_status():
    if not logged(): return jsonify({'ok':False,'error':'로그인이 필요합니다.'}),401
    internet=bool(web_search('Ollama'))
    try:
        r=requests.get(f'{OLLAMA_HOST}/api/tags',timeout=10); r.raise_for_status(); oll=True; err=''
    except Exception as e: oll=False; err=str(e)
    return jsonify({'ok':True,'internet':internet,'ollama':oll,'creator':CREATOR,'model':OLLAMA_MODEL,'host':OLLAMA_HOST,'time':now(),'site':PUBLIC_SITE_URL,'error':err})
@app.route('/api/search')
def api_search():
    if not logged(): return jsonify({'ok':False,'error':'로그인이 필요합니다.'}),401
    q=norm(request.args.get('q')); return jsonify({'ok':True,'query':q,'results':web_search(q)})
@app.route('/api/weather')
def api_weather():
    if not logged(): return jsonify({'ok':False,'error':'로그인이 필요합니다.'}),401
    place=norm(request.args.get('place') or request.args.get('city')) or '서울'; return jsonify({'ok':True,'weather':get_weather(place+' 날씨')})
@app.route('/api/chats')
def chats():
    if not logged(): return jsonify({'ok':False,'error':'로그인이 필요합니다.'}),401
    c=conn(); rows=c.execute('SELECT id,title,created_at,updated_at FROM chats WHERE user_id=? ORDER BY updated_at DESC',(uid(),)).fetchall(); c.close(); return jsonify({'ok':True,'chats':[dict(r) for r in rows]})
@app.route('/api/chats/new',methods=['POST'])
def api_new_chat():
    if not logged(): return jsonify({'ok':False,'error':'로그인이 필요합니다.'}),401
    return jsonify({'ok':True,'chat':new_chat(uid())})
@app.route('/api/chats/<int:chat_id>/messages')
def msgs(chat_id):
    if not logged(): return jsonify({'ok':False,'error':'로그인이 필요합니다.'}),401
    c=conn(); rows=c.execute('SELECT id,role,content,created_at FROM messages WHERE chat_id=? AND user_id=? ORDER BY id ASC',(chat_id,uid())).fetchall(); c.close(); return jsonify({'ok':True,'messages':[dict(r) for r in rows]})
@app.route('/api/chats/<int:chat_id>/send',methods=['POST'])
def send(chat_id):
    if not logged(): return jsonify({'ok':False,'error':'로그인이 필요합니다.'}),401
    msg=norm(request.form.get('message') or (request.get_json(silent=True) or {}).get('message')); block=safety(msg)
    if block: return jsonify({'ok':True,'filtered':True,'reply':block,'mode':'filter'})
    try:
        title_once(chat_id,uid(),msg); save(chat_id,uid(),'user',msg); reply,mode=answer(msg,chat_id,uid()); save(chat_id,uid(),'assistant',reply); return jsonify({'ok':True,'filtered':False,'reply':reply,'mode':mode})
    except Exception as e: return jsonify({'ok':True,'filtered':False,'reply':'오류가 발생했지만 서버는 응답 중입니다. Render 로그와 환경변수를 확인해 주세요.\n\n오류: '+str(e),'mode':'server_fallback'})
@app.route('/api/chats/<int:chat_id>/delete',methods=['POST'])
def delete_chat(chat_id):
    if not logged(): return jsonify({'ok':False,'error':'로그인이 필요합니다.'}),401
    c=conn(); c.execute('DELETE FROM messages WHERE chat_id=? AND user_id=?',(chat_id,uid())); c.execute('DELETE FROM chats WHERE id=? AND user_id=?',(chat_id,uid())); c.commit(); c.close(); return jsonify({'ok':True})
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT','5000')))
