# Shift Demo – Stabil, Denkleştirme & Denge/Erken Güncellemeleri
import json, os, random
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

PAGE_TITLE = "Şişecam Paşabahçe | Otomatik Vardiya Sistemi"
DATA_FILE = "data.json"
DAYS = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"]

SHIFT_TIMES = {
    'Sabah': ('09:30','18:00'),
    'Ara':   ('11:30','20:00'),
    'Akşam': ('13:30','22:00')
}
SPECIAL = {
    'H.T':'Haftalık Tatil','PT':'Part‑time İzin','Rapor':'Raporlu','Yİ':'Yıllık İzin'
}
SCENS = {'denge':'3 Sabahçı + 3 Akşamcı','ayrik':'Yarı Sabahçı/Yarı Akşamcı (hafta ters)','erken':'Erken Vardiya'}
DEFAULT_USERS = {'admin':'1234','fatihdemir':'1234','ademkeles':'1234'}

# ── DB Helpers ─────────────────────────
def load_db(): return json.load(open(DATA_FILE,encoding='utf-8')) if os.path.exists(DATA_FILE) else {'users':DEFAULT_USERS.copy(),'managers':{}}
def save_db(db): json.dump(db,open(DATA_FILE,'w',encoding='utf-8'),ensure_ascii=False,indent=2)
if 'db' not in st.session_state: st.session_state['db']=load_db()
DB=st.session_state['db']; DB.setdefault('users',{}).update({u:DEFAULT_USERS[u] for u in DEFAULT_USERS if u not in DB['users']}); DB.setdefault('managers',{}); save_db(DB)

# ── Layout ──────────────────────────────
st.set_page_config(page_title=PAGE_TITLE,page_icon='📆',layout='wide')
st.markdown("""
<style>
div.block-container{padding-top:2rem}
.stButton>button{border-radius:6px;font-weight:600}
</style>
""",unsafe_allow_html=True)
st.title(PAGE_TITLE)

# ── Auth ────────────────────────────────
if 'user' not in st.session_state:
    c1,c2=st.columns(2); uname=c1.text_input('Kullanıcı Adı'); upass=c2.text_input('Şifre',type='password')
    if st.button('Giriş'):
        if DB['users'].get(uname)==upass:
            DB['managers'].setdefault(uname,{'employees':[],'scenario':{'type':'denge','ask_ara':False,'ship_hour':8.0,'early_days':[]},'history':[]}); save_db(DB)
            st.session_state['user']=uname; st.rerun()
        else: st.error('Hatalı kullanıcı/şifre')
    st.stop()
USER=st.session_state['user']; MGR=DB['managers'][USER]
if st.sidebar.button('🔓 Oturumu Kapat'): del st.session_state['user']; st.rerun()
st.sidebar.write(f'👤 {USER}')

# ── Sidebar Menu ─────────────────────────
MENU=st.sidebar.radio('Menü',['Vardiya Oluştur','Veriler','Geçmiş'])

# ── Veriler ──────────────────────────────
if MENU=='Veriler':
    st.header('Senaryo Ayarları')
    types=list(SCENS.keys()); labels=list(SCENS.values()); idx=types.index(MGR['scenario']['type'])
    sel=st.radio('Senaryo',labels,index=idx); scen=types[labels.index(sel)]
    ask=st.checkbox('Ara vardiyaları manuel',value=MGR['scenario']['ask_ara'])
    ship=MGR['scenario']['ship_hour']; days_early=MGR['scenario']['early_days']
    if scen=='erken':
        ship=st.number_input('Sevkiyat Saati (örn.8.5=08:30)',0.0,23.5,step=0.5,value=float(ship))
        days_early=st.multiselect('Erken Günler',DAYS,default=days_early)
    if st.button('Kaydet Senaryo'):
        MGR['scenario']={'type':scen,'ask_ara':ask,'ship_hour':ship,'early_days':days_early}; save_db(DB); st.success('Kaydedildi')
    st.divider(); st.header('Çalışanlar')
    with st.expander('Yeni Çalışan Ekle'):
        n1,n2=st.columns(2); nm=n1.text_input('İsim'); sc=n2.text_input('Sicil')
        pt=st.checkbox('Part-time'); ht=st.selectbox('Haftalık Tatil',DAYS)
        pt_days=st.multiselect('PT Günleri',DAYS) if pt else []
        if st.button('Ekle') and nm and sc:
            MGR['employees'].append({'name':nm,'sicil':sc,'pt':pt,'pt_days':pt_days,'ht_day':ht}); save_db(DB); st.success('Eklendi'); st.rerun()
    df=pd.DataFrame(MGR['employees']) if MGR['employees'] else pd.DataFrame(columns=['name','sicil','pt','pt_days','ht_day'])
    ed=st.data_editor(df,num_rows='dynamic',hide_index=True)
    if st.button('Çalışanları Kaydet'):
        clean=ed.dropna(subset=['name','sicil']).drop_duplicates('sicil')
        MGR['employees']=clean.to_dict('records'); save_db(DB); st.success('Kaydedildi'); st.rerun()

