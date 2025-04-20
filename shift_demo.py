# Shift Demo – Hata Düzeltildi ve Son Stabil Sürüm
import json, os, random
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

PAGE_TITLE = "Şişecam Paşabahçe | Otomatik Vardiya Sistemi"
DATA_FILE = "data.json"
DAYS = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"]

# Standart vardiya zamanları
SHIFT_TIMES = {
    'Sabah': ('09:30','18:00'),
    'Ara':   ('11:30','20:00'),
    'Akşam': ('13:30','22:00')
}
# Özel etiketler
SPECIAL = {'H.T':'Haftalık Tatil','PT':'Part‑time İzin','Rapor':'Raporlu','Yİ':'Yıllık İzin'}
# Senaryolar
SCENS = {'denge':'3 Sabahçı + 3 Akşamcı','ayrik':'Yarı Sabahçı/Yarı Akşamcı (hafta ters)','erken':'Erken Vardiya'}
# Default kullanıcılar
DEFAULT_USERS = {'admin':'1234','fatihdemir':'1234','ademkeles':'1234'}

# DB yükleme ve kaydetme

def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE,encoding='utf-8') as f:
            return json.load(f)
    return {'users':DEFAULT_USERS.copy(),'managers':{}}

def save_db(db):
    with open(DATA_FILE,'w',encoding='utf-8') as f:
        json.dump(db,f,ensure_ascii=False,indent=2)

if 'db' not in st.session_state:
    st.session_state['db'] = load_db()
DB = st.session_state['db']
DB.setdefault('users', {}).update({u:DEFAULT_USERS[u] for u in DEFAULT_USERS if u not in DB['users']})
DB.setdefault('managers', {})
save_db(DB)

# Sayfa düzeni
st.set_page_config(page_title=PAGE_TITLE, page_icon='📆', layout='wide')
st.markdown(
    """
    <style>
    div.block-container{padding-top:2rem}
    .stButton>button{border-radius:6px;font-weight:600}
    </style>
    """,
    unsafe_allow_html=True
)
st.title(PAGE_TITLE)

# Kullanıcı doğrulama
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
            st.error('Hatalı kullanıcı/şifre')
    st.stop()

USER = st.session_state['user']
MGR = DB['managers'][USER]
# Scenario alanlarını denetle
MGR.setdefault('scenario', {})
for key, val in [('type','denge'),('ask_ara',False),('ship_hour',8.0),('early_days',[])]:
    MGR['scenario'].setdefault(key, val)
save_db(DB)

# Oturumu kapatma
if st.sidebar.button('🔓 Oturumu Kapat'):
    del st.session_state['user']
    st.rerun()
st.sidebar.markdown(f"**Kullanıcı:** {USER}")


MENU = st.sidebar.radio('Menü', ['Vardiya Oluştur','Veriler','Geçmiş'])
# Özel not yeri
st.sidebar.markdown('Palladium&Hiltown Paşabahçe Magazaları Üretimidir Aşk ile Yapıldı')

# Menü
MENU = st.sidebar.radio('Menü', ['Vardiya Oluştur','Veriler','Geçmiş'])
# Veriler bölümü
if MENU == 'Veriler':
    st.header('Senaryo Ayarları')
    keys = list(SCENS.keys()); labels = list(SCENS.values())
    idx = keys.index(MGR['scenario']['type'])
    sel = st.radio('Senaryo', labels, index=idx)
    scen = keys[labels.index(sel)]
    ask_ara = st.checkbox('Ara vardiyaları manuel', value=MGR['scenario']['ask_ara'])
    ship_hour = MGR['scenario']['ship_hour']; early_days = MGR['scenario']['early_days']
    if scen == 'erken':
        ship_hour = st.number_input('Sevkiyat Saati (örn.8.5=08:30)', 0.0, 23.5, step=0.5, value=float(ship_hour))
        early_days = st.multiselect('Erken Günler', DAYS, default=early_days)
    if st.button('Kaydet Senaryo'):
        MGR['scenario'] = {'type':scen, 'ask_ara':ask_ara, 'ship_hour':ship_hour, 'early_days':early_days}
        save_db(DB)
        st.success('Kaydedildi')
    st.divider(); st.header('Çalışanlar')
    with st.expander('Yeni Çalışan Ekle'):
        n1, n2 = st.columns(2)
        name = n1.text_input('İsim'); code = n2.text_input('Sicil')
        is_pt = st.checkbox('Part-time'); ht_day = st.selectbox('Haftalık Tatil', DAYS)
        pt_days = st.multiselect('PT İzin Günleri', DAYS) if is_pt else []
        if st.button('Ekle') and name and code:
            MGR['employees'].append({'name':name,'sicil':code,'pt':is_pt,'pt_days':pt_days,'ht_day':ht_day})
            save_db(DB); st.success('Çalışan eklendi'); st.rerun()
    df_emp = pd.DataFrame(MGR['employees']) if MGR['employees'] else pd.DataFrame(columns=['name','sicil','pt','pt_days','ht_day'])
    edited = st.data_editor(df_emp, num_rows='dynamic', hide_index=True)
    if st.button('Çalışanları Kaydet'):
        clean = edited.dropna(subset=['name','sicil']).drop_duplicates(subset=['sicil'])
        MGR['employees'] = clean.to_dict('records')
        save_db(DB); st.success('Kaydedildi'); st.rerun()

