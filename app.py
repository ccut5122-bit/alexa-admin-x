import os,json,time,base64,hashlib,logging,urllib.request,urllib.parse
from flask import Flask, request, send_from_directory

logging.basicConfig(format='%(asctime)s - %(message)s',level=logging.INFO)
log=logging.getLogger('app')

app = Flask(__name__, static_folder=None)
PANEL_DIR = os.path.join(os.path.dirname(__file__), 'panel')

BOT_TOKEN='8965641250:AAF-x_Nrc1IPc5IX01B7Y1IQNsQWdUihwag'
MAIN_ADMIN=8295208785
FIREBASE_URL='https://newrto30-default-rtdb.firebaseio.com'
PIKA_URL='https://pikachu-bykitterfb60-default-rtdb.firebaseio.com'
BIHAR_URL='https://biharnew2-default-rtdb.firebaseio.com'
BIHAR_ROOT='19112024'
ENC_KEY='alexa@adminx!protect'
API_BASE=f'https://api.telegram.org/bot{BOT_TOKEN}'
WEBHOOK_PATH='/webhook'

user_state={}

def tg_call(method,data=None):
    url=f'{API_BASE}/{method}'
    if data:
        req=urllib.request.Request(url,data=urllib.parse.urlencode(data).encode())
        req.add_header('Content-Type','application/x-www-form-urlencoded')
    else:
        req=urllib.request.Request(url)
    try:
        r=urllib.request.urlopen(req,timeout=30)
        return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body=e.read().decode(errors='ignore')
        log.error(f'TG HTTP {e.code} for {method}: {body[:200]}')
        return None
    except Exception as e:
        log.error(f'TG error for {method}: {e}')
        return None

def tg_send(chat_id,text,parse_mode='',reply_markup=None):
    d={'chat_id':chat_id,'text':text}
    if parse_mode:d['parse_mode']=parse_mode
    if reply_markup:d['reply_markup']=json.dumps(reply_markup)
    return tg_call('sendMessage',d)

def tg_delete(chat_id,msg_id):
    return tg_call('deleteMessage',{'chat_id':chat_id,'message_id':msg_id})

def xor_encrypt(text):
    k=ENC_KEY.encode();data=text.encode()
    return base64.b64encode(bytes(data[i]^k[i%len(k)] for i in range(len(data)))).decode()

def xor_decrypt(enc):
    k=ENC_KEY.encode();data=base64.b64decode(enc.encode())
    return bytes(data[i]^k[i%len(k)] for i in range(len(data))).decode()

def fb_put(path,data):
    j=json.dumps(data).encode()
    r=urllib.request.Request(f'{FIREBASE_URL}/{path}.json',data=j,method='PUT')
    r.add_header('Content-Type','application/json')
    return json.loads(urllib.request.urlopen(r,timeout=15).read())

def fb_get(path):
    try:
        r=urllib.request.urlopen(f'{FIREBASE_URL}/{path}.json',timeout=10)
        return json.loads(r.read())
    except: return None

def fb_delete(path):
    r=urllib.request.Request(f'{FIREBASE_URL}/{path}.json',method='DELETE')
    return json.loads(urllib.request.urlopen(r,timeout=15).read())

def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()[:16]

def is_sub_admin(uid):
    ad=fb_get('asia_protection/admins')
    return ad and str(uid) in ad

def is_admin(uid):
    return uid==MAIN_ADMIN or is_sub_admin(uid)

def btn(text,callback_data):
    return {'text':text,'callback_data':callback_data}

def row(*btns):
    return list(btns)

def main_menu_keyboard(is_main):
    kb=[]
    kb.append(row(btn('🔑 Set Password','setpass'),btn('🗑 Delete Password','delpass')))
    if is_main:
        kb.append(row(btn('➕ Add Admin','addadmin'),btn('❌ Remove Admin','rmadmin')))
    kb.append(row(btn('📋 List Passwords','listpass'),btn('👥 Admins','listadmins')))
    if is_main:
        kb.append(row(btn('👤 My ID','myid')))
    return {'inline_keyboard':kb}

def cmd_start(chat_id,uid):
    if not is_admin(uid):
        tg_send(chat_id,'⛔ *ACCESS DENIED*',parse_mode='Markdown'); return
    tg_send(chat_id,'🏆 *ALEXA ADMIN X* 🏆\n\nPremium Panel Management\n\n_All data encrypted & secure_',
        parse_mode='Markdown',reply_markup=main_menu_keyboard(uid==MAIN_ADMIN))

