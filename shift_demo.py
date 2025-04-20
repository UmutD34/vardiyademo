# Shift Demo – Stable with Erken Vardiya and Even Denge
import json, os, random
from datetime import datetime
import pandas as pd
import streamlit as st

PAGE_TITLE = "Şişecam Paşabahçe | Otomatik Vardiya Sistemi"
DATA_FILE = "data.json"
DAYS = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"]

SHIFT_MAP = {
    "Sabah": "09:30‑18:00",
    "Ara":   "11:30‑20:00",
    "Akşam": "13:30‑22:00",
    "H.T":   "Haftalık Tatil",
    "PT":    "Part‑time İzin",
    "Rapor": "Raporlu",
    "Yİ":    "Yıllık İzin",
}
SCENS = {
    "denge": "3 Sabahçı + 3 Akşamcı (eşit bölünür)",
    "ayrik": "Yarı Sabahçı / Yarı Akşamcı (hafta hafta terslenir)",
    "erken": "Erken Vardiya (sevkiyat saati + 2 kişi erken gelme)",
}
DEFAULT_USERS = {"admin":"1234","fatihdemir":"1234","ademkeles":"1234"}

# ─────────── DB Helpers ───────────

def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding='utf-8') as f:
            return json.load(f)
    return {"users": DEFAULT_USERS.copy(), "managers": {}}

def save_db(db):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

if 'db' not in st.session_state:
    st.session_state['db'] = load_db()
DB = st.session_state['db']
DB.setdefault('users', {}).update({u:DEFAULT_USERS[u] for u in DEFAULT_USERS if u not in DB['users']})
DB.setdefault('managers', {})
save_db(DB)

# ─────────── Page Config ───────────

st.set_page_config(page_title=PAGE_TITLE, page_icon='📆', layout='wide')
st.title(PAGE_TITLE)

# ─────────── Auth ───────────

if 'user' not in st.session_state:
    c1, c2 = st.columns(2)
    uname = c1.text_input('Kullanıcı Adı')
    upass = c2.text_input('Şifre', type='password')
    if st.button('Giriş'):
        if DB['users'].get(uname) == upass:
            DB['managers'].setdefault(uname, {
                'employees': [],
                'scenario': {'type':'denge','ask_ara':False,'ship_hour':8.0,'early_days':[]},
                'history': []
            })
            save_db(DB)
            st.session_state['user'] = uname
            st.rerun()
        else:
            st.error('Hatalı kullanıcı / şifre')
    st.stop()

USER = st.session_state['user']
MGR = DB['managers'][USER]
if st.sidebar.button('🔓 Oturumu Kapat'):
    del st.session_state['user']
    st.rerun()

# ─────────── Sidebar Menu ───────────

menu = st.sidebar.radio('🚀 Menü', ['Vardiya Oluştur','Veriler','Geçmiş'])
st.sidebar.markdown('---')
st.sidebar.write(f'👤 {USER}')

# ─────────── Veriler ───────────

if menu == 'Veriler':
    st.header('Senaryo Ayarları')
    keys = list(SCENS.keys()); labels=list(SCENS.values()); idx = keys.index(MGR['scenario']['type'])
    sel_label = st.radio('Senaryo', labels, index=idx)
    scen = keys[labels.index(sel_label)]

    ask_ara = st.checkbox('Ara vardiyaları manuel seç', value=MGR['scenario']['ask_ara'])
    ship = MGR['scenario']['ship_hour']; days_early = MGR['scenario']['early_days']
    if scen == 'erken':
        ship = st.number_input('Sevkiyat Saati (örn. 8.5 = 08:30)', min_value=0.0, max_value=23.5, step=0.5, value=float(ship))
        days_early = st.multiselect('Erken Günler', DAYS, default=days_early)

    if st.button('Kaydet Senaryo'):
        MGR['scenario'] = {'type':scen,'ask_ara':ask_ara,'ship_hour':ship,'early_days':days_early}
        save_db(DB)
        st.success('Kaydedildi')

    st.divider(); st.header('Çalışanlar')
    with st.expander('Yeni Çalışan Ekle'):
        a,b = st.columns(2)
        name = a.text_input('İsim'); code = b.text_input('Sicil')
        is_pt = st.checkbox('Part-time'); ht = st.selectbox('Haftalık Tatil', DAYS)
        pt_days = st.multiselect('PT İzin Günleri', DAYS) if is_pt else []
        if st.button('Ekle', key='add_emp') and name and code:
            MGR['employees'].append({'name':name,'sicil':code,'pt':is_pt,'pt_days':pt_days,'ht_day':ht})
            save_db(DB); st.success('Çalışan eklendi'); st.rerun()

    df_emp = pd.DataFrame(MGR['employees']) if MGR['employees'] else pd.DataFrame(columns=['name','sicil','pt','pt_days','ht_day'])
    edited = st.data_editor(df_emp, num_rows='dynamic', hide_index=True)
    if st.button('Çalışanları Kaydet'):
        tmp = edited.dropna(subset=['name','sicil']).drop_duplicates(subset=['sicil'])
        MGR['employees'] = tmp.to_dict('records')
        save_db(DB); st.success('Kaydedildi'); st.rerun()

