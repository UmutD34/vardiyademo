# ------------- Shift Demo corrected full script -------------
import json, os
from datetime import datetime
import pandas as pd, streamlit as st

PAGE_TITLE = "Şişecam Paşabahçe | Otomatik Vardiya Sistemi"
PRIMARY = "#0D4C92"
DATA_FILE = "data.json"
DAYS = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"]
SHIFT_MAP = {
    "Sabah":"09:30‑18:00","Ara":"11:30‑20:00","Akşam":"13:30‑22:00",
    "H.T":"Haftalık Tatil","PT":"Part‑time İzin","IZ":"İzin/Rapor",
}
SCENS={"denge":"Denge (her çalışan 3 Sabah + 3 Akşam)","ayrik":"Ayrık (yarı Sabah, yarı Akşam)"}
LEGACY={"balance":"denge","split":"ayrik"}
DEFAULT_USERS={"admin":"1234","fatihdemir":"1234","ademkeles":"1234"}

# ---------- helpers ----------

def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE,'r',encoding='utf-8') as f: return json.load(f)
    return {"users":DEFAULT_USERS.copy(),"managers":{}}

def save_db(db):
    with open(DATA_FILE,'w',encoding='utf-8') as f: json.dump(db,f,ensure_ascii=False,indent=2)

# ---------- init ----------
if "db" not in st.session_state:
    st.session_state["db"] = load_db()
DB = st.session_state["db"]
DB.setdefault('users',{}).update({k:v for k,v in DEFAULT_USERS.items() if k not in DB['users']})
DB.setdefault('managers',{})
save_db(DB)

st.set_page_config(page_title=PAGE_TITLE,page_icon="📆",layout="wide")
st.markdown(f"<style>div.block-container{{padding-top:1rem}} .st-emotion-cache-fblp2m{{color:{PRIMARY}!important}}</style>",unsafe_allow_html=True)
st.title(PAGE_TITLE)

# ---------- auth ----------
if 'user' not in st.session_state:
    ucol,pcol=st.columns(2)
    uname=ucol.text_input('Kullanıcı Adı')
    upass=pcol.text_input('Şifre',type='password')
    if st.button('Giriş'):
        if DB['users'].get(uname)==upass:
            if uname not in DB['managers']:
                DB['managers'][uname]={"employees":[],"scenario":{"type":"denge","ask_ara":False},"history":[]}
                save_db(DB)
            st.session_state['user']=uname
            st.experimental_rerun()
        else: st.error('Hatalı kullanıcı / şifre')
    st.stop()

USER=st.session_state['user']
MGR=DB['managers'][USER]

if st.sidebar.button('🔓 Oturumu Kapat'):
    del st.session_state['user']; st.experimental_rerun()

# legacy scenario fix
stype=LEGACY.get(MGR.get('scenario',{}).get('type','denge'),MGR.get('scenario',{}).get('type','denge'))
if stype not in SCENS: stype='denge'
MGR.setdefault('scenario',{"type":stype,"ask_ara":False})
MGR['scenario']['type']=stype; save_db(DB)

MENU=st.sidebar.radio('🚀 Menü',["Vardiya Oluştur","Veriler","Geçmiş"],index=0)

# ---------- Veriler ----------
if MENU=='Veriler':
    st.header('📂 Veriler')
    st.subheader('Senaryo Ayarları')
    scen_sel=st.radio('Haftalık Dağıtım',SCENS,index=list(SCENS).index(stype))
    ask_ara=st.checkbox('Ara vardiyaları her hafta manuel seçeceğim',value=MGR['scenario'].get('ask_ara',False))
    if st.button('Kaydet Senaryo'): MGR['scenario'].update({'type':scen_sel,'ask_ara':ask_ara}); save_db(DB); st.success('Kaydedildi')

    st.divider(); st.subheader('Çalışanlar')
    with st.expander('Yeni Çalışan Ekle'):
        n1,n2=st.columns(2); nm=n1.text_input('İsim'); sc=n2.text_input('Sicil')
        is_pt=st.checkbox('Part‑time'); ht=st.selectbox('Haftalık Tatil',DAYS,index=6)
        pt_days=st.multiselect('PT İzin Günleri',DAYS) if is_pt else []
        if st.button('Ekle') and nm and sc:
            MGR['employees'].append({'name':nm,'sicil':sc,'pt':is_pt,'pt_days':pt_days,'ht_day':ht}); save_db(DB); st.success('Eklendi')
    if MGR['employees']:
        for i,e in enumerate(MGR['employees']):
            c=st.columns([4,1]); c[0].markdown(f"**{e['name']}** — {e['sicil']} • {e['ht_day']} • {'PT' if e['pt'] else 'FT'}")
            if c[1].button('Sil',key=f'del{i}'):
                MGR['employees'].pop(i); save_db(DB); st.experimental_rerun()
    else: st.info('Henüz çalışan yok.')