def cmd_listpass(chat_id,uid):
    pwds=fb_get('asia_protection/passwords')
    if not pwds:
        tg_send(chat_id,'📭 *No passwords set*',parse_mode='Markdown',
            reply_markup={'inline_keyboard':[[btn('🔙 Back','menu')]]}); return
    msg='📋 *Panel Passwords*\n\n'
    for pid,data in pwds.items():
        try: p=xor_decrypt(data.get('p',''))
        except: p='???'
        active='✅' if data.get('a')!='0' else '❌'
        browser='🔒' if data.get('b') else '🔓'
        last=data.get('l','Never')
        if last!='Never':
            try:
                mins=int((time.time()-int(last))/60)
                if mins<60: last=f'{mins}m ago'
                else: last=f'{mins//60}h {mins%60}m ago'
            except: pass
        msg+=f'`{p}` {active} {browser} | last: {last}\n'
    if len(msg)>4000:
        for i in range(0,len(msg),4000):
            tg_send(chat_id,msg[i:i+4000],parse_mode='Markdown')
    else:
        tg_send(chat_id,msg,parse_mode='Markdown',
            reply_markup={'inline_keyboard':[[btn('🔙 Back','menu')]]})

def cmd_listadmins(chat_id,uid):
    existing=fb_get('asia_protection/admins') or {}
    msg='👥 *Sub-Admins*\n\n'
    if not existing: msg+='None'
    else:
        for aid,ts in existing.items():
            msg+=f'• `{aid}`\n'
    tg_send(chat_id,msg,parse_mode='Markdown',
        reply_markup={'inline_keyboard':[[btn('🔙 Back','menu')]]})

def handle_callback(cb):
    cb_id=cb['id'];data=cb['data']
    chat_id=cb['message']['chat']['id'];msg_id=cb['message']['message_id'];uid=cb['from']['id']
    if data=='menu':
        tg_delete(chat_id,msg_id);cmd_start(chat_id,uid)
        tg_call('answerCallbackQuery',{'callback_query_id':cb_id})
    elif data=='cancel':
        user_state.pop(uid,None);tg_delete(chat_id,msg_id)
        tg_call('answerCallbackQuery',{'callback_query_id':cb_id,'text':'Cancelled'})
        cmd_start(chat_id,uid)
    elif data=='setpass':
        tg_call('answerCallbackQuery',{'callback_query_id':cb_id});tg_delete(chat_id,msg_id)
        if not is_admin(uid):return
        user_state[uid]={'action':'awaiting_pass','is_main':uid==MAIN_ADMIN}
        tg_send(chat_id,'🔑 *Set Password*\n\nEnter password (4-20 chars):',parse_mode='Markdown',
            reply_markup={'inline_keyboard':[[btn('❌ Cancel','cancel')]]})
    elif data=='delpass':
        tg_call('answerCallbackQuery',{'callback_query_id':cb_id});tg_delete(chat_id,msg_id)
        if uid!=MAIN_ADMIN:return
        user_state[uid]={'action':'awaiting_delpass'}
        tg_send(chat_id,'🗑 *Delete Password*\n\nEnter password to delete:',parse_mode='Markdown',
            reply_markup={'inline_keyboard':[[btn('❌ Cancel','cancel')]]})
    elif data=='listpass':
        tg_call('answerCallbackQuery',{'callback_query_id':cb_id});tg_delete(chat_id,msg_id)
        cmd_listpass(chat_id,uid)
    elif data=='addadmin':
        tg_call('answerCallbackQuery',{'callback_query_id':cb_id});tg_delete(chat_id,msg_id)
        if uid!=MAIN_ADMIN:return
        user_state[uid]={'action':'awaiting_addadmin'}
        tg_send(chat_id,'➕ *Add Admin*\n\nSend Telegram ID:',parse_mode='Markdown',
            reply_markup={'inline_keyboard':[[btn('❌ Cancel','cancel')]]})
    elif data=='rmadmin':
        tg_call('answerCallbackQuery',{'callback_query_id':cb_id});tg_delete(chat_id,msg_id)
        if uid!=MAIN_ADMIN:return
        existing=fb_get('asia_protection/admins') or {}
        if not existing:
            tg_send(chat_id,'📭 No sub-admins',reply_markup={'inline_keyboard':[[btn('🔙 Back','menu')]]});return
        kb=[[btn(f'❌ {aid}','rmadmin_'+aid)] for aid in existing]
        kb.append([btn('🔙 Back','menu')])
        tg_send(chat_id,'🗑 *Remove Admin*',parse_mode='Markdown',reply_markup={'inline_keyboard':kb})
    elif data=='listadmins':
        tg_call('answerCallbackQuery',{'callback_query_id':cb_id});tg_delete(chat_id,msg_id)
        cmd_listadmins(chat_id,uid)
    elif data=='myid':
        tg_call('answerCallbackQuery',{'callback_query_id':cb_id,'text':f'Your ID: {uid}'})
    elif data.startswith('rmadmin_'):
        if uid!=MAIN_ADMIN:return
        aid=data.split('_',1)[1]
        existing=fb_get('asia_protection/admins') or {}
        if aid in existing:
            del existing[aid];fb_put('asia_protection/admins',existing)
            tg_call('answerCallbackQuery',{'callback_query_id':cb_id,'text':'✅ Removed'})
            tg_delete(chat_id,msg_id);cmd_listadmins(chat_id,uid)