# ─────────── Vardiya Oluştur ───────────

if menu == 'Vardiya Oluştur':
    st.header('Yeni Vardiya')
    if not MGR['employees']:
        st.warning('Önce çalışan ekleyin'); st.stop()

    week_start = st.date_input('Haftanın Pazartesi', datetime.today())
    ara_list = st.multiselect('Ara vardiyaları', [e['name'] for e in MGR['employees']]) if MGR['scenario']['ask_ara'] else []

    if 'iz' not in st.session_state: st.session_state['iz'] = {}
    iz = st.session_state['iz']
    with st.expander('İzin / Rapor'):
        emp_sel = st.selectbox('Çalışan', ['—']+[e['name'] for e in MGR['employees']])
        day_sel = st.selectbox('Gün', DAYS)
        type_sel=st.selectbox('Tür',['Rapor','Yıllık İzin'])
        if st.button('Kaydet İzin') and emp_sel!='—':
            iz[emp_sel] = {'day':day_sel,'type':('Rapor' if type_sel=='Rapor' else 'Yİ')}
            st.success('Eklendi')

    scen = MGR['scenario']['type']; early = {}
    if scen == 'erken':
        for d in MGR['scenario']['early_days']:
            # sabahcı adaylar
            early[d] = random.sample([e['name'] for e in MGR['employees']], 2)

    last = MGR['history'][-1]['schedule'] if MGR['history'] else []
    def prev(emp, d): return next((r[d] for r in last if r['Çalışan']==emp), None)

    rows = []
    for idx,e in enumerate(MGR['employees']):
        for di,day in enumerate(DAYS):
            # izin
            ent = iz.get(e['name'])
            if ent and ent['day']==day:
                shift = ent['type']
            elif e['pt'] and day in e['pt_days']:
                shift = 'PT'
            elif day == e['ht_day']:
                shift = 'H.T'
            elif scen == 'erken' and day in MGR['scenario']['early_days'] and e['name'] in early.get(day,[]):
                s = MGR['scenario']['ship_hour']; h=int(s); m=int((s-h)*60)
                h2=int(h+8); m2=int(((s+8)-h2)*60)
                shift = f"{h:02d}:{m:02d}-{h2:02d}:{m2:02d}"
            else:
                if scen == 'denge':
                    half = len(MGR['employees'])/2
                    shift = 'Sabah' if idx < half else 'Akşam'
                else:
                    # ayrık
                    sab = sum(1 for d in DAYS if prev(e['name'],d) in ['Sabah','Ara'])
                    akm = sum(1 for d in DAYS if prev(e['name'],d)=='Akşam')
                    shift = 'Akşam' if sab>akm else 'Sabah'
                # ara
                if e['name'] in ara_list and shift=='Sabah': shift='Ara'
            rows.append({'Çalışan':e['name'],**{day:shift for day in [day]}})
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    MGR['history'].append({'week_start':str(week_start),'schedule':rows})
    save_db(DB); st.session_state['iz'] = {}
    st.download_button('Excel’e Aktar', df.to_csv(index=False).encode('utf-8-sig'))

# ─────────── Geçmiş ───────────

if menu=='Geçmiş':
    st.header('Geçmiş Vardiyalar')
    hist=MGR['history']
    if not hist: st.info('Kayıt yok')
    else:
        sel=st.selectbox('Hafta',[h['week_start'] for h in hist])
        rec = next(h for h in hist if h['week_start']==sel)
        st.dataframe(pd.DataFrame(rec['schedule']), use_container_width=True)
