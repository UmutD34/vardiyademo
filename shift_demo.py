# Shift Demo – güncellenmiş Erken Vardiya Logic ile
import json, os, random
datetime
from datetime import datetime
import pandas as pd
import streamlit as st

PAGE_TITLE = "Şişecam Paşabahçe | Otomatik Vardiya Sistemi"
DATA_FILE = "data.json"
DAYS = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"]
SHIFT_MAP = {
    "Sabah": "09:30‑18:00",
    "Ara":  "11:30‑20:00",
    "Akşam": "13:30‑22:00",
    "H.T":   "Haftalık Tatil",
    "PT":   "Part‑time İzin",
    "Rapor":"Raporlu",
    "Yİ":   "Yıllık İzin",
}
SCENS = {
    "denge": "3 Sabahçı + 3 Akşamcı",
    "ayrik": "Yarı Sabahçı / Yarı Akşamcı (hafta değişir)",
    "erken": "Erken Vardiya"
}
DEFAULT_USERS = {"admin":"1234","fatihdemir":"1234","ademkeles":"1234"}

# DB helpers

def load_db():
    if os.path.exists(DATA_FILE):
        return json.load(open(DATA_FILE,encoding='utf-8'))
    return {"users":DEFAULT_USERS.copy(),"managers":{}}

def save_db(db): json.dump(db,open(DATA_FILE,'w',encoding='utf-8'),ensure_ascii=False,indent=2)

if 'db' not in st.session_state: st.session_state['db']=load_db()
DB=st.session_state['db']; DB.setdefault('users',{}).update({k:v for k,v in DEFAULT_USERS.items() if k not in DB['users']}); DB.setdefault('managers',{}); save_db(DB)

# page config
st.set_page_config(page_title=PAGE_TITLE,page_icon='📆',layout='wide')
st.title(PAGE_TITLE)

# auth
if 'user' not in st.session_state:
    u,p=st.columns(2)
    uname=u.text_input('Kullanıcı Adı'); upass=p.text_input('Şifre',type='password')
    if st.button('Giriş'):
        if DB['users'].get(uname)==upass:
            DB['managers'].setdefault(uname,{'employees':[],'scenario':{'type':'denge','ask_ara':False,'ship_hour':8.0,'early_days':[]},'history':[]})
            save_db(DB); st.session_state['user']=uname; st.rerun()
        else: st.error('Hatalı giriş')
    st.stop()
USER=st.session_state['user']; MGR=DB['managers'][USER]

# sidebar
menu=st.sidebar.radio('Menü', ['Vardiya Oluştur','Veriler','Geçmiş'])
st.sidebar.markdown('---'); st.sidebar.write('👤 Umut Doğan')

# Veriler page
if menu=='Veriler':
    st.header('Senaryo Ayarları')
    keys=list(SCENS); labels=list(SCENS.values()); idx=keys.index(MGR['scenario']['type'])
    sel_label=st.radio('Senaryo',labels,index=idx)
    scen=keys[labels.index(sel_label)]
    ask=st.checkbox('Ara vardiya manuel',value=MGR['scenario']['ask_ara'])
    ship=st.number_input('Sevkiyat Saati (küsurat)',min_value=0.0,max_value=23.5,step=0.5,value=float(MGR['scenario'].get('ship_hour',8.0))) if scen=='erken' else MGR['scenario']['ship_hour']
    early_days=st.multiselect('Erken Günler',DAYS,default=MGR['scenario'].get('early_days',[])) if scen=='erken' else []
    if st.button('Kaydet'): MGR['scenario']={'type':scen,'ask_ara':ask,'ship_hour':ship,'early_days':early_days}; save_db(DB); st.success('Kaydedildi')

    st.header('Çalışanlar')
    with st.expander('Yeni Çalışan'):
        n1,n2=st.columns(2); name=n1.text_input('İsim'); code=n2.text_input('Sicil')
        pt=st.checkbox('Part-Time'); ht=st.selectbox('Haftalık Tatil',DAYS)
        pt_days=st.multiselect('PT İzin Günleri',DAYS) if pt else []
        if st.button('Ekle'): MGR['employees'].append({'name':name,'sicil':code,'pt':pt,'pt_days':pt_days,'ht_day':ht}); save_db(DB); st.success('Eklendi'); st.rerun()
    df=pd.DataFrame(MGR['employees'])
    edited=st.data_editor(df,num_rows='dynamic',hide_index=True)
    if st.button('Kaydet Çalışan Değ'): MGR['employees']=edited.dropna(subset=['name','sicil']).drop_duplicates('sicil').to_dict('records'); save_db(DB); st.success('Kaydedildi'); st.rerun()

# Vardiya oluştur
if menu=='Vardiya Oluştur':
    st.header('Yeni Vardiya')
    if not MGR['employees']: st.warning('Çalışan yok'); st.stop()
    week=st.date_input('Pzt tarihi',datetime.today())
    ara_list = st.multiselect('Ara vardiya', [e['name'] for e in MGR['employees']]) if MGR['scenario']['ask_ara'] else []
    if 'iz' not in st.session_state: st.session_state['iz']={}
    iz=st.session_state['iz']
    with st.expander('İzin/Rapor'): emp=st.selectbox('Çalışan',['—']+[e['name'] for e in MGR['employees']]); day=st.selectbox('Gün',DAYS); itype=st.selectbox('Tür',['Rapor','Yıllık İzin']);
        if st.button('Kaydet İzin'): iz[emp]={'day':day,'type':'Rapor' if itype=='Rapor' else 'Yİ'}; st.success('Eklendi')
    # Erken atamalar
    scen=MGR['scenario']['type']; early_ass={}
    if scen=='erken':
        days=MGR['scenario']['early_days'];
        for d in days: early_ass[d]=random.sample([e['name'] for e in MGR['employees']],2)
    # schedule generate
    rows=[]
    for idx,e in enumerate(MGR['employees']): prev = MGR['history'][-1]['schedule'] if MGR['history'] else []
        prev_row = next((r for r in prev if r['Çalışan']==e['name']),{})
        for i,day in enumerate(DAYS):
            # izin
            ent=iz.get(e['name']);
            if ent and ent['day']==day: shift=ent['type']
            elif e['pt'] and day in e['pt_days']: shift='PT'
            elif day==e['ht_day']: shift='H.T'
            # erken logic
            elif scen=='erken' and day in MGR['scenario']['early_days'] and e['name'] in early_ass.get(day,[]):
                s=MGR['scenario']['ship_hour']; h1=int(s); m1=int((s-h1)*60);
                d1=f"{h1:02d}:{m1:02d}"; s2=s+8; h2=int(s2); m2=int((s2-h2)*60);
                shift=f"{d1}-{h2:02d}:{m2:02d}"
            else:
                # default denge
                prop = 'Sabah' if (i+idx)%2==0 else 'Akşam'
                shift=prop
            rows.append({'Çalışan':e['name'],'Gün':day,'Vardiya':shift})
    df_out=pd.DataFrame(rows)
    st.dataframe(df_out, use_container_width=True)
    MGR['history'].append({'week_start':str(week),'schedule':rows}); save_db(DB)
    st.session_state['iz']={}
    st.download_button('Excel',df_out.to_csv(index=False).encode('utf-8-sig'))

# Geçmiş
df_hist=pd.DataFrame([{'week':h['week_start'],**{d:r[d] for r in h['schedule']}} for h in MGR['history']])
if menu=='Geçmiş':
    st.header('Geçmiş')
    st.dataframe(df_hist,use_container_width=True)
