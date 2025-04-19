# Shift Demo – bug‑free edition with nicer employee UI
import json, os
from datetime import datetime
import pandas as pd, streamlit as st

PAGE_TITLE="Şişecam Paşabahçe | Otomatik Vardiya Sistemi"
PRIMARY="#0D4C92"; DATA_FILE="data.json"
DAYS=["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"]
SHIFT_MAP={"Sabah":"09:30‑18:00","Ara":"11:30‑20:00","Akşam":"13:30‑22:00","H.T":"Haftalık Tatil","PT":"Part‑time İzin","IZ":"İzin/Rapor"}
SCENS={"denge":"Denge (herkes 3 Sabah + 3 Akşam)","ayrik":"Ayrık (ekibin yarısı sabit Sabah, yarısı Akşam)"}
LEGACY={"balance":"Haftada ","split":"ayrik"}
DEFAULT_USERS={"admin":"1234","fatihdemir":"1234","ademkeles":"1234"}

# ── helpers ─────────────────────────────────────────────

def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE,'r',encoding='utf-8') as f:return json.load(f)
    return {"users":DEFAULT_USERS.copy(),"managers":{}}

def save_db(db):
    with open(DATA_FILE,'w',encoding='utf-8') as f:json.dump(db,f,ensure_ascii=False,indent=2)

# ── init state ──────────────────────────────────────────
if 'db' not in st.session_state: st.session_state['db']=load_db()
DB=st.session_state['db']; DB.setdefault('users',{}).update({k:v for k,v in DEFAULT_USERS.items() if k not in DB['users']}); DB.setdefault('managers',{}); save_db(DB)

st.set_page_config(page_title=PAGE_TITLE,page_icon="📆",layout="wide")
st.markdown(f"<style>div.block-container{{padding-top:1rem}} .st-emotion-cache-fblp2m{{color:{PRIMARY}!important}}</style>",unsafe_allow_html=True)
st.title(PAGE_TITLE)

# ── auth ───────────────────────────────────────────────
if 'user' not in st.session_state:
    u,p=st.columns(2); uname=u.text_input('Kullanıcı Adı'); upass=p.text_input('Şifre',type='password')
    if st.button('Giriş'):
        if DB['users'].get(uname)==upass:
            if uname not in DB['managers']:
                DB['managers'][uname]={'employees':[], 'scenario':{'type':'denge','ask_ara':False}, 'history':[]}; save_db(DB)
            st.session_state['user']=uname; st.rerun()
        else: st.error('Hatalı giriş')
    st.stop()

USER=st.session_state['user']; MGR=DB['managers'][USER]
if st.sidebar.button('🔓 Oturumu Kapat'): del st.session_state['user']; st.rerun()

# legacy scenario key
stype=LEGACY.get(MGR.get('scenario',{}).get('type','denge'),MGR.get('scenario',{}).get('type','denge'))
if stype not in SCENS: stype='denge'
MGR.setdefault('scenario',{'type':stype,'ask_ara':False}); MGR['scenario']['type']=stype; save_db(DB)

MENU=st.sidebar.radio('🚀 Menü',["Vardiya Oluştur","Veriler","Geçmiş"],index=0)

# ── Veriler ────────────────────────────────────────────
if MENU=='Veriler':
    st.header('📂 Veriler')
    # Senaryo
    st.subheader('Senaryo Ayarları')
    scen_sel=st.radio('Haftalık Dağıtım',SCENS,index=list(SCENS).index(stype))
    ask_ara=st.checkbox('Ara vardiyaları manuel seçeceğim',value=MGR['scenario'].get('ask_ara',False))
    if st.button('Kaydet Senaryo'): MGR['scenario'].update({'type':scen_sel,'ask_ara':ask_ara}); save_db(DB); st.success('Kaydedildi')

    st.divider(); st.subheader('Çalışanlar')

    # --- Yeni çalışan ekleme formu ---
    with st.expander('Yeni Çalışan Ekle'):
        ec1,ec2=st.columns(2); nm=ec1.text_input('İsim'); sc=ec2.text_input('Sicil')
        is_pt=st.checkbox('Part‑time')
        ht=st.selectbox('Haftalık Tatil',DAYS,index=6)
        pt_days=st.multiselect('PT İzin Günleri',DAYS) if is_pt else []
        if st.button('Ekle',key='add_emp') and nm and sc:
            MGR['employees'].append({'name':nm,'sicil':sc,'pt':is_pt,'pt_days':pt_days,'ht_day':ht})
            save_db(DB); st.success('Çalışan eklendi'); st.experimental_rerun()

    # --- Düzenleme tablosu ---
    emp_df=pd.DataFrame(MGR['employees']) if MGR['employees'] else pd.DataFrame(columns=['name','sicil','pt','pt_days','ht_day'])
    edited=st.data_editor(emp_df,width=None,num_rows='dynamic',hide_index=True)

    if st.button('Değişiklikleri Kaydet'):
        cleaned=edited.dropna(subset=['name','sicil'])  # boş satırları sil
        MGR['employees']=cleaned.to_dict('records'); save_db(DB); st.success('Kaydedildi')