# Vardiya Oluştur bölümü
if MENU == 'Vardiya Oluştur':
    st.header('Yeni Vardiya')
    if not MGR['employees']:
        st.warning('Önce çalışan ekleyin'); st.stop()
    week_start = st.date_input('Haftanın Pazartesi', datetime.today())
    ara_list = st.multiselect('Ara vardiya', [e['name'] for e in MGR['employees']]) if MGR['scenario']['ask_ara'] else []

    # İzin / Rapor
    iz_entries = st.session_state.setdefault('iz', {})
    with st.expander('İzin / Rapor'):
        emp_sel = st.selectbox('Çalışan', ['—']+[e['name'] for e in MGR['employees']])
        day_sel = st.selectbox('Gün', DAYS); type_sel = st.selectbox('Tür', ['Rapor','Yıllık İzin'])
        if st.button('Ekle İzin') and emp_sel != '—':
            iz_entries[emp_sel] = {'day':day_sel, 'type':('Rapor' if type_sel=='Rapor' else 'Yİ')}
            st.success('İzin eklendi')

    # Denkleştirme
    with st.expander('Denkleştirme'):
        use = st.checkbox('Denkleştirme Yap')
        if use:
            emp_d = st.selectbox('Çalışan', [e['name'] for e in MGR['employees']], key='denkl_emp')
            hrs = st.number_input('Kaç Saat (0.5 adım)', 0.5, 12.0, step=0.5, key='denkl_hrs')
            day_d = st.selectbox('Fazla Çalışılacak Gün', DAYS, key='denkl_day')
            exit_d = st.selectbox('Erken Çıkış Günü (Opsiyonel)', ['']+DAYS, key='denkl_exit')
            if st.button('Ekle Denkl'):
                st.session_state['denkl'] = {'emp':emp_d, 'hours':hrs, 'day':day_d, 'exit':exit_d}
                st.success('Denkleştirme eklendi')

    # Vardiya Oluştur butonu
    if st.button('Vardiya Oluştur 🛠️'):
        last = MGR['history'][-1]['schedule'] if MGR['history'] else []
        def prev(name,d): return next((r[d] for r in last if r['Çalışan']==name), None)
        rows = []
        for idx, e in enumerate(MGR['employees']):
            r = {'Çalışan':e['name'], 'Sicil':e['sicil']}
            for di, day in enumerate(DAYS):
                # İzin / PT / Haftalık Tatil
                ent = iz_entries.get(e['name'])
                if ent and ent['day']==day:
                    shift = ent['type']
                elif e['pt'] and day in e['pt_days']:
                    shift = 'PT'
                elif day == e['ht_day']:
                    shift = 'H.T'
                else:
                    scen = MGR['scenario']['type']
                    if scen == 'erken' and day in MGR['scenario']['early_days'] and e['name'] in random.sample([x['name'] for x in MGR['employees']], 2):
                        s = MGR['scenario']['ship_hour']; h,m = int(s), int((s-int(s))*60)
                        h2,m2 = int(s+8), int(((s+8)-int(s+8))*60)
                        shift = f"{h:02d}:{m:02d}-{h2:02d}:{m2:02d}"
                    elif scen == 'ayrik':
                        sab = sum(1 for d in DAYS if prev(e['name'],d) in ['Sabah','Ara'])
                        akm = sum(1 for d in DAYS if prev(e['name'], d)=='Akşam')
                        shift = 'Akşam' if sab > akm else 'Sabah'
                    else:
                        shift = 'Sabah' if (di+idx)%2==0 else 'Akşam'
                    if e['name'] in ara_list and shift=='Sabah':
                        shift = 'Ara'
                # Denkleştirme uygulama
                d_s = st.session_state.get('denkl')
                if d_s and d_s['emp']==e['name']:
                    if day == d_s['day'] and shift in SHIFT_TIMES:
                        start,end = SHIFT_TIMES[shift]
                        sf,ef = datetime.strptime(start,'%H:%M'), datetime.strptime(end,'%H:%M')
                        ef += timedelta(hours=d_s['hours']); shift = f"{sf.strftime('%H:%M')}-{ef.strftime('%H:%M')}"
                    if d_s['exit'] and day == d_s['exit'] and shift in SHIFT_TIMES:
                        start,end = SHIFT_TIMES.get(prev(e['name'],day), SHIFT_TIMES[shift])
                        sf,ef = datetime.strptime(start,'%H:%M'), datetime.strptime(end,'%H:%M')
                        ef -= timedelta(hours=d_s['hours']); shift = f"{sf.strftime('%H:%M')}-{ef.strftime('%H:%M')}"
                r[day] = shift
            rows.append(r)
        df = pd.DataFrame(rows)
        # Görsel tab
ingi
        time_map = {k:f"{v[0]}-{v[1]}" for k,v in SHIFT_TIMES.items()}
        shift_map = {**time_map, **SPECIAL}
        pretty = df.copy()
        for c in DAYS: pretty[c] = pretty[c].map(lambda x:shift_map.get(x,x))
        st.dataframe(pretty, use_container_width=True)
        MGR['history'].append({'week_start':str(week_start), 'schedule':rows}); save_db(DB)
        st.session_state['iz'] = {}
        st.download_button("Excel'e Aktar", pretty.to_csv(index=False).encode('utf-8-sig'))

# Geçmiş bölümü
if MENU == 'Geçmiş':
    st.header('Geçmiş Vardiyalar')
    hist = MGR['history']
    if not hist:
        st.info('Kayıt yok')
    else:
        sel = st.selectbox('Hafta', [h['week_start'] for h in hist])
        rec = next(h for h in hist if h['week_start']==sel)
        st.dataframe(pd.DataFrame(rec['schedule']), use_container_width=True)