# ── Vardiya Oluştur ───────────────────────
if MENU=='Vardiya Oluştur':
    st.header('Yeni Vardiya')
    if not MGR['employees']: st.warning('Çalışan yok'); st.stop()
    week=st.date_input('Haftanın Pazartesi',datetime.today())
    ara_list=st.multiselect('Ara vardiya', [e['name'] for e in MGR['employees']]) if MGR['scenario']['ask_ara'] else []

    # İzin/Rapor ve Denkleştirme expanders
    iz_entries=st.session_state.setdefault('iz',{})
    with st.expander('İzin / Rapor'): 
        emp=st.selectbox('Çalışan',['—']+[e['name'] for e in MGR['employees']]); d=st.selectbox('Gün',DAYS); t=st.selectbox('Tür',['Rapor','Yıllık İzin'])
        if st.button('Ekle İzin'): iz_entries[emp]={'day':d,'type':('Rapor' if t=='Rapor' else 'Yİ')}; st.success('Eklendi')
    denkl=st.session_state.setdefault('denkl',None)
    with st.expander('Denkleştirme'): 
        use=st.checkbox('Denkleştirme Yap'); temp=None
        if use:
            emp_d=st.selectbox('Çalışan', [e['name'] for e in MGR['employees']])
            hrs=st.number_input('Kaç Saat (0.5 adım)',0.5,12.0,step=0.5)
            day_d=st.selectbox('Fazla Çalışılacak Gün',DAYS)
            exit_d=st.selectbox('Erken Çıkış Günü (Opsl.)',['']+DAYS)
            if st.button('Ekle Denkl'): denkl={'emp':emp_d,'hours':hrs,'day':day_d,'exit':exit_d}; st.session_state['denkl']=denkl; st.success('Eklendi')

    # Atama
    last=MGR['history'][-1]['schedule'] if MGR['history'] else []
    def prev(emp,day): return next((r[day] for r in last if r['Çalışan']==emp),None)
    rows=[]
    for idx,e in enumerate(MGR['employees']):
        for di,day in enumerate(DAYS):
            # izin / PT / HT
            ent=iz_entries.get(e['name']);
            if ent and ent['day']==day: shift=ent['type']
            elif e['pt'] and day in e['pt_days']: shift='PT'
            elif day==e['ht_day']: shift='H.T'
            else:
                scen=MGR['scenario']['type']
                # Erken Vardiya aşaması
                if scen=='erken' and day in MGR['scenario']['early_days'] and e['name'] in random.sample([x['name'] for x in MGR['employees']],2):
                    s=MGR['scenario']['ship_hour']; h,m=int(s),int((s-int(s))*60)
                    h2,m2=int(s+8),int(((s+8)-int(s+8))*60)
                    shift=f"{h:02d}:{m:02d}-{h2:02d}:{m2:02d}"
                else:
                    # denge veya ayrık
                    if scen=='ayrik':
                        sab=sum(1 for d in DAYS if prev(e['name'],d) in ['Sabah','Ara'])
                        akm=sum(1 for d in DAYS if prev(e['name'],d)=='Akşam')
                        shift='Akşam' if sab>akm else 'Sabah'
                    else:
                        half=len(MGR['employees'])/2
                        shift='Sabah' if idx<half else 'Akşam'
                # Ara
                if e['name'] in ara_list and shift=='Sabah': shift='Ara'
            # Denklştirme apply
            if denkl and denkl['emp']==e['name']:
                if day==denkl['day'] and shift in SHIFT_TIMES:
                    stime,etime=SHIFT_TIMES[shift]
                    sf=datetime.strptime(stime,'%H:%M'); ef=datetime.strptime(etime,'%H:%M')
                    ef+=timedelta(hours=denkl['hours']); shift=f"{sf.strftime('%H:%M')}-{ef.strftime('%H:%M')}"
                if denkl['exit'] and day==denkl['exit'] and shift in SHIFT_TIMES:
                    stime,etime=SHIFT_TIMES[prev(e['name'],day) or shift]
                    sf=datetime.strptime(stime,'%H:%M'); ef=datetime.strptime(etime,'%H:%M')
                    ef-=timedelta(hours=denkl['hours']); shift=f"{sf.strftime('%H:%M')}-{ef.strftime('%H:%M')}"
            rows.append({'Çalışan':e['name'],**{day:shift}})
    df=pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)
    MGR['history'].append({'week_start':str(week),'schedule':rows}); save_db(DB)
    st.session_state['iz']={}; st.download_button('Excel',df.to_csv(index=False).encode('utf-8-sig'))

# ── Geçmiş ────────────────────────────────
if MENU=='Geçmiş': 
    st.header('Geçmiş Vardiyalar')
    hist=MGR['history'];
    if not hist: st.info('Yok')
    else:
        opt=[h['week_start'] for h in hist]
        sel=st.selectbox('Hafta',opt)
        rec=next(h for h in hist if h['week_start']==sel)
        st.dataframe(pd.DataFrame(rec['schedule']),use_container_width=True)