# ── Vardiya Oluştur ─────────────────────────────────── ───────────────────────────────────
if MENU=='Vardiya Oluştur':
    st.header('🗓️ Yeni Vardiya')
    if not MGR['employees']: st.warning('Önce çalışan ekleyin'); st.stop()

    week_start=st.date_input('Haftanın Pazartesi',datetime.today())
    ara_list=st.multiselect('Ara vardiya atanacaklar',[e['name'] for e in MGR['employees']]) if MGR['scenario']['ask_ara'] else []
    iz_entries={}
    with st.expander('Bu hafta İzin/Rapor'):
        ie=st.selectbox('Çalışan',['—']+[e['name'] for e in MGR['employees']])
        iday=st.selectbox('Gün',DAYS)
        if st.button('Ekle',key='add_iz') and ie!='—': iz_entries[ie]=iday; st.success('Eklendi')

    if st.button('Vardiya Oluştur 🛠️'):
        last=MGR['history'][-1]['schedule'] if MGR['history'] else []
        def last_row(n): return next((r for r in last if r['Çalışan']==n),None)
        rows=[]
        for idx,e in enumerate(MGR['employees']):
            r={'Çalışan':e['name'],'Sicil':e['sicil']}; prev=last_row(e['name'])
            for d_idx,day in enumerate(DAYS):
                if iz_entries.get(e['name'])==day: r[day]='IZ'; continue
                if e.get('pt') and day in e.get('pt_days',[]): r[day]='PT'; continue
                if day==e.get('ht_day'): r[day]='H.T'; continue
                if DAYS[(d_idx+1)%7]==e.get('ht_day'): r[day]='Sabah'; continue
                if DAYS[(d_idx-1)%7]==e.get('ht_day'):
                    r[day]='Ara' if e['name'] in ara_list else 'Akşam'; continue
                scen=MGR['scenario']['type']
                prop='Sabah' if (scen=='ayrik' and idx<len(MGR['employees'])/2) or (scen=='denge' and (d_idx+idx)%2==0) else 'Akşam'
                if e['name'] in ara_list and prop=='Sabah': prop='Ara'
                if prev and prev.get(day)==prop: prop='Akşam' if prop=='Sabah' else 'Sabah'
                if d_idx>0 and r[DAYS[d_idx-1]]==prop: prop='Akşam' if prop=='Sabah' else 'Sabah'
                r[day]=prop
            rows.append(r)
        raw=pd.DataFrame(rows); pretty=raw.applymap(lambda x:SHIFT_MAP.get(x,x))
        st.dataframe(pretty,use_container_width=True)
        MGR['history'].append({'week_start':str(week_start),'schedule':raw.to_dict('records')}); save_db(DB)
        st.download_button('Excel\'e Aktar',pretty.to_csv(index=False).encode('utf-8-sig'))

# ── Geçmiş ─────────────────────────────────────────────
if MENU=='Geçmiş':
    st.header('📑 Geçmiş')
    hist = MGR.get('history', [])
    if not hist:
        st.info('Kayıt yok')
    else:
        options=[f"Hafta: {h['week_start']}" for h in hist[::-1]]
        choice=st.selectbox('Hafta',options)
        rec=hist[::-1][options.index(choice)]
        df=pd.DataFrame(rec['schedule']).applymap(lambda x:SHIFT_MAP.get(x,x))
        st.dataframe(df,use_container_width=True)

        col_clear,_=st.columns([1,5])
        if col_clear.button('Geçmişi Temizle 🗑️'):
            if st.confirm('Tüm geçmiş silinecek, emin misiniz?'):
                MGR['history'].clear(); save_db(DB)
                st.success('Geçmiş temizlendi')
                st.experimental_rerun()