def handle_msg(msg):
    if 'text' not in msg: return
    chat_id=msg['chat']['id'];uid=msg['from']['id'];text=msg['text'].strip()
    parts=text.split();cmd=parts[0].lower()
    if uid in user_state:
        state=user_state[uid];action=state.get('action')
        if action=='awaiting_pass':
            if len(text)<4 or len(text)>20:
                tg_send(chat_id,'❌ 4-20 chars',reply_markup={'inline_keyboard':[[btn('❌ Cancel','cancel')]]});return
            pid=hash_pass(text)
            entry={'p':xor_encrypt(text),'b':'','a':'1' if uid==MAIN_ADMIN else '0',
                   't':str(int(time.time())),'l':'','u':str(uid)}
            fb_put(f'asia_protection/passwords/{pid}',entry)
            user_state.pop(uid,None)
            tg_send(chat_id,f'✅ *SET:* `{text}`',parse_mode='Markdown',
                reply_markup={'inline_keyboard':[[btn('🔙 Back','menu')]]});return
        elif action=='awaiting_delpass':
            if uid!=MAIN_ADMIN: user_state.pop(uid,None);return
            pid=hash_pass(text);fb_delete(f'asia_protection/passwords/{pid}')
            user_state.pop(uid,None)
            tg_send(chat_id,f'🗑 *DELETED*',parse_mode='Markdown',
                reply_markup={'inline_keyboard':[[btn('🔙 Back','menu')]]});return
        elif action=='awaiting_addadmin':
            if uid!=MAIN_ADMIN: user_state.pop(uid,None);return
            try: aid=str(int(text.strip()))
            except:
                tg_send(chat_id,'❌ Invalid ID',reply_markup={'inline_keyboard':[[btn('❌ Cancel','cancel')]]});return
            existing=fb_get('asia_protection/admins') or {}
            existing[aid]=str(int(time.time()));fb_put('asia_protection/admins',existing)
            user_state.pop(uid,None)
            tg_send(chat_id,f'✅ *ADDED:* `{aid}`',parse_mode='Markdown',
                reply_markup={'inline_keyboard':[[btn('🔙 Back','menu')]]});return
        if text.startswith('/') or text.lower()=='cancel':
            user_state.pop(uid,None);tg_send(chat_id,'❌ Cancelled');cmd_start(chat_id,uid);return
    if cmd=='/start':cmd_start(chat_id,uid)
    elif cmd=='/setpass':
        if not is_admin(uid):return
        user_state[uid]={'action':'awaiting_pass'}
        tg_send(chat_id,'🔑 *Set Password*\n\nEnter password (4-20 chars):',parse_mode='Markdown',
            reply_markup={'inline_keyboard':[[btn('❌ Cancel','cancel')]]})
    elif cmd=='/delpass' and uid==MAIN_ADMIN:
        user_state[uid]={'action':'awaiting_delpass'}
        tg_send(chat_id,'🗑 *Delete Password*\n\nEnter password:',parse_mode='Markdown',
            reply_markup={'inline_keyboard':[[btn('❌ Cancel','cancel')]]})
    elif cmd in ('/passwords','/list'):cmd_listpass(chat_id,uid)
    elif cmd=='/addadmin' and uid==MAIN_ADMIN:
        user_state[uid]={'action':'awaiting_addadmin'}
        tg_send(chat_id,'➕ *Add Admin*\n\nSend ID:',parse_mode='Markdown',
            reply_markup={'inline_keyboard':[[btn('❌ Cancel','cancel')]]})
    elif cmd in ('/admins','/adminlist') and uid==MAIN_ADMIN:cmd_listadmins(chat_id,uid)
    elif cmd=='/myid':tg_send(chat_id,f'👤 Your ID: `{uid}`',parse_mode='Markdown')

