import mne, glob, os, re, yaml, numpy as np, pandas as pd
rows=[]; curves={}
lags=np.arange(-3,8.001,0.05)
for d in sorted(glob.glob("data/derivatives/P*")):
    p=os.path.basename(d); e=glob.glob(f"data/raw/{p}/*Trial*.EDF"); v=glob.glob(f"data/raw/{p}/*.webm")
    if not e or not os.path.exists(f"{d}/pose.npz"): continue
    r=mne.io.read_raw_edf(e[0],preload=True,verbose="error"); r.pick([c for c in r.ch_names if "Add" not in c])
    x=r.filter(20,34,verbose="error").get_data()*1e6; sf=r.info["sfreq"]
    env=np.sqrt(np.convolve((x**2).mean(0),np.ones(50)/50,"same")); env=np.log(env+1e-3); te=r.times; env[:300]=np.median(env)
    z=np.load(f"{d}/pose.npz"); tv=z["t"]; mv=np.nan_to_num(z["motion"])
    tl=pd.read_csv(f"{d}/timeline.csv"); ist=tl[tl.task.str.contains("ISTIRAHAT UTAMA",na=False)].start.min()
    end_mov=tl[tl.task.str.contains("AGEM|NGEED",na=False)].end.max()
    def scan(a,b):
        t=np.arange(a,b,0.1); m=np.interp(t,tv,mv); out=[]
        for L in lags:
            ok=(t+L>0)&(t+L<te[-1]); out.append(np.corrcoef(m[ok],np.interp(t[ok]+L,te,env))[0,1] if ok.sum()>100 else np.nan)
        return np.array(out)
    c=scan(4,end_mov); c1=scan(4,ist); c2=scan(ist,end_mov); curves[p]=c
    dec=yaml.safe_load(open(f"data/decisions/{p}.yaml"))["sync"]
    used=dec.get("offset_sec", dec.get("offset_blocks"))
    m=re.search(r"(\d{4}-\d\d-\d\d)T(\d\d)-(\d\d)",v[0]) if v else None
    rows.append(dict(p=p, hari=m.group(1)[5:] if m else "?", jam_wita=f"{int(m.group(2))+8:02d}:{m.group(3)}" if m else "?",
        offset_dipakai=used, metode=dec.get("method"), scan_terbaik=round(lags[np.nanargmax(c)],2), r_puncak=round(np.nanmax(c),2),
        r_pada_085=round(c[np.argmin(abs(lags-0.85))],2), blok1=round(lags[np.nanargmax(c1)],2), blok2=round(lags[np.nanargmax(c2)],2),
        edf_min_video=round(te[-1]-tv[-1],1)))
df=pd.DataFrame(rows); df.to_csv("results/pola_offset.csv",index=False); np.savez("results/pola_offset_curves.npz",lags=lags,**curves)
pd.set_option("display.width",200); print(df.to_string(index=False))