# ---------- Vardiya Oluştur ----------
if MENU=='Vardiya Oluştur':
    st.header('🗓️ Yeni Vardiya Oluştur')
    if not MGR['employees']: st.warning('Önce çalışan ekleyin'); st.stop()
    week_start=st.date_input('Haftanın Pazartesi',datetime.today())
    ara_list=st.multiselect('Ara vardiya atanacaklar',[e['name'] for e in MGR['employees']]) if MGR['scenario'].get('ask_ara') else []
    iz_entries={}
    with st.expander('Bu hafta İzin / Rapor'):
        ie=st.selectbox('Çalışan',['—']+[e['name'] for e in MGR['employees']])
        iday=st.selectbox('Gün',DAYS)
        if st.button('Ekle İzin/Rapor') and ie!='—': iz_entries[ie]=iday; st.success('Kayıt eklendi')

    if st.button('Vardiya Oluştur 🛠️'):
        last=MGR['history'][-1]['schedule'] if MGR['history'] else []
        def last_row(n): return next((r for r in last if r['Çalışan']==n),None)
        rows=[]
        for idx,e in enumerate(MGR['employees']):
            r={"Çalışan":e['name'],"Sicil":e['sicil']}; prev=last_row(e['name'])
            for d_idx,day in enumerate(DAYS):
                if iz_entries.get(e['name'])==day: r[day]='IZ'; continue
                if e['pt'] and day in e['pt_days']: r[day]='PT'; continue
                if day==e['ht_day']: r[day]='H.T'; continue
                if DAYS[(d_idx+1)%7]==e['ht_day']: r[day]='Sabah'; continue
                if DAYS[(d_idx-1)%7]==e['ht_day']:
                    r[day]='Ara' if e['name'] in ara_list else 'Akşam'; continue
                scen=MGR['scenario']['type']
                prop='Sabah' if (scen=='ayrik' and idx<len(MGR['employees'])/2) or (scen=='denge' and (d_idx+idx)%2==0) else 'Akşam'
                if e['name'] in ara_list and prop=='Sabah': prop='Ara'
                if prev and prev.get(day)==prop: prop='Akşam' if prop=='Sabah' else 'Sabah'
                if d_idx>0 and r[DAYS[d_idx-1]]==prop: prop='Akşam' if prop=='Sabah' else 'Sabah'
                r[day]=prop
            rows.append(r)
        raw=pd.DataFrame(rows)
        pretty=raw.copy(); [pretty.__setitem__(d,pretty[d].map(lambda x:SHIFT_MAP.get(x,x))) for d in DAYS]
        st.dataframe(pretty,use_container_width=True)
        MGR['history'].append({'week_start':str(week_start),'schedule':raw.to_dict('records')}); save_db(DB)
        st.download_button('Excel\'e Aktar',pretty.to_csv(index=False).encode('utf-8-sig'),file_name='vardiya.csv')

# ---------- Geçmiş ----------
if MENU=='Geçmiş':
    st.header('📑 Geçmiş Vardiyalar')
    if not MGR['history']: st.info('Kayıt yok');
    else:
        opts=[f"Hafta: {h['week_start']}" for h in MGR['history'][::-1]]
        ch=st.selectbox('Hafta',opts)
        rec=MGR['history'][::-1][opts.index(ch)]
        df=pd.DataFrame(rec['schedule']); [df.__setitem__(d,df[d].map(lambda x:SHIFT_MAP.get(x,x))) for d in DAYS]
        st.dataframe(df,use_container_width=True)