@app.route('/')
def serve_index():
    return send_from_directory(PANEL_DIR, 'xin.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(PANEL_DIR, path)

@app.route('/health')
def health():
    return 'ok', 200

@app.route('/api/fb/<path:fb_path>')
def api_fb(fb_path):
    return api_proxy(fb_path, FIREBASE_URL)

@app.route('/api/pika/<path:fb_path>')
def api_pika(fb_path):
    return api_proxy(fb_path, PIKA_URL)

@app.route('/api/bihar/<path:fb_path>')
def api_bihar(fb_path):
    return api_proxy(fb_path, BIHAR_URL, BIHAR_ROOT)

def api_proxy(fb_path, base_url, root=''):
    try:
        full_path = f'{root}/{fb_path}' if root else fb_path
        r=urllib.request.urlopen(f'{base_url}/{full_path}.json',timeout=15)
        d=json.loads(r.read())
    except:
        return json.dumps(None),200,{'Content-Type':'application/json'}
    return json.dumps(d),200,{'Content-Type':'application/json'}

@app.route('/api/verify_pass', methods=['POST'])
def verify_pass():
    data=request.get_json(force=True)
    p=data.get('password','')
    pid=hash_pass(p)
    pwds=fb_get('asia_protection/passwords')
    if pwds and pid in pwds:
        entry=pwds[pid]
        if entry.get('a')!='0':
            return json.dumps({'ok':True}),200,{'Content-Type':'application/json'}
    return json.dumps({'ok':False}),200,{'Content-Type':'application/json'}

@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    try:
        update=request.get_json(force=True)
        if 'callback_query' in update:
            handle_callback(update['callback_query'])
        elif 'message' in update:
            handle_msg(update['message'])
        return 'ok', 200
    except Exception as e:
        log.error(f'Webhook error: {e}')
        return 'error', 500

def set_webhook():
    base_url = os.environ.get('RENDER_EXTERNAL_URL', '')
    if not base_url:
        log.warning('RENDER_EXTERNAL_URL not set - skipping webhook setup')
        return
    webhook_url = base_url.rstrip('/') + WEBHOOK_PATH
    tg_call('deleteWebhook')
    r = tg_call('setWebhook', {'url': webhook_url, 'allowed_updates': json.dumps(['message', 'callback_query'])})
    if r and r.get('ok'):
        log.info(f'Webhook set to {webhook_url}')
    else:
        log.error(f'Failed to set webhook: {r}')

def bot_polling():
    log.info('Starting bot polling mode...')
    offset=0
    while True:
        try:
            r=tg_call('getUpdates',{'offset':offset,'allowed_updates':json.dumps(['message','callback_query'])})
            if r and r.get('ok'):
                for update in r['result']:
                    offset=update['update_id']+1
                    if 'callback_query' in update:
                        handle_callback(update['callback_query'])
                    elif 'message' in update:
                        handle_msg(update['message'])
                if not r['result']:
                    time.sleep(2)
            else:
                time.sleep(3)
        except Exception as e:
            log.error(f'Polling error: {e}')
            time.sleep(5)

if __name__=='__main__':
    base_url = os.environ.get('RENDER_EXTERNAL_URL', '')
    if base_url:
        set_webhook()
    else:
        import threading
        t=threading.Thread(target=bot_polling, daemon=True)
        t.start()
        log.info('Bot polling thread started')
    port=int(os.environ.get('PORT',8080))
    app.run(host='0.0.0.0',port=port)
